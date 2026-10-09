"""把 Logic Gates 世界改成 1.2.0.4 客户端能认的样子。

只做两件事（都在副本上）：
  1. lastOpenedWithVersion  [1,2,10,1] -> [1,2,0,4]   （纯声明，零风险）
  2. StorageVersion         6 -> 5                     （Format 档位，实验性质）

level.dat 是「8 字节头 + 明文 NBT」，而且是定长字段，所以直接原地改字节即可，
不需要重新序列化整个 NBT —— 改完长度不变，其余字节一个不动。

输出两个变体，用来区分两个不匹配各自的影响：
  A: 只改 lastOpenedWithVersion
  B: 两个都改
两次 zip 都把世界根前缀剥掉（level.dat 落在根目录），符合游戏的导入要求。
"""
import zipfile, struct, os, io, sys

SRC = r"C:\Users\Administrator\DoubaoWork\chats\LogicGates.zip"
OUTDIR = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace"

TAG = {1:"Byte",2:"Short",3:"Int",4:"Long",5:"Float",6:"Double",
       7:"ByteArray",8:"String",9:"List",10:"Compound",11:"IntArray"}

class Walker:
    """只走到顶层，记录关心的键的值偏移。"""
    def __init__(self, d):
        self.d = d; self.p = 0
    def u1(self):
        v = self.d[self.p]; self.p += 1; return v
    def i2(self):
        v = struct.unpack_from("<h", self.d, self.p)[0]; self.p += 2; return v
    def u2(self):
        v = struct.unpack_from("<H", self.d, self.p)[0]; self.p += 2; return v
    def i4(self):
        v = struct.unpack_from("<i", self.d, self.p)[0]; self.p += 4; return v
    def i8(self):
        v = struct.unpack_from("<q", self.d, self.p)[0]; self.p += 8; return v
    def f4(self):
        v = struct.unpack_from("<f", self.d, self.p)[0]; self.p += 4; return v
    def f8(self):
        v = struct.unpack_from("<d", self.d, self.p)[0]; self.p += 8; return v
    def s(self):
        n = self.u2(); v = self.d[self.p:self.p+n].decode("utf-8","replace"); self.p += n; return v

    def skip(self, t):
        if t == 1: self.p += 1; return None
        if t == 2: self.p += 2; return None
        if t == 3:
            off = self.p; self.p += 4; return ("int", off)
        if t == 4: self.p += 8; return None
        if t == 5: self.p += 4; return None
        if t == 6: self.p += 8; return None
        if t == 7:
            n = self.i4(); self.p += n; return None
        if t == 8:
            self.s(); return None
        if t == 9:
            et = self.u1(); n = self.i4()
            if et == 3:
                off = self.p; self.p += 4*n
                return ("intlist", off, et, n)
            for _ in range(n): self.skip(et)
            return None
        if t == 10:
            while True:
                tt = self.u1()
                if tt == 0: break
                self.s(); self.skip(tt)
            return None
        if t == 11:
            n = self.i4(); self.p += 4*n; return None
        raise ValueError("tag %d" % t)

def find_keys(nbt, keys):
    w = Walker(nbt)
    assert w.u1() == 10, "根不是 compound"
    w.s()                       # 根名（空）
    found = {}
    while True:
        t = w.u1()
        if t == 0: break
        name = w.s()
        info = w.skip(t)
        if name in keys:
            found[name] = (t, info)
    return found

def load(blob):
    """返回 (header8, nbt)"""
    if blob[:2] == b"\x1f\x8b":
        import gzip; return b"", gzip.decompress(blob)
    if blob[:1] == b"\x78":
        import zlib
        try: return b"", zlib.decompress(blob)
        except Exception: pass
    if blob[0] not in (0x0a, 0x0b) and blob[8] in (0x0a, 0x0b):
        return blob[:8], blob[8:]
    return b"", blob

def patch_level_dat(blob, do_storage):
    header, nbt = load(blob)
    found = find_keys(nbt, {"StorageVersion", "lastOpenedWithVersion"})
    out = bytearray(nbt)
    changes = []

    t, info = found["lastOpenedWithVersion"]
    kind, off, et, n = info
    old = [struct.unpack_from("<i", out, off + 4*i)[0] for i in range(n)]
    new = [1, 2, 0, 4]
    for i in range(min(n, len(new))):
        struct.pack_into("<i", out, off + 4*i, new[i])
    changes.append(f"lastOpenedWithVersion {old} -> {[struct.unpack_from('<i', out, off+4*i)[0] for i in range(n)]}")

    if do_storage:
        t, info = found["StorageVersion"]
        kind, off = info
        old = struct.unpack_from("<i", out, off)[0]
        struct.pack_into("<i", out, off, 5)
        changes.append(f"StorageVersion {old} -> 5")

    return header + bytes(out), changes

def main():
    z = zipfile.ZipFile(SRC)
    # 世界根前缀
    prefix = None
    for n in z.namelist():
        nn = n.replace("\\", "/")
        if nn.lower().endswith("level.dat"):
            d = nn.rsplit("/", 1)[0] + "/" if "/" in nn else ""
            if prefix is None or len(d) < len(prefix): prefix = d
    print("世界根前缀:", repr(prefix))

    # 组装展平后的条目
    entries = []
    for n in z.namelist():
        nn = n.replace("\\", "/")
        if nn.endswith("/"): continue
        if prefix and not nn.startswith(prefix): continue
        rel = nn[len(prefix):] if prefix else nn
        data = z.read(n)
        entries.append([rel, data])
    print("世界内条目:", [e[0] for e in entries])

    for tag, do_storage in (("A", False), ("B", True)):
        out_entries = []
        for rel, data in entries:
            if rel in ("level.dat", "level.dat_old"):
                data, ch = patch_level_dat(data, do_storage)
                print(f"  [{tag}] {rel}: " + "; ".join(ch))
            out_entries.append((rel, data))

        out = os.path.join(OUTDIR, f"LogicGates-兼容{tag}.mcworld")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
            for rel, data in out_entries:
                zo.writestr(rel, data)
        print(f"  [{tag}] 输出 {out}  ({os.path.getsize(out)} B)")

if __name__ == "__main__":
    main()
