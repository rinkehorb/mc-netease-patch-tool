"""重排 skinpacks/Base/skindefs.json 里 skins 数组的顺序，用来做实验。

为什么要这个：
    未改动的 v19 里，skindefs.json 的顺序是 Alex(细) / Steve(粗) / Dummy，
    而游戏实际默认用的是 **Alex**。到底是"按数组第一条选"，还是"引擎硬编码 alex"，
    靠调换顺序就能一次问清楚：
        把 Steve 排到第一位 → 全新安装后
            显示 Steve（= 原始 Steve 贴图）+ 4px  → 说明按顺序
            仍显示 Miku（= v19 的 alex 贴图）+ 3px → 说明引擎硬编码 alex

用法：
    python reorder_skindefs.py <源APK> <输出APK> [顺序]     顺序默认 steve,alex,dummy

注意：只改 skindefs.json 的条目顺序，**不动任何 geometry 值**
（Alex 仍是 customSlim=细、Steve 仍是 custom=粗），否则实验就没意义了。
输出的 APK 是未签名的 —— 交给 DesktopHarness 重新签名即可（传 skin=- 时它不会碰 skindefs）。
"""
import json
import os
import shutil
import sys
import zipfile

SKINDEFS = "assets/resource_packs/skins/skinpacks/Base/skindefs.json"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    order = (sys.argv[3] if len(sys.argv) > 3 else "steve,alex,dummy").split(",")

    z = zipfile.ZipFile(src)
    defs = json.loads(z.read(SKINDEFS).decode("utf-8"))
    print("  原顺序: " + " / ".join("%s(%s)" % (s["name"], s["geometry"].replace("geometry.humanoid.", ""))
                                    for s in defs["skins"]))

    by_name = {s["name"].lower(): s for s in defs["skins"]}
    new_skins = []
    for n in order:
        n = n.strip().lower()
        if n in by_name:
            new_skins.append(by_name.pop(n))
    new_skins.extend(by_name.values())          # 剩下的按原顺序接在后面
    defs["skins"] = new_skins
    print("  新顺序: " + " / ".join("%s(%s)" % (s["name"], s["geometry"].replace("geometry.humanoid.", ""))
                                    for s in defs["skins"]))

    payload = json.dumps(defs, ensure_ascii=False, indent=1).encode("utf-8")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = payload if item.filename == SKINDEFS else zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    print("  写出: %s (%.1f MB)" % (dst, os.path.getsize(dst) / 1024 / 1024))
    print("  注意：这是未签名包，只给 DesktopHarness 当输入用")
    return 0


if __name__ == "__main__":
    sys.exit(main())
