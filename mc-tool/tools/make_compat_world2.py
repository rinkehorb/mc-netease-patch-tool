"""按客户端真实值重新生成兼容存档。

修正：客户端版本不是 .so 里的 "1.2.0.4"（那是 libcurl 区域的库版本号），
而是客户端自建世界写进去的 lastOpenedWithVersion = [1,1,3,50]。
StorageVersion 目标 = 5（同样来自客户端自建世界，与 .so 的
SharedConstants::CurrentStorageVersion 一致，两边互相验证过）。

target_version  : [1,1,3,50]  客户端 GameVersion::current()
target_storage  : 5          客户端 SharedConstants::CurrentStorageVersion
target_network  : 113        客户端自建世界的 NetworkVersion
"""
import zipfile, struct, os, gzip, zlib

SRC = r"C:\Users\Administrator\DoubaoWork\chats\LogicGates.zip"
OUTDIR = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace"

TARGET_VERSION = [1, 1, 3, 50]
TARGET_STORAGE = 5
TARGET_NETWORK = 113


class W:
    def __init__(s, d): s.d = d; s.p = 0
    def u1(s):
        v = s.d[s.p]; s.p += 1; return v
    def i4(s):
        v = struct.unpack_from("<i", s.d, s.p)[0]; s.p += 4; return v
    def u2(s):
        v = struct.unpack_from("<H", s.d, s.p)[0]; s.p += 2; return v
    def s(s):
        n = s.u2(); v = s.d[s.p:s.p+n].decode("utf-8", "replace"); s.p += n; return v
    def skip(s, t):
        if t == 1: s.p += 1
        elif t == 2: s.p += 2
        elif t == 3:
            off = s.p; s.p += 4; return ("int", off)
        elif t == 4: s.p += 8
        elif t == 5: s.p += 4
        elif t == 6: s.p += 8
        elif t == 7:
            n = s.i4(); s.p += n
        elif t == 8: s.s()
        elif t == 9:
            et = s.u1(); n = s.i4()
            if et == 3:
                off = s.p; s.p += 4*n; return ("intlist", off, n)
            for _ in range(n): s.skip(et)
        elif t == 10:
            while True:
                tt = s.u1()
                if tt == 0: break
                s.s(); s.skip(tt)
        elif t == 11:
            n = s.i4(); s.p += 4*n
        return None


def find(nbt, keys):
    w = W(nbt)
    assert w.u1() == 10
    w.s()
    out = {}
    while True:
        t = w.u1()
        if t == 0: break
        nm = w.s()
        info = w.skip(t)
        if nm in keys: out[nm] = (t, info)
    return out


def load(blob):
    if blob[:2] == b"\x1f\x8b": return b"", gzip.decompress(blob)
    if blob[:1] == b"\x78":
        try: return b"", zlib.decompress(blob)
        except Exception: pass
    if blob[0] not in (0x0a, 0x0b) and len(blob) > 8 and blob[8] in (0x0a, 0x0b):
        return blob[:8], blob[8:]
    return b"", blob


def patch(blob, do_storage, do_network):
    header, nbt = load(blob)
    f = find(nbt, {"StorageVersion", "lastOpenedWithVersion", "NetworkVersion"})
    out = bytearray(nbt)
    ch = []

    _, (_, off, n) = f["lastOpenedWithVersion"]
    old = [struct.unpack_from("<i", out, off+4*i)[0] for i in range(n)]
    for i in range(n):
        struct.pack_into("<i", out, off+4*i, TARGET_VERSION[i] if i < len(TARGET_VERSION) else 0)
    new = [struct.unpack_from("<i", out, off+4*i)[0] for i in range(n)]
    ch.append(f"lastOpenedWithVersion {old} -> {new}")

    if do_storage:
        _, (_, off) = f["StorageVersion"]
        o = struct.unpack_from("<i", out, off)[0]
        struct.pack_into("<i", out, off, TARGET_STORAGE)
        ch.append(f"StorageVersion {o} -> {TARGET_STORAGE}")

    if do_network:
        _, (_, off) = f["NetworkVersion"]
        o = struct.unpack_from("<i", out, off)[0]
        struct.pack_into("<i", out, off, TARGET_NETWORK)
        ch.append(f"NetworkVersion {o} -> {TARGET_NETWORK}")

    return header + bytes(out), ch


def main():
    z = zipfile.ZipFile(SRC)
    prefix = None
    for n in z.namelist():
        nn = n.replace("\\", "/")
        if nn.lower().endswith("level.dat"):
            d = nn.rsplit("/", 1)[0] + "/" if "/" in nn else ""
            if prefix is None or len(d) < len(prefix): prefix = d
    entries = []
    for n in z.namelist():
        nn = n.replace("\\", "/")
        if nn.endswith("/"): continue
        if prefix and not nn.startswith(prefix): continue
        entries.append((nn[len(prefix):] if prefix else nn, z.read(n)))

    print("世界根前缀:", repr(prefix), " 条目:", len(entries))
    print("目标: version=%s storage=%d network=%d" % (TARGET_VERSION, TARGET_STORAGE, TARGET_NETWORK))
    print()

    variants = [
        ("A2", False, False, "只改 lastOpenedWithVersion → [1,1,3,50]"),
        ("B2", True,  False, "再加 StorageVersion 6→5"),
        ("C2", True,  True,  "再加 NetworkVersion 200→113"),
    ]
    for tag, ds, dn, desc in variants:
        out_entries = []
        for rel, data in entries:
            if rel in ("level.dat", "level.dat_old"):
                data, ch = patch(data, ds, dn)
                print(f"  [{tag}] {rel}: " + "; ".join(ch))
            out_entries.append((rel, data))
        out = os.path.join(OUTDIR, f"LogicGates-兼容{tag}.mcworld")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
            for rel, data in out_entries:
                zo.writestr(rel, data)
        print(f"  [{tag}] {desc}  → {os.path.basename(out)}  ({os.path.getsize(out)} B)\n")


if __name__ == "__main__":
    main()
