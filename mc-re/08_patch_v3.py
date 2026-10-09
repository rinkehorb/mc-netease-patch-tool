#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3 补丁（幂等，可重复跑）：
  A. smali：matrix/a.smali 中 NOP 掉三个 360 悬浮球/游戏中心初始化调用
     （QSuspendAgent.init、suspend/c/c.l()、gameunionplugin/a.a(Context)）
  B. assets 生成：
     - skindefs.json：Steve 排第一；Steve 条目 name -> rinkehorb；Alex 条目改造为
       Steve 外观（geometry 换 classic、texture 指 steve）+ name rinkehorb（双保险，
       防止默认皮肤 id 硬编码为 Standard_Alex）
     - alex.png / alex_dev.png：本体替换为 steve.png / steve_dev.png 内容

用法： python 08_patch_v3.py
产物： smali_v3/（补丁后的 smali 树）、v3_assets/（改后的皮肤资源）
"""
import json
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "original", "Minecraft.apk")
S2 = os.path.join(HERE, "smali_v2")
S3 = os.path.join(HERE, "smali_v3")
A3 = os.path.join(HERE, "v3_assets")
MATRIX = os.path.join(S3, "com", "qihoo", "gamecenter", "sdk", "matrix", "a.smali")

SKIN_DEF = "assets/resource_packs/skins/skinpacks/Base/skindefs.json"
ALEX = "assets/resource_packs/skins/skinpacks/Base/alex.png"
ALEX_DEV = "assets/resource_packs/skins/skinpacks/Base/alex_dev.png"
STEVE = "assets/resource_packs/skins/skinpacks/Base/steve.png"
STEVE_DEV = "assets/resource_packs/skins/skinpacks/Base/steve_dev.png"

PLAYER_NAME = "rinkehorb"

# ---------------- A. smali ----------------
def patch_matrix():
    if os.path.exists(S3):
        shutil.rmtree(S3)
    shutil.copytree(S2, S3)
    with open(MATRIX, "r", encoding="utf-8") as f:
        src = f.read()

    edits = []
    # 1) QSuspendAgent.init
    a1 = "invoke-static {p0}, Lcom/qihoo/gamecenter/sdk/suspend/QSuspendAgent;->init(Landroid/app/Activity;)V"
    b1 = "nop"
    # 2) suspend/c/c.l() 三连
    a2 = ("invoke-static {}, Lcom/qihoo/gamecenter/sdk/suspend/c/c;->a()Lcom/qihoo/gamecenter/sdk/suspend/c/c;\n"
          "\n"
          "    move-result-object v0\n"
          "\n"
          "    invoke-virtual {v0}, Lcom/qihoo/gamecenter/sdk/suspend/c/c;->l()V")
    b2 = "nop\n\n    nop\n\n    nop"
    # 3) gameunionplugin/a.a(Context) 初始化
    a3 = "invoke-static {p0}, Lcom/qihoo/gamecenter/sdk/support/gameunionplugin/a;->a(Landroid/content/Context;)V"
    b3 = "nop"

    for i, (a, b) in enumerate([(a1, b1), (a2, b2), (a3, b3)], 1):
        cnt = src.count(a)
        if cnt == 0:
            print(f"[smali] 第{i}处目标未找到 -> 可能已补丁或代码结构变化")
        elif cnt > 1:
            print(f"[smali] 第{i}处目标出现 {cnt} 次 -> 需人工确认")
        else:
            src = src.replace(a, b)
            print(f"[smali] 第{i}处已 NOP")

    with open(MATRIX, "w", encoding="utf-8") as f:
        f.write(src)

    # 自检：三处 invoke 必须全部消失
    remain = src.count("QSuspendAgent;->init") + src.count("suspend/c/c;->l()V") + \
             src.count("gameunionplugin/a;->a(Landroid/content/Context;)V")
    print(f"[smali] 残留目标调用数: {remain}（应为 0）")
    if remain != 0:
        raise SystemExit("FAIL: 仍有目标调用未清除")
    # 类数校验
    n_class = sum(len(d) for _, _, d in os.walk(S3) if d)
    print(f"[smali] smali_v3 目录类数: {n_class}（应等于 smali_v2）")


# ---------------- B. assets ----------------
def patch_assets():
    if os.path.exists(A3):
        shutil.rmtree(A3)
    os.makedirs(A3)
    z = zipfile.ZipFile(SRC)

    # 1) skindefs.json
    sd = json.loads(z.read(SKIN_DEF).decode("utf-8-sig"))
    skins = sd["skins"]
    by_id = {s["id"]: s for s in skins}
    steve = by_id["skinpacks/Base/steve"]
    alex = by_id["skinpacks/Base/alex"]
    # Steve 排第一
    rest = [s for s in skins if s["id"] not in ("skinpacks/Base/steve", "skinpacks/Base/alex")]
    steve["name"] = PLAYER_NAME
    # Alex 条目改造为 Steve 外观 + 新名字（双保险）
    alex["name"] = PLAYER_NAME
    alex["geometry"] = "geometry.humanoid.custom"
    alex["texture"] = "skinpacks/Base/steve"
    new_skins = [steve, alex] + rest
    sd["skins"] = new_skins
    new_json = json.dumps(sd, ensure_ascii=False, indent=2).encode("utf-8")
    with open(os.path.join(A3, "skindefs.json"), "wb") as f:
        f.write(new_json)
    print("[assets] skindefs.json 已生成（顺序: Steve[%s], Alex[%s], ...）" % (steve["name"], alex["name"]))

    # 2) alex.png / alex_dev.png <- steve.png / steve_dev.png
    for dst, src in ((ALEX, STEVE), (ALEX_DEV, STEVE_DEV)):
        data = z.read(src)
        with open(os.path.join(A3, os.path.basename(dst)), "wb") as f:
            f.write(data)
        print(f"[assets] {os.path.basename(dst)} <- {os.path.basename(src)} 字节级替换（{len(data)} B）")
    print("[assets] 完成")


if __name__ == "__main__":
    patch_matrix()
    patch_assets()
    print("v3 补丁全部完成")
