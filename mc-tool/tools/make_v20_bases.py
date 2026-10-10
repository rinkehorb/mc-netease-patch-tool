"""从 v19 生成两个"底包"：v20a（4px / Steve）与 v20b（3px / Alex）。

为什么需要底包
    手臂粗细在**首次运行建立玩家档案**时就定死了（实测见 mc-tool/README.md §2.2.1），
    之后覆盖安装只换贴图、不换粗细。
    所以正确用法是：先装一个"锁好粗细"的底包，再用工具去换皮肤/改名/加资源包
    （那些都走覆盖安装，贴图会变，粗细保持底包的值）。
    底包的默认皮肤 = `skindefs.json` 里 **skins 数组第一条**（实测结论）。

三个来源
    v19（成品/Minecraft-0.2.0.25445-offline-v19.apk）  ← 离线补丁在这里的 classes.dex 里，必须基于它
    官方母本（mc-re/original/Minecraft.apk）           ← 取回原版的 alex.png / alex_dev.png
                                                        （v19 这两张已被换成 Miku）

每个底包改什么（**不碰 classes.dex**，所以离线补丁原样保留）
    1. Base/alex.png、Base/alex_dev.png  ← 官方母本里的原版
    2. Base/skindefs.json：
         v20a: Steve 排第一，所有 geometry = geometry.humanoid.custom      (4px / Steve 体型)
         v20b: Alex  排第一，所有 geometry = geometry.humanoid.customSlim  (3px / Alex 体型)

输出的是**未签名** APK，交给 DesktopHarness 去签名 —— 顺带让它注入「导入世界」按钮：

    java -cp <classes> DesktopHarness <本脚本产物> <成品.apk> <assetsDir> - - slim <mc-import.js>

用法：
    python make_v20_bases.py <v19.apk> <官方母本.apk> <输出目录>
"""
import json
import os
import sys
import zipfile

BASE = "assets/resource_packs/skins/skinpacks/Base/"
SKINDEFS = BASE + "skindefs.json"
ALEX = [BASE + "alex.png", BASE + "alex_dev.png"]

# v19 把玩家名（= 默认皮肤的名字）改成了 "Miku"，底包要还原成官方原版：
#   zh_CN: skin.name.alex=艾莉克斯   en_US: skin.name.alex=Alex
# 每个语言文件与官方母本**只差这一行**（实测：BOM 保留、行数一致、steve/dummy 本来就对）。
LANG_FILES = [
    "assets/resource_packs/vanilla/texts/zh_CN.lang",
    "assets/resource_packs/vanilla/texts/en_US.lang",
]
NAME_KEY = b"skin.name.alex="

SLIM = "geometry.humanoid.customSlim"
CLASSIC = "geometry.humanoid.custom"

VARIANTS = [
    # (名字, 排第一的皮肤, 目标几何)
    ("v20a", "Steve", CLASSIC),
    ("v20b", "Alex", SLIM),
]


def restore_alex_name(cur, official):
    """把 skin.name.alex=... 那一行换成官方母本里的内容（逐行替换，不动其它任何字节）。"""
    a = cur.split(b"\n")
    b = official.split(b"\n")
    want = next((l for l in b if l.startswith(NAME_KEY)), None)
    if want is None:
        raise SystemExit("官方母本里找不到 skin.name.alex=")
    for i, l in enumerate(a):
        if l.startswith(NAME_KEY):
            a[i] = want
            return b"\n".join(a)
    raise SystemExit("当前包的语言文件里找不到 skin.name.alex=")


def build(v19, official, out_dir, tag, first, target):
    z19 = zipfile.ZipFile(v19)
    zoff = zipfile.ZipFile(official)

    defs = json.loads(z19.read(SKINDEFS).decode("utf-8"))
    for s in defs["skins"]:
        s["geometry"] = target                      # 所有皮肤统一成目标体型
    by_name = {s["name"].lower(): s for s in defs["skins"]}
    ordered = [by_name.pop(first.lower())]          # 目标皮肤排第一 = 默认
    ordered.extend(by_name.values())
    defs["skins"] = ordered
    payload = json.dumps(defs, ensure_ascii=False, indent=1).encode("utf-8")

    out = os.path.join(out_dir, "%s-unsigned.apk" % tag)
    replaced = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in z19.infolist():
            n = item.filename
            if n == SKINDEFS:
                data = payload
                replaced.append("skindefs.json")
            elif n in ALEX:
                data = zoff.read(n)                 # 原版 Alex 贴图
                replaced.append(os.path.basename(n))
            elif n in LANG_FILES:
                data = restore_alex_name(z19.read(n), zoff.read(n))   # 玩家名还原成官方原版
                replaced.append(os.path.basename(n))
            else:
                data = z19.read(n)
            zi = zipfile.ZipInfo(n, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zo.writestr(zi, data)

    print("  %s → %s" % (tag, out))
    print("    默认皮肤: %s（数组第一条）" % first)
    print("    全部 geometry: %s" % target.replace("geometry.humanoid.", ""))
    print("    替换: %s" % ", ".join(replaced))
    print("    条数: %d（与 v19 相同结构）" % len(z19.infolist()))
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    v19, official, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    for p in (v19, official):
        if not os.path.exists(p):
            print("缺少文件: %s" % p)
            return 1
    os.makedirs(out_dir, exist_ok=True)
    print("从 v19 + 官方母本生成底包：")
    for tag, first, target in VARIANTS:
        build(v19, official, out_dir, tag, first, target)
    print()
    print("下一步（签名 + 注入导入按钮）：")
    print('  java -cp <desktop-classes> DesktopHarness <xxx-unsigned.apk> <成品.apk> '
          '<assetsDir> - - slim <assets/mc-import.js>')
    return 0


if __name__ == "__main__":
    sys.exit(main())
