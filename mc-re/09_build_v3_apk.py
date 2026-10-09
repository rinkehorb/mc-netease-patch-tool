#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3 重打包：在原 APK 基础上替换 classes.dex + 3 个皮肤资源条目，
其余条目逐字节原样复制 + 4 字节对齐。逻辑与 02_build_apk.py 相同。

用法： python 09_build_v3_apk.py <src.apk> <classes.dex> <out.apk>
"""
import os
import struct
import sys
import zlib
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "original", "Minecraft.apk")
DEX = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "patched_v3", "classes.dex")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, "patched_v3", "Minecraft-unsigned.apk")
A3 = os.path.join(HERE, "v3_assets")

# 额外替换：条目名 -> 本地新文件
EXTRA = {
    "assets/resource_packs/skins/skinpacks/Base/skindefs.json": os.path.join(A3, "skindefs.json"),
    "assets/resource_packs/skins/skinpacks/Base/alex.png": os.path.join(A3, "alex.png"),
    "assets/resource_packs/skins/skinpacks/Base/alex_dev.png": os.path.join(A3, "alex_dev.png"),
}

ALIGN = 4
ZIP_STORED = 0
ZIP_DEFLATED = 8


def dos_time_date(dt):
    return ((dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2),
            ((max(dt[0], 1980) - 1980) << 9) | (dt[1] << 5) | dt[2])


def deflate_raw(data, level=9):
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()


def main():
    with open(DEX, "rb") as f:
        new_dex = f.read()
    print("新 classes.dex: %d 字节" % len(new_dex))
    for entry, path in EXTRA.items():
        print("额外替换: %s (%d B)" % (entry, os.path.getsize(path)))

    zin = zipfile.ZipFile(SRC, "r")
    if os.path.exists(OUT):
        os.remove(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    n_copy = n_skip = n_extra = 0
    with open(OUT, "wb") as f:
        central = []
        offset = 0
        for info in zin.infolist():
            name = info.filename
            if name.startswith("META-INF/"):
                n_skip += 1
                continue

            if name == "classes.dex":
                raw = new_dex
            elif name in EXTRA:
                with open(EXTRA[name], "rb") as ef:
                    raw = ef.read()
                n_extra += 1
            else:
                raw = zin.read(name)

            method = info.compress_type
            if method == ZIP_STORED:
                payload, usize, csize = raw, len(raw), len(raw)
                crc = zlib.crc32(raw) & 0xFFFFFFFF
            else:
                method = ZIP_DEFLATED
                payload = deflate_raw(raw)
                usize, csize = len(raw), len(payload)
                crc = zlib.crc32(raw) & 0xFFFFFFFF

            name_b = name.encode("utf-8")
            flags = 0x0800
            mtime, mdate = dos_time_date(info.date_time)

            extra = b""
            if method == ZIP_STORED:
                base = offset + 30 + len(name_b)
                pad = (-base) % ALIGN
                if pad:
                    if pad < 4:
                        pad += 4
                    extra = struct.pack("<HH", 0xD935, pad - 4) + b"\x00" * (pad - 4)

            f.write(struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, method,
                                mtime, mdate, crc, csize, usize,
                                len(name_b), len(extra)))
            f.write(name_b)
            f.write(extra)
            f.write(payload)

            central.append((name_b, flags, method, mtime, mdate, crc, csize, usize,
                            extra, info.external_attr, offset))
            offset += 30 + len(name_b) + len(extra) + csize
            n_copy += 1

        cd_offset = offset
        for (name_b, flags, method, mtime, mdate, crc, csize, usize,
             extra, extattr, lho) in central:
            f.write(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50,
                                20, 20, flags, method, mtime, mdate, crc, csize, usize,
                                len(name_b), len(extra), 0, 0, 0, extattr, lho))
            f.write(name_b)
            f.write(extra)
        cd_size = f.tell() - cd_offset
        f.write(struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, n_copy, n_copy,
                            cd_size, cd_offset, 0))

    print("复制条目 %d，丢弃旧签名 %d，额外替换 %d" % (n_copy, n_skip, n_extra))
    print("输出: %s (%d 字节)" % (OUT, os.path.getsize(OUT)))

    # ---------------- 自检 ----------------
    z = zipfile.ZipFile(OUT)
    bad = z.testzip()
    print("testzip          :", "OK" if bad is None else ("BAD " + bad))
    orig = zipfile.ZipFile(SRC)
    oi = {i.filename: i for i in orig.infolist()}
    ni = {i.filename: i for i in z.infolist()}
    keep = {n for n in oi if not n.startswith("META-INF/")}
    print("缺失条目         :", sorted(keep - set(ni)) or "无")
    print("多出条目         :", sorted(set(ni) - keep) or "无")
    changed = [n for n in keep if n != "classes.dex" and n not in EXTRA
               and orig.read(n) != z.read(n)]
    print("非预期条目差异   :", changed or "无")
    exp = [n for n in EXTRA if z.read(n) != open(EXTRA[n], "rb").read()]
    print("预期替换条目差异 :", "全部与设计一致" if not exp else exp)
    print("classes.dex 匹配 :", z.read("classes.dex") == new_dex)
    print("resources.arsc   :", "原样" if z.read("resources.arsc") == orig.read("resources.arsc") else "变了!")
    print("AndroidManifest  :", "原样" if z.read("AndroidManifest.xml") == orig.read("AndroidManifest.xml") else "变了!")

    stored = [i for i in z.infolist() if i.compress_type == ZIP_STORED]
    bad_align = []
    for i in stored:
        data_off = i.header_offset + 30 + len(i.filename.encode("utf-8")) + len(i.extra)
        if data_off % ALIGN:
            bad_align.append((i.filename, data_off % ALIGN))
    print("未压缩条目 %d 个，未对齐 %d 个" % (len(stored), len(bad_align)))


if __name__ == "__main__":
    main()
