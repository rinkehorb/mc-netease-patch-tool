#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建「探针版」MC APK：把只读探针脚本注入 assets/web/index.html。

做法沿用 02_build_apk.py 的整包重写策略（那套已经验证过）：
  * 只替换 assets/web/index.html 一个条目，其余 3990 个条目按原始压缩方式、
    原始时间戳、原始属性原样复制，一个字节都不改；
  * 丢掉旧的 META-INF/（旧签名必然失效）；
  * 未压缩（STORED）条目做 4 字节对齐（extra field 填充），zipalign 等价。

关键前提（已核实）：lib/*.so（#256-260）、resources.arsc（#2）、AndroidManifest.xml（#3）
全都排在 index.html（#3919）之前，所以改它的体积不会影响这些关键条目的对齐。

用法： python 50_build_probe.py
"""
import os
import struct
import zlib
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft-0.2.0.25445-offline-v19.apk"
SCRIPT = os.path.join(HERE, "probe", "probe_script.html")
OUT = os.path.join(HERE, "probe", "out", "Minecraft-probe-unsigned.apk")

TARGET = "assets/web/index.html"
MARK = "MCPROBE"

ALIGN = 4
ZIP_STORED = 0
ZIP_DEFLATED = 8


def dos_time_date(dt):
    return ((dt[3] << 11) | (dt[4] << 5) | (dt[5] // 2),
            ((max(dt[0], 1980) - 1980) << 9) | (dt[1] << 5) | dt[2])


def deflate_raw(data, level=9):
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()


def build_index_html(old_html, script):
    text = old_html.decode("utf-8")
    if MARK in text:
        raise SystemExit("index.html 里已经有探针了，别重复注入")
    idx = text.rfind("</body>")
    if idx < 0:
        raise SystemExit("index.html 里找不到 </body>")
    new_text = text[:idx] + script + "\n</body>" + text[idx + len("</body>"):]
    return new_text.encode("utf-8")


def main():
    with open(SCRIPT, "r", encoding="utf-8") as f:
        script = f.read()
    print("探针脚本: %d 字节" % len(script))

    zin = zipfile.ZipFile(SRC, "r")
    old_html = zin.read(TARGET)
    new_html = build_index_html(old_html, script)
    print("index.html: %d -> %d 字节" % (len(old_html), len(new_html)))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    replaced = 0
    n_copy = n_skip = 0
    with open(OUT, "wb") as f:
        central = []
        offset = 0
        for info in zin.infolist():
            name = info.filename
            if name.startswith("META-INF/"):
                n_skip += 1
                continue

            if name == TARGET:
                raw = new_html
                replaced += 1
            else:
                raw = zin.read(name)

            method = info.compress_type
            if method == ZIP_STORED:
                payload, usize, csize = raw, len(raw), len(raw)
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

    print("替换条目 %d，复制条目 %d，丢弃旧签名 %d" % (replaced, n_copy, n_skip))
    print("输出: %s (%d 字节)" % (OUT, os.path.getsize(OUT)))

    # ---------------- 自检 ----------------
    print("\n---- 自检 ----")
    z = zipfile.ZipFile(OUT)
    print("testzip            :", "OK" if z.testzip() is None else "BAD")
    orig = zipfile.ZipFile(SRC)
    oi = {i.filename: i for i in orig.infolist()}
    ni = {i.filename: i for i in z.infolist()}
    keep = {n for n in oi if not n.startswith("META-INF/")}
    print("缺失条目           :", sorted(keep - set(ni)) or "无")
    print("多出条目           :", sorted(set(ni) - keep) or "无")
    diff = [n for n in keep if n != TARGET and orig.read(n) != z.read(n)]
    print("除目标外内容有差异 :", diff or "无")
    got = z.read(TARGET)
    print("index.html 已注入  :", MARK.encode() in got)
    print("index.html 完整性  :", got.count(b"</html>") == 1 and got.rstrip().endswith(b"</html>"))
    for k in ("resources.arsc", "AndroidManifest.xml", "classes.dex",
              "lib/armeabi-v7a/libminecraftpe.so"):
        same = (orig.read(k) == z.read(k))
        print(f"{k:38s}: {'原样' if same else '变了!'}")

    stored = [i for i in z.infolist() if i.compress_type == ZIP_STORED]
    bad = []
    for i in stored:
        off = i.header_offset + 30 + len(i.filename.encode("utf-8")) + len(i.extra)
        if off % ALIGN:
            bad.append((i.filename, off % ALIGN))
    print("未压缩条目 %d 个，未对齐 %d 个 %s" % (len(stored), len(bad), bad[:3]))


if __name__ == "__main__":
    main()
