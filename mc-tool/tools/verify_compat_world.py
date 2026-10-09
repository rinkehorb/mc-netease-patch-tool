import zipfile, io, os, sys, hashlib

D = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace"
SRC = r"C:\Users\Administrator\DoubaoWork\chats\LogicGates.zip"

def level_dat_from(path):
    z = zipfile.ZipFile(path)
    best = None
    for n in z.namelist():
        nn = n.replace("\\", "/")
        if nn.lower().endswith("level.dat"):
            d = nn.rsplit("/", 1)[0] + "/" if "/" in nn else ""
            if best is None or len(d) < len(best[1]): best = (nn, d)
    return z.read(best[0])

def parse(d):
    p = [0]
    def u1():
        v = d[p[0]]; p[0] += 1; return v
    def u2():
        import struct; v = struct.unpack_from("<H", d, p[0])[0]; p[0] += 2; return v
    def i4():
        import struct; v = struct.unpack_from("<i", d, p[0])[0]; p[0] += 4; return v
    def s():
        n = u2(); v = d[p[0]:p[0]+n].decode("utf-8", "replace"); p[0] += n; return v
    def pl(t):
        import struct
        if t == 1: p[0] += 1; return None
        if t == 2: p[0] += 2; return None
        if t == 3: return i4()
        if t == 4: p[0] += 8; return None
        if t == 5: p[0] += 4; return None
        if t == 6: p[0] += 8; return None
        if t == 7:
            n = i4(); p[0] += n; return None
        if t == 8: return s()
        if t == 9:
            et = u1(); n = i4()
            return [pl(et) for _ in range(n)]
        if t == 10:
            o = {}
            while True:
                tt = u1()
                if tt == 0: break
                nm = s(); o[nm] = pl(tt)
            return o
        if t == 11:
            n = i4(); return [i4() for _ in range(n)]
    t = u1(); s()
    return pl(t)

def nbt_of(blob):
    if blob[0] not in (0x0a, 0x0b) and blob[8] in (0x0a, 0x0b):
        return blob[8:]
    return blob

orig = level_dat_from(SRC)
print("原始 level.dat  长度", len(orig), " sha256", hashlib.sha256(orig).hexdigest()[:24])
t = parse(nbt_of(orig))
print("   StorageVersion =", t["StorageVersion"], " lastOpenedWithVersion =", t["lastOpenedWithVersion"])
print()

for tag in ("A", "B"):
    p = os.path.join(D, f"LogicGates-兼容{tag}.mcworld")
    b = level_dat_from(p)
    n = nbt_of(b)
    tr = parse(n)
    print(f"变体 {tag}: {os.path.basename(p)}  ({os.path.getsize(p)} B)")
    print("   level.dat 长度", len(b), " sha256", hashlib.sha256(b).hexdigest()[:24])
    print("   StorageVersion =", tr["StorageVersion"], "  lastOpenedWithVersion =", tr["lastOpenedWithVersion"])

    # 逐字节 diff
    assert len(b) == len(orig), "长度变了！原 %d 新 %d" % (len(orig), len(b))
    diff = [i for i in range(len(orig)) if orig[i] != b[i]]
    print(f"   与原始逐字节差异: {len(diff)} 字节 @ {[hex(i) for i in diff]}")
    # 检查除这些字节外完全一致
    ok = all(orig[i] == b[i] for i in range(len(orig)) if i not in diff)
    print("   其余字节完全一致:", ok)

    # 其余键是否一个没动
    keys_o = set(t.keys()); keys_n = set(tr.keys())
    print("   键集合一致:", keys_o == keys_n)
    differing = [k for k in keys_o if t[k] != tr[k]]
    print("   值有变化的键:", differing)
    print()

# 结构检查：level.dat 是否在 zip 根目录
import zipfile as zf
for tag in ("A", "B"):
    p = os.path.join(D, f"LogicGates-兼容{tag}.mcworld")
    z = zf.ZipFile(p)
    names = z.namelist()
    root_level = "level.dat" in names
    print(f"变体 {tag}: level.dat 在根目录 = {root_level}   条目 {len(names)}: {sorted(names)}")
