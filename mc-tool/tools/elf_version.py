import zipfile, struct, sys, re

APK = r"C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft-0.2.0.25445-offline-v19.apk"

def read_so(name):
    z = zipfile.ZipFile(APK)
    return z.read(name)

def elf_sections(d):
    assert d[:4] == b"\x7fELF", "not ELF"
    is64 = d[4] == 2
    le = d[5] == 1
    e = "<" if le else ">"
    if is64:
        e_shoff = struct.unpack_from(e+"Q", d, 0x28)[0]
        e_shentsize = struct.unpack_from(e+"H", d, 0x3a)[0]
        e_shnum = struct.unpack_from(e+"H", d, 0x3c)[0]
        e_shstrndx = struct.unpack_from(e+"H", d, 0x3e)[0]
    else:
        e_shoff = struct.unpack_from(e+"I", d, 0x20)[0]
        e_shentsize = struct.unpack_from(e+"H", d, 0x2e)[0]
        e_shnum = struct.unpack_from(e+"H", d, 0x30)[0]
        e_shstrndx = struct.unpack_from(e+"H", d, 0x32)[0]
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i*e_shentsize
        if is64:
            name, typ, flags, addr, offset, size, link, info, align, entsize = struct.unpack_from(e+"IIQQQQIIQQ", d, off)
        else:
            name, typ, flags, addr, offset, size, link, info, align, entsize = struct.unpack_from(e+"IIIIIIIIII", d, off)
        secs.append(dict(name=name, type=typ, addr=addr, off=offset, size=size,
                         link=link, entsize=entsize, is64=is64, le=le))
    # shstrtab
    sh = secs[e_shstrndx]
    for s in secs:
        n = d[sh["off"]+s["name"]: d.index(b"\x00", sh["off"]+s["name"])].decode("latin1")
        s["sname"] = n
    return secs, is64, e

def find_sym(d, secs, is64, e, want):
    # 遍历 .dynsym 和 .symtab
    for sec in secs:
        if sec["sname"] not in (".dynsym", ".symtab"):
            continue
        strtab = secs[sec["link"]]
        strbase = strtab["off"]
        n = sec["size"] // sec["entsize"]
        for i in range(n):
            off = sec["off"] + i*sec["entsize"]
            if is64:
                nm, info, other, shndx, value, size = struct.unpack_from(e+"IBBHQQ", d, off)
            else:
                nm, value, size, info, other, shndx = struct.unpack_from(e+"IIIBBH", d, off)
            end = d.index(b"\x00", strbase+nm)
            name = d[strbase+nm:end].decode("latin1")
            if name == want:
                return dict(section=sec["sname"], value=value, size=size, shndx=shndx)
    return None

def addr_to_off(secs, addr):
    for s in secs:
        if s["type"] != 8 and s["addr"] and s["addr"] <= addr < s["addr"]+s["size"]:
            return s["off"] + (addr - s["addr"]), s["sname"]
    return None, None

for so_name in ("lib/armeabi-v7a/libminecraftpe.so", "lib/arm64-v8a/libminecraftpe.so"):
    try:
        d = read_so(so_name)
    except KeyError:
        print(f"[{so_name}] 不存在，跳过")
        continue
    print("="*70)
    print(so_name, len(d), "B")
    secs, is64, e = elf_sections(d)
    names = [s["sname"] for s in secs]
    print("  ELF", "64-bit" if is64 else "32-bit", " 段数:", len(secs))
    print("  有 .symtab:", ".symtab" in names, "  有 .dynsym:", ".dynsym" in names)
    for want in ("_ZN15SharedConstants21CurrentStorageVersionE",
                 "_ZN15SharedConstants19CurrentNetworkVersionE",
                 "_ZN11GameVersion7currentEv"):
        r = find_sym(d, secs, is64, e, want)
        if not r:
            print(f"  {want}: 符号表里没有")
            continue
        print(f"  {want}: {r}")
        off, sn = addr_to_off(secs, r["value"])
        if off is None:
            print("      地址无法映射到文件偏移")
            continue
        raw = d[off:off+16]
        print(f"      地址 0x{r['value']:x} → 段 {sn} @0x{off:x}  前16字节 {raw.hex()}")
        if r["size"] and r["size"] <= 8:
            val = int.from_bytes(raw[:r["size"]], "little")
            print(f"      ★ 值（小端 {r['size']} 字节）= {val}")
