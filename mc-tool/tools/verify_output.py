#!/usr/bin/env python3
"""核对「工具生成的改包」到底改了哪些东西 —— 逐项对照源包。

用法:
    python verify_output.py <产物.apk> <源APK> [资源包.mcpack] [皮肤.png]

它检查（这些都是真机上出过问题的地方）：
  ① 导入界面脚本的版本 —— 源包里可能带着旧脚本，工具必须把它换成新的
  ② 玩家名称 —— assets/resource_packs/vanilla/texts/*.lang 里的 skin.name.*
  ③ 皮肤 —— skins/skinpacks/Base/*.png 是否等于给的皮肤图
  ④ 资源包 —— 抽查包内文件是否真的覆盖进了 vanilla/
  ⑤ 不该动的 —— resources.arsc / AndroidManifest.xml / classes.dex / lib/*.so 必须逐字节一致
"""
import hashlib
import sys
import zipfile


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    out_path, src_path = sys.argv[1], sys.argv[2]
    pack_path = sys.argv[3] if len(sys.argv) > 3 else None
    skin_path = sys.argv[4] if len(sys.argv) > 4 else None

    out = zipfile.ZipFile(out_path)
    src = zipfile.ZipFile(src_path)
    on = set(out.namelist())
    sn = set(src.namelist())

    print("产物: %s" % out_path)
    print("源包: %s" % src_path)
    print("条目数: 源 %d → 产物 %d" % (len(sn), len(on)))
    print()

    # ---------------------------------------------------------------- ① 导入脚本
    print("① 导入界面脚本")
    if "assets/web/index.html" in on:
        h = out.read("assets/web/index.html").decode("utf-8", "replace")
        ver = "新版（找 .png）" if "var CANDS" in h else (
            "中间版（找 Android/media+.zip）" if "var DIRS" in h else (
                "最早版（写死 Download + .zip）" if "var DIR = " in h else "没有注入过"))
        print("   index.html %d 字节 → 版本判定: %s" % (len(h), ver))
        print("   含 __MCIMPORT__:", "__MCIMPORT__" in h, "  <script> 块数:", h.count("<script"))
        if "var CANDS" in h:
            i = h.find("var CANDS")
            print("   " + h[i:i + 90].replace("\n", " ").replace("  ", " "))
        else:
            print("   ⚠️ 不是最新版！源包里可能是旧脚本，而工具没有替换掉它。")
    else:
        print("   ⚠️ 产物里没有 assets/web/index.html")
    print()

    # ---------------------------------------------------------------- ② 玩家名称
    print("② 玩家名称（skin.name.*）")
    for lang in ("zh_CN", "en_US"):
        key = "assets/resource_packs/vanilla/texts/%s.lang" % lang
        if key not in on:
            print("   %s: 不存在" % key)
            continue
        a = out.read(key)
        b = src.read(key) if key in sn else b""
        lines = [l for l in a.decode("utf-8", "replace").splitlines() if "skin.name." in l]
        print("   %s: %d 字节（源 %d 字节）%s" % (lang, len(a), len(b), "" if a != b else "  ⚠️ 没变"))
        for l in lines:
            print("      " + l)
    print()

    # ---------------------------------------------------------------- ③ 皮肤
    print("③ 皮肤")
    base = "assets/resource_packs/skins/skinpacks/Base/"
    skin = open(skin_path, "rb").read() if skin_path else None
    if skin:
        print("   给的皮肤图: %d 字节  sha=%s" % (len(skin), sha(skin)))
    for nm in ("alex.png", "alex_dev.png", "steve.png", "steve_dev.png"):
        k = base + nm
        if k not in on:
            print("   %-14s 产物里没有" % nm)
            continue
        d = out.read(k)
        old = src.read(k) if k in sn else b""
        flag = ""
        if skin is not None:
            flag = "  == 给的皮肤 ✔" if d == skin else "  ≠ 给的皮肤"
        print("   %-14s %d 字节（源 %d）%s" % (nm, len(d), len(old), flag))
    for nm in ("skindefs.json",):
        k = base + nm
        if k in on and k in sn:
            print("   %-14s %s" % (nm, "有改动" if out.read(k) != src.read(k) else "没变"))
    print()

    # ---------------------------------------------------------------- ④ 资源包
    print("④ 资源包覆盖")
    if pack_path:
        pk = zipfile.ZipFile(pack_path)
        files = [x for x in pk.namelist() if not x.endswith("/")]
        print("   资源包内 %d 个文件" % len(files))
        same = diff = missing = 0
        for x in files:
            k = "assets/resource_packs/vanilla/" + x
            if k not in on:
                missing += 1
            elif out.read(k) == pk.read(x):
                same += 1
            else:
                diff += 1
        print("   覆盖结果: 内容一致 %d / 不一致 %d / 产物里没有 %d" % (same, diff, missing))
        # 包元数据不该被覆盖
        for m in ("manifest.json", "pack_icon.png"):
            k = "assets/resource_packs/vanilla/" + m
            if k in on and k in sn:
                print("   %-16s %s（应与源包一致）" % (m, "没被覆盖 ✔" if out.read(k) == src.read(k) else "被覆盖了 ✗"))
    else:
        print("   （没给资源包，跳过）")
    print()

    # ---------------------------------------------------------------- ⑤ 不该动的
    print("⑤ 绝对不该动的（要逐字节一致）")
    for k in ("resources.arsc", "AndroidManifest.xml", "classes.dex",
              "lib/armeabi-v7a/libminecraftpe.so"):
        if k in on and k in sn:
            a, b = out.read(k), src.read(k)
            print("   %-38s %s  (%d 字节)" % (k, "一致 ✔" if a == b else "变了 ✗", len(b)))
    print()
    print("产物 testzip:", "OK" if out.testzip() is None else "损坏 ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
