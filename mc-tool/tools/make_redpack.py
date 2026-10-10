"""造一个"纯红皮肤"资源包，用来验证游戏到底读哪一份玩家贴图。

背景（真机实测）：
    工具原本改的是 assets/resource_packs/skins/skinpacks/Base/*.png，
    但把四张全换成 Miku 之后，游戏里仍然渲染原版 Steve —— 说明那张不是游戏用的。
    vanilla 包里另有 textures/entity/{steve,alex,char,dummy}.png，
    其中 steve.png(1350B) 与皮肤包里的完全同尺寸，高度怀疑游戏用的是这一份。

这个包通过工具的「资源包叠加」功能覆盖进 assets/resource_packs/vanilla/，
所以只要路径写对，就会命中 vanilla/textures/entity/*.png。

用法: python make_redpack.py [颜色 R,G,B]
"""
import json
import os
import struct
import sys
import zipfile
import zlib

W = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(W, "调试记录")

# 玩家贴图（vanilla 包里那几个）
TARGETS = [
    "textures/entity/steve.png",
    "textures/entity/alex.png",
    "textures/entity/char.png",
    "textures/entity/dummy.png",
]


def make_png(w, h, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def main():
    rgb = (255, 0, 0)
    if len(sys.argv) > 1:
        rgb = tuple(int(x) for x in sys.argv[1].split(","))
    png = make_png(64, 64, rgb)
    png_path = os.path.join(OUT_DIR, "red64.png")
    open(png_path, "wb").write(png)
    print("  贴图: %s (%d 字节, RGB%s)" % (png_path, len(png), rgb))

    manifest = {
        "format_version": 1,
        "header": {
            "name": "redskin-test",
            "description": "只为了验证玩家贴图位置",
            "uuid": "11111111-2222-3333-4444-555555555555",
            "version": [1, 0, 0],
        },
        "modules": [{
            "type": "resources",
            "uuid": "66666666-7777-8888-9999-aaaaaaaaaaaa",
            "version": [1, 0, 0],
        }],
    }
    pack = os.path.join(OUT_DIR, "redskin.mcpack")
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for t in TARGETS:
            z.writestr(t, png)
    with zipfile.ZipFile(pack) as z:
        print("  资源包: %s" % pack)
        for n in z.namelist():
            print("    %-34s %d 字节" % (n, z.getinfo(n).file_size))
    print()
    print("  覆盖后 APK 里的路径会是：")
    for t in TARGETS:
        print("    assets/resource_packs/vanilla/" + t)


if __name__ == "__main__":
    main()
