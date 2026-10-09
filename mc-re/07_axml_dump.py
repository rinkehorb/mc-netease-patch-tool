#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简 Android 二进制 XML (AXML) 解析器：打印元素树与常用属性，用于读 AndroidManifest。"""
import struct
import sys


class AXML:
    def __init__(self, data):
        self.d = data
        self.pos = 0
        self.strings = []
        self.events = []

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.pos)[0]
        self.pos += 4
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.pos)[0]
        self.pos += 2
        return v

    def parse(self):
        # header: type(u16)=0x0003, headerSize(u16)=8, fileSize(u32)
        assert self.u16() == 0x0003
        self.u16()  # header size
        self.u32()  # file size
        # string pool chunk: type(u16)=0x0001, headerSize(u16)=0x1c, size(u32)
        pool_start = self.pos  # 此时 self.pos = 8，即 pool chunk 起点
        assert self.u16() == 0x0001
        hsz = self.u16()
        pool_size = self.u32()  # pool total size
        sc = self.u32()  # string count
        self.u32()  # style count
        flags = self.u32()
        self.u32()  # stringsStart (aapt 的字段值不可靠，用公式重算)
        self.u32()  # styles offset
        str_offsets = [self.u32() for _ in range(sc)]
        data_start = pool_start + hsz + sc * 4  # 实证公式
        for o in str_offsets:
            p = data_start + o
            if flags & 0x100:  # UTF-8
                ulen, p2 = self._read_len(self.d, p)
                p = p2
                slen, p2 = self._read_len(self.d, p)
                p = p2
                s = self.d[p:p + slen].decode("utf-8", errors="replace")
            else:
                clen = struct.unpack_from("<H", self.d, p)[0]
                p += 2
                s = self.d[p:p + clen * 2].decode("utf-16-le", errors="replace")
            self.strings.append(s)
        self.pos = pool_start + pool_size  # 跳到字符串池 chunk 末尾
        # walk remaining chunks
        while self.pos < len(self.d):
            ctype = self.u16()
            hsize = self.u16()
            csize = self.u32()
            body = self.d[self.pos:self.pos + csize - 8]
            if ctype == 0x0180:  # resource map
                pass
            elif ctype == 0x0100:  # start namespace
                pass
            elif ctype == 0x0101:  # end namespace
                pass
            elif ctype == 0x0102:  # start element
                self._start_element(body)
            elif ctype == 0x0103:  # end element
                pass
            elif ctype == 0x0104:  # cdata
                pass
            else:
                break
            self.pos += csize - 8
        return

    @staticmethod
    def _read_len(buf, p):
        b = buf[p]
        p += 1
        if b & 0x80:
            b2 = buf[p]
            p += 1
            return ((b & 0x7F) << 8 | b2), p
        return b, p

    def _start_element(self, body):
        p = 0
        p += 4  # lineNumber
        p += 4  # comment
        ns = struct.unpack_from("<I", body, p)[0]; p += 4
        name = struct.unpack_from("<I", body, p)[0]; p += 4
        attr_start = struct.unpack_from("<H", body, p)[0]; p += 2
        attr_size = struct.unpack_from("<H", body, p)[0]; p += 2
        attr_count = struct.unpack_from("<H", body, p)[0]; p += 2
        p += 2  # id index
        p += 2  # class index
        p += 2  # style index
        attrs = []
        for _ in range(attr_count):
            ans = struct.unpack_from("<I", body, p)[0]; p += 4   # ns ref
            aname = struct.unpack_from("<I", body, p)[0]; p += 4  # name ref
            araw = struct.unpack_from("<I", body, p)[0]; p += 4   # raw string ref
            av = struct.unpack_from("<I", body, p)[0]; p += 4     # typedValue: size u16, res0 u8, dataType u8
            ad = struct.unpack_from("<I", body, p)[0]; p += 4     # data
            dtype = (av >> 24) & 0xFF
            name_str = self.strings[aname] if 0 <= aname < len(self.strings) else None
            if dtype == 0x03 and 0 <= araw < len(self.strings):
                value = self.strings[araw]
            elif dtype == 0x10:
                value = ad
            elif dtype == 0x12:
                value = bool(ad)
            elif dtype == 0x11:
                value = struct.unpack("<f", struct.pack("<I", ad))[0]
            elif dtype == 0x01:
                value = "0x%08x" % ad
            else:
                value = "type%d:0x%08x" % (dtype, ad)
            a = {"name": name_str, "value": value}
            attrs.append(a)
        el = {"name": self.strings[name] if 0 <= name < len(self.strings) else "?",
              "attrs": attrs}
        self.events.append(("start", el))


def main():
    path = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk"
    import zipfile
    z = zipfile.ZipFile(path)
    ax = AXML(z.read("AndroidManifest.xml"))
    ax.parse()
    indent = 0
    for kind, el in ax.events:
        if kind == "start":
            attrs = []
            for a in el["attrs"]:
                if a["name"] and a["value"] is not None:
                    attrs.append("%s=%s" % (a["name"], a["value"]))
            print("  " * indent + "<" + el["name"] + " " + " ".join(attrs))
            indent += 1
        else:
            indent -= 1


if __name__ == "__main__":
    main()
