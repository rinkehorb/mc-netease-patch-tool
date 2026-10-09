#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4 重打包：v3 dex + 6 个 assets 替换（lang 改名 / base.json 粗手臂化 / v3 皮肤三件）。"""
import os, struct, sys, zlib, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "original", "Minecraft.apk")
DEX = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "patched_v3", "classes.dex")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "patched_v4", "Minecraft-unsigned.apk")
A4 = os.path.join(HERE, "v4_assets")

EXTRA = {
    "assets/resource_packs/skins/skinpacks/Base/skindefs.json": os.path.join(A4, "skindefs.json"),
    "assets/resource_packs/skins/skinpacks/Base/alex.png": os.path.join(A4, "alex.png"),
    "assets/resource_packs/skins/skinpacks/Base/alex_dev.png": os.path.join(A4, "alex_dev.png"),
    "assets/resource_packs/skins/skinpacks/Base/base.json": os.path.join(A4, "base.json"),
    "assets/resource_packs/vanilla/texts/zh_CN.lang": os.path.join(A4, "zh_CN.lang"),
    "assets/resource_packs/vanilla/texts/en_US.lang": os.path.join(A4, "en_US.lang"),
}
ALIGN = 4; ZIP_STORED = 0; ZIP_DEFLATED = 8

def dos_time_date(dt):
    return ((dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2),
            ((max(dt[0], 1980) - 1980) << 9) | (dt[1] << 5) | dt[2])

def deflate_raw(data, level=9):
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()

def main():
    new_dex = open(DEX, "rb").read()
    print("dex:", len(new_dex), "| 额外替换:", len(EXTRA), "项")
    zin = zipfile.ZipFile(SRC, "r")
    if os.path.exists(OUT): os.remove(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n_copy = n_skip = n_extra = 0
    with open(OUT, "wb") as f:
        central = []; offset = 0
        for info in zin.infolist():
            name = info.filename
            if name.startswith("META-INF/"): n_skip += 1; continue
            if name == "classes.dex": raw = new_dex
            elif name in EXTRA: raw = open(EXTRA[name], "rb").read(); n_extra += 1
            else: raw = zin.read(name)
            method = info.compress_type
            if method == ZIP_STORED: payload, usize, csize = raw, len(raw), len(raw)
            else:
                method = ZIP_DEFLATED; payload = deflate_raw(raw); usize, csize = len(raw), len(payload)
            crc = zlib.crc32(raw) & 0xFFFFFFFF
            name_b = name.encode("utf-8"); flags = 0x0800
            mtime, mdate = dos_time_date(info.date_time)
            extra = b""
            if method == ZIP_STORED:
                base = offset + 30 + len(name_b); pad = (-base) % ALIGN
                if pad:
                    if pad < 4: pad += 4
                    extra = struct.pack("<HH", 0xD935, pad - 4) + b"\x00" * (pad - 4)
            f.write(struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, method, mtime, mdate,
                                crc, csize, usize, len(name_b), len(extra)))
            f.write(name_b); f.write(extra); f.write(payload)
            central.append((name_b, flags, method, mtime, mdate, crc, csize, usize, extra, info.external_attr, offset))
            offset += 30 + len(name_b) + len(extra) + csize; n_copy += 1
        cd_offset = offset
        for (name_b, flags, method, mtime, mdate, crc, csize, usize, extra, extattr, lho) in central:
            f.write(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, flags, method, mtime, mdate,
                                crc, csize, usize, len(name_b), len(extra), 0, 0, 0, extattr, lho))
            f.write(name_b); f.write(extra)
        cd_size = f.tell() - cd_offset
        f.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, n_copy, n_copy, cd_size, cd_offset, 0))
    print("复制 %d，丢签名 %d，替换 %d -> %s (%d B)" % (n_copy, n_skip, n_extra, OUT, os.path.getsize(OUT)))

    z = zipfile.ZipFile(OUT); orig = zipfile.ZipFile(SRC)
    print("testzip:", z.testzip() is None and "OK" or "BAD")
    keep = {i.filename for i in orig.infolist() if not i.filename.startswith("META-INF/")}
    ni = {i.filename for i in z.infolist()}
    print("缺失:", sorted(keep - ni) or "无", "| 多出:", sorted(ni - keep) or "无")
    bad = [n for n in keep if n != "classes.dex" and n not in EXTRA and orig.read(n) != z.read(n)]
    print("非预期差异:", bad or "无")
    exp = [n for n in EXTRA if z.read(n) != open(EXTRA[n], "rb").read()]
    print("预期替换:", "全部一致" if not exp else exp)
    print("dex 匹配:", z.read("classes.dex") == new_dex)
    print("arsc 原样:", z.read("resources.arsc") == orig.read("resources.arsc"))
    print("Manifest 原样:", z.read("AndroidManifest.xml") == orig.read("AndroidManifest.xml"))
    stored = [i for i in z.infolist() if i.compress_type == ZIP_STORED]
    ba = [i.filename for i in stored if (i.header_offset + 30 + len(i.filename) + len(i.extra)) % ALIGN]
    print("未压缩 %d，未对齐 %d" % (len(stored), len(ba)))

if __name__ == "__main__":
    main()
