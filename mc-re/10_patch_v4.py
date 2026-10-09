#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v4 补丁（幂等）：修 v3 实测暴露的两个问题
  1. 名字仍是"艾莉克斯"：显示名读 zh_CN.lang 的 skin.name.alex 键（按皮肤 id 本地化），
     不读 skindefs.json。把 skin.name.alex/steve 的值改成 rinkehorb（中英两个 lang）。
  2. 细手臂+错位：默认皮肤按 Alex id 硬走 geometry.humanoid.customSlim（手臂 3 宽），
     而贴图已换成 steve.png（4 宽布局）。把 base.json 里 customSlim 骨架的手臂
     全部改成 4 宽（对齐 custom 粗手臂尺寸/pivot/origin，uv 不变）。
smali 不动（沿用 v3 的 classes.dex）。
"""
import json
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "original", "Minecraft.apk")
V3A = os.path.join(HERE, "v3_assets")
A4 = os.path.join(HERE, "v4_assets")

ZH = "assets/resource_packs/vanilla/texts/zh_CN.lang"
EN = "assets/resource_packs/vanilla/texts/en_US.lang"
BASEJSON = "assets/resource_packs/skins/skinpacks/Base/base.json"

NEW_NAME = "rinkehorb"


def patch_lang():
    z = zipfile.ZipFile(SRC)

    zh = z.read(ZH).decode("utf-8")
    lines = zh.split("\n")
    out = []
    hit = 0
    for ln in lines:
        if ln.startswith("skin.name.alex="):
            out.append("skin.name.alex=%s\t#" % NEW_NAME)
            hit += 1
        elif ln.startswith("skin.name.steve="):
            out.append("skin.name.steve=%s\t#" % NEW_NAME)
            hit += 1
        else:
            out.append(ln)
    assert hit == 2, "zh_CN skin.name 键替换数异常: %d" % hit
    open(os.path.join(A4, "zh_CN.lang"), "wb").write("\n".join(out).encode("utf-8"))
    print("[lang] zh_CN: skin.name.alex/steve ->", NEW_NAME)

    en = z.read(EN).decode("utf-8")
    out = []
    hit = 0
    for ln in en.split("\n"):
        if ln.startswith("skin.name.alex="):
            out.append("skin.name.alex=%s" % NEW_NAME); hit += 1
        elif ln.startswith("skin.name.steve="):
            out.append("skin.name.steve=%s" % NEW_NAME); hit += 1
        else:
            out.append(ln)
    assert hit == 2, "en_US skin.name 键替换数异常: %d" % hit
    open(os.path.join(A4, "en_US.lang"), "wb").write("\n".join(out).encode("utf-8"))
    print("[lang] en_US: skin.name.alex/steve ->", NEW_NAME)


def patch_basejson():
    z = zipfile.ZipFile(SRC)
    bj = json.loads(z.read(BASEJSON).decode("utf-8"))
    slim = bj["geometry.humanoid.customSlim:geometry.humanoid"]
    # 粗手臂目标（对照 geometry.humanoid.custom 的对应骨骼）
    FIX = {
        "leftArm":   {"pivot": [5.0, 22.0, 0.0],  "origin": [4.0, 12.0, -2.0],   "size": [4, 12, 4]},
        "rightArm":  {"pivot": [-5.0, 22.0, 0.0], "origin": [-8.0, 12.0, -2.0],  "size": [4, 12, 4]},
        "leftSleeve":  {"pivot": [5.0, 22.0, 0.0],  "origin": [4.0, 12.0, -2.0],   "size": [4, 12, 4]},
        "rightSleeve": {"pivot": [-5.0, 22.0, 0.0], "origin": [-8.0, 12.0, -2.0],  "size": [4, 12, 4]},
    }
    for bone in slim["bones"]:
        if bone["name"] in FIX:
            f = FIX[bone["name"]]
            bone["pivot"] = f["pivot"]
            bone["cubes"][0]["origin"] = f["origin"]
            bone["cubes"][0]["size"] = f["size"]
    open(os.path.join(A4, "base.json"), "wb").write(
        json.dumps(bj, ensure_ascii=False, indent=2).encode("utf-8"))
    print("[base.json] customSlim 手臂 3->4 粗手臂化完成")


def copy_v3_assets():
    # v3 的 skindefs.json / alex.png / alex_dev.png 沿用
    for fn in ("skindefs.json", "alex.png", "alex_dev.png"):
        shutil.copyfile(os.path.join(V3A, fn), os.path.join(A4, fn))
    print("[assets] 沿用 v3 的 skindefs.json / alex.png / alex_dev.png")


if __name__ == "__main__":
    if os.path.exists(A4):
        shutil.rmtree(A4)
    os.makedirs(A4)
    patch_lang()
    patch_basejson()
    copy_v3_assets()
    print("v4 assets 全部完成")
