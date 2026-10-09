"""确认客户端 GameVersion::current() 到底是什么。

之前把 .so 里的 "1.2.0.4" 当成游戏版本，但那段字符串周围全是 libcurl 的东西
（bind / resolved / content unencoding），极可能是某个库的版本号。
而客户端自建世界写进去的 lastOpenedWithVersion = [1,1,3,50] 才是 GameVersion::current()
的真实输出。这里直接把 current() 的机器码 dump 出来对一下。
"""
import zipfile, struct

APK = r"C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft-0.2.0.25445-offline-v19.apk"
z = zipfile.ZipFile(APK)
d = z.read("lib/armeabi-v7a/libminecraftpe.so")

def sections(d):
    assert d[:4] == b"\x7fELF"
    e_shoff = struct.unpack_from("<I", d, 0x20)[0]
    e_shentsize = struct.unpack_from("<H", d, 0x2e)[0]
    e_shnum = struct.unpack_from("<H", d, 0x30)[0]
    e_shstrndx = struct.unpack_from("<H", d, 0x32)[0]
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i*e_shentsize
        f = struct.unpack_from("<IIIIIIIIII", d, off)
        secs.append(dict(name=f[0], type=f[1], flags=f[2], addr=f[3], off=f[4],
                         size=f[5], link=f[6], entsize=f[9]))
    sh = secs[e_shstrndx]
    for s in secs:
        s["sname"] = d[sh["off"]+s["name"]: d.index(b"\x00", sh["off"]+s["name"])].decode("latin1")
    return secs

secs = sections(d)
def sym(want):
    for sec in secs:
        if sec["sname"] != ".dynsym": continue
        strtab = secs[sec["link"]]
        n = sec["size"] // sec["entsize"]
        for i in range(n):
            off = sec["off"] + i*sec["entsize"]
            nm, value, size, info, other, shndx = struct.unpack_from("<IIIBBH", d, off)
            end = d.index(b"\x00", strtab["off"]+nm)
            if d[strtab["off"]+nm:end].decode("latin1") == want:
                return value, size, shndx
    return None

def to_off(addr):
    for s in secs:
        if s["type"] != 8 and s["addr"] and s["addr"] <= addr < s["addr"]+s["size"]:
            return s["off"] + (addr - s["addr"]), s["sname"]
    return None, None

for want in ("_ZN11GameVersion7currentEv", "_ZN6Common20getGameVersionStringEv"):
    r = sym(want)
    print(f"{want} -> {r}")
    if not r: continue
    off, sn = to_off(r[0])
    code = d[off:off+r[1]]
    print(f"   @0x{r[0]:x} 段 {sn}  ({r[1]} 字节)")
    print("   hex:", code.hex())

# Thumb: movs Rd,#imm8 = 0x2000 | (Rd<<8) | imm8
def movs(code, i):
    h = struct.unpack_from("<H", code, i)[0]
    if (h & 0xF800) == 0x2000:
        return (h >> 8) & 7, h & 0xFF
    return None

print()
print("=== 在 GameVersion::current() 里找 movs 立即数序列 ===")
r = sym("_ZN11GameVersion7currentEv")
off, _ = to_off(r[0])
code = d[off:off+r[1]]
seq = []
for i in range(0, len(code)-1, 2):
    m = movs(code, i)
    if m: seq.append((i, m[0], m[1]))
for i, rd, imm in seq:
    print(f"   +{i:3d}  movs r{rd}, #{imm}")

print()
print("=== 全 .text 搜 8 字节模式 [1,1,3,50] / [1,2,0,4] 的 movs 序列 ===")
text = None
for s in secs:
    if s["sname"] == ".text":
        text = d[s["off"]:s["off"]+s["size"]]
        tabase = s["addr"]
        toff = s["off"]
print("  .text 大小:", len(text))
for label, vals in (("[1,1,3,50]", (1,1,3,50)), ("[1,2,0,4]", (1,2,0,4))):
    pat = b"".join(struct.pack("<H", 0x2000 | (i << 8) | v) for i, v in enumerate(vals))
    idx = text.find(pat)
    hits = []
    while idx >= 0 and len(hits) < 5:
        hits.append(idx)
        idx = text.find(pat, idx+1)
    print(f"  {label} 连续 movs 模式 {pat.hex()} → {len(hits)} 处 {[hex(tabase+h) for h in hits]}")
    # 宽松点：允许寄存器顺序变化
    loose = 0
    for i in range(len(text)-8):
        ok = True
        for k, v in enumerate(vals):
            h = struct.unpack_from("<H", text, i+2*k)[0]
            if (h & 0xF800) != 0x2000 or (h & 0xFF) != v:
                ok = False; break
        if ok:
            loose += 1
            if loose <= 5: print(f"     宽松命中 @0x{tabase+i:x}")
    print(f"     宽松命中总数: {loose}")
