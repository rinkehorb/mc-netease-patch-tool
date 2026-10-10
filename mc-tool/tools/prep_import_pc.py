"""在 PC 上复刻 WorldImportPrep 的行为，做出 3a 需要的几个包，推到手机 Download。

用途：验证「游戏侧注入的导入界面」端到端是否可用（不依赖工具 App 的 UI）。
逻辑与 Java 版 WorldImportPrep 逐条对应：
  * 找最浅的 level.dat 当世界根，剥掉外壳前缀
  * 按【顶层目录】分组：root / db / players / …（因为 decompress_map 会压平目录，
    所以每组的解压目标目录会指向对应的子目录）
  * 版本降级：lastOpenedWithVersion / StorageVersion / NetworkVersion 原地改字节
  * 记录 zip：里面就一个 <slotId>.json，字段与客户端自己写的一致（不写 game_type）
"""
import zipfile, struct, os, sys, io, json

SRC = r"C:\Users\Administrator\DoubaoWork\chats\LogicGates.zip"
OUT = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\import_out"
# 槽位号：命令行第一个参数，默认 1。包名用数字（mcweb_3_*.zip），
# 世界目录名与记录里的 level_id 用 "mcw<槽位>" —— 必须和 mc-import.js 的约定一致。
SLOT_NO = sys.argv[1] if len(sys.argv) > 1 else "1"
SLOT = "mcw" + SLOT_NO
if len(sys.argv) > 2:
    SRC = sys.argv[2]
TARGET_VER = [1, 1, 3, 50]
TARGET_STORAGE = 5
TARGET_NETWORK = 113


def norm(n):
    return n.replace("\\", "/")


def read_nbt_versions(nbt):
    """只走到顶层，找三个字段的偏移。"""
    p = [0]

    def u1():
        v = nbt[p[0]]; p[0] += 1; return v

    def u2():
        v = nbt[p[0]] | (nbt[p[0] + 1] << 8); p[0] += 2; return v

    def i4():
        v = struct.unpack_from("<i", nbt, p[0])[0]; p[0] += 4; return v

    def s():
        n = u2(); v = nbt[p[0]:p[0] + n].decode("utf-8", "replace"); p[0] += n; return v

    def skip(t):
        if t == 1: p[0] += 1
        elif t == 2: p[0] += 2
        elif t == 3: p[0] += 4
        elif t == 4: p[0] += 8
        elif t == 5: p[0] += 4
        elif t == 6: p[0] += 8
        elif t == 7: p[0] += 4 + i4()
        elif t == 8: s()
        elif t == 9:
            et = u1(); n = i4()
            for _ in range(n): skip(et)
        elif t == 10:
            while True:
                tt = u1()
                if tt == 0: break
                s(); skip(tt)
        elif t == 11: p[0] += 4 * i4()
        else: raise ValueError("tag %d" % t)

    assert u1() == 10
    s()
    found = {}
    while True:
        t = u1()
        if t == 0: break
        name = s()
        mark = p[0]
        skip(t)
        if name in ("lastOpenedWithVersion", "StorageVersion", "NetworkVersion", "LevelName"):
            found[name] = (t, mark)
    return found


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(SRC)

    # 1) 世界根 = 最浅的 level.dat 所在目录
    prefix = None
    for n in z.namelist():
        nn = norm(n)
        if nn.lower().endswith("level.dat"):
            d = nn.rsplit("/", 1)[0] + "/" if "/" in nn else ""
            if prefix is None or len(d) < len(prefix): prefix = d
    print("世界根前缀:", repr(prefix))

    # 2) 读 level.dat 并降级
    raw = z.read(prefix + "level.dat")
    header, nbt = raw[:8], bytearray(raw[8:])
    f = read_nbt_versions(nbt)
    # 注意：列表的 mark 指向【元素类型】那一个字节，元素实际从 mark+5 开始
    #（1 字节元素类型 + 4 字节元素个数）。Java 版 LevelDat 用的是读完之后的位置，
    # 所以没这个坑 —— 这里是 PC 测试脚本，别把参考实现抄错。
    voff = f["lastOpenedWithVersion"][1] + 5
    old_ver = [struct.unpack_from("<i", nbt, voff + 4 * i)[0] for i in range(4)]
    old_storage = struct.unpack_from("<i", nbt, f["StorageVersion"][1])[0]
    old_net = struct.unpack_from("<i", nbt, f["NetworkVersion"][1])[0]
    print("降级前: version=%s storage=%d net=%d" % (old_ver, old_storage, old_net))

    for i, v in enumerate(TARGET_VER):
        struct.pack_into("<i", nbt, voff + 4 * i, v)
    struct.pack_into("<i", nbt, f["StorageVersion"][1], TARGET_STORAGE)
    struct.pack_into("<i", nbt, f["NetworkVersion"][1], TARGET_NETWORK)
    new_level_dat = header + bytes(nbt)

    after = read_nbt_versions(bytearray(new_level_dat[8:]))
    avoff = after["lastOpenedWithVersion"][1] + 5
    new_ver = [struct.unpack_from("<i", new_level_dat, 8 + avoff + 4 * i)[0] for i in range(4)]
    print("降级后: version=%s storage=%d net=%d"
          % (new_ver,
             struct.unpack_from("<i", new_level_dat, 8 + after["StorageVersion"][1])[0],
             struct.unpack_from("<i", new_level_dat, 8 + after["NetworkVersion"][1])[0]))
    diff = sum(1 for a, b in zip(raw, new_level_dat) if a != b)
    print("差异字节数:", diff)

    # 3) 按顶层目录分组
    groups = {"root": {}}
    for n in z.namelist():
        nn = norm(n)
        if nn.endswith("/"): continue
        if not nn.startswith(prefix): continue
        rel = nn[len(prefix):]
        if not rel: continue
        data = z.read(n)
        if rel in ("level.dat", "level.dat_old"):
            data = new_level_dat
        if "/" in rel:
            top, inner = rel.split("/", 1)
            if not inner: continue
            groups.setdefault(top, {})[inner] = data
        else:
            groups["root"][rel] = data

    order = ["root"] + [k for k in groups if k != "root"]
    total_files = 0
    for top in order:
        g = groups.get(top) or {}
        if not g: continue
        path = os.path.join(OUT, "mcweb_%s_%s.zip" % (SLOT_NO, top))
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zo:
            for name, data in g.items():
                zo.writestr(name, data)
        total_files += len(g)
        print("  %-28s %d 个文件  %d 字节" % (os.path.basename(path), len(g), os.path.getsize(path)))

    # 4) 世界记录
    rec = {"second_type": -1, "is_local": True, "is_copy": False,
           "name": "A/B测试(槽位%s)" % SLOT_NO, "level_id": SLOT, "resource_packs": {},
           "user_ids": {"": 1791539226}, "version": 0, "item_id": "-100",
           "path": SLOT, "addons": {}, "icon": ""}
    s = json.dumps(rec, ensure_ascii=True)
    recpath = os.path.join(OUT, "mcweb_%s_record.zip" % SLOT_NO)
    with zipfile.ZipFile(recpath, "w", zipfile.ZIP_DEFLATED) as zo:
        zo.writestr(SLOT + ".json", s)
    print("  记录: %s   内容: %s" % (os.path.basename(recpath), s))
    print("合计世界文件:", total_files)


if __name__ == "__main__":
    main()
