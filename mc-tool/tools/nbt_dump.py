import zipfile, zlib, gzip, struct, os, io, sys

TAG = {0:"End",1:"Byte",2:"Short",3:"Int",4:"Long",5:"Float",6:"Double",
       7:"ByteArray",8:"String",9:"List",10:"Compound",11:"IntArray"}

class R:
    def __init__(self, d): self.d=d; self.p=0
    def u1(self):
        v=self.d[self.p]; self.p+=1; return v
    def i1(self):
        v=struct.unpack_from("<b", self.d, self.p)[0]; self.p+=1; return v
    def i2(self):
        v=struct.unpack_from("<h", self.d, self.p)[0]; self.p+=2; return v
    def u2(self):
        v=struct.unpack_from("<H", self.d, self.p)[0]; self.p+=2; return v
    def i4(self):
        v=struct.unpack_from("<i", self.d, self.p)[0]; self.p+=4; return v
    def i8(self):
        v=struct.unpack_from("<q", self.d, self.p)[0]; self.p+=8; return v
    def f4(self):
        v=struct.unpack_from("<f", self.d, self.p)[0]; self.p+=4; return v
    def f8(self):
        v=struct.unpack_from("<d", self.d, self.p)[0]; self.p+=8; return v
    def s(self):
        n=self.u2(); v=self.d[self.p:self.p+n].decode("utf-8","replace"); self.p+=n; return v

def payload(r, t):
    if t==1: return r.i1()
    if t==2: return r.i2()
    if t==3: return r.i4()
    if t==4: return r.i8()
    if t==5: return round(r.f4(),6)
    if t==6: return round(r.f8(),6)
    if t==7:
        n=r.i4(); v=list(r.d[r.p:r.p+n]); r.p+=n; return f"<{n} bytes>"
    if t==8: return r.s()
    if t==9:
        et=r.u1(); n=r.i4()
        if et==0: return []
        # 对纯数值列表直接展开，避免刷屏
        if et in (1,2,3,4,5,6):
            return [payload(r,et) for _ in range(n)]
        return [payload(r,et) for _ in range(n)]
    if t==10:
        out={}
        while True:
            tt=r.u1()
            if tt==0: break
            nm=r.s(); out[nm]=payload(r,tt)
        return out
    if t==11:
        n=r.i4(); return [r.i4() for _ in range(n)]
    raise ValueError("unknown tag %d at %d" % (t, r.p))

def parse(data):
    r=R(data)
    t=r.u1()
    if t!=10: raise ValueError("root not compound: %d"%t)
    name=r.s()
    return name, payload(r,10)

def load_nbt(raw):
    fmt="raw(8字节头)"
    data=raw
    if raw[:2]==b"\x1f\x8b":
        fmt="gzip"; data=gzip.decompress(raw)
    elif raw[:1]==b"\x78":
        try:
            fmt="zlib"; data=zlib.decompress(raw)
        except Exception:
            fmt="zlib?"; data=raw
    if data and data[0] not in (0x0a,0x0b) and len(data)>8 and data[8] in (0x0a,0x0b):
        fmt="raw + 8字节头"; data=data[8:]
    return fmt, data

def find_level(z):
    best=None
    for n in z.namelist():
        nn=n.replace("\\","/")
        if nn.lower().endswith("level.dat"):
            d=nn.rsplit("/",1)[0]+"/" if "/" in nn else ""
            if best is None or len(d)<len(best[1]): best=(nn,d)
    return best

KEYS = ["StorageVersion","lastOpenedWithVersion","MinimumCompatibleClientVersion",
        "NetworkVersion","LevelName","GameType","Difficulty","Generator","InventoryVersion",
        "WorldVersion","Platform","IsEditorWorld","editorWorldType","NetEase","netease"]

def report(label, raw):
    fmt, data = load_nbt(raw)
    print(f"--- {label}")
    print(f"    编码: {fmt}   NBT 长度: {len(data)}")
    try:
        name, tree = parse(data)
        print(f"    根名: {name!r}   顶层键数: {len(tree)}")
        print("    === 全部键（按名） ===")
        for k in sorted(tree.keys()):
            v = tree[k]
            vs = str(v)
            if len(vs) > 90: vs = vs[:90]+"…"
            print(f"       {k:42s} = {vs}")
    except Exception as e:
        print("    解析失败:", e)

def handle(path):
    print("="*74)
    print(os.path.basename(path), os.path.getsize(path), "B")
    z=zipfile.ZipFile(path)
    names=z.namelist()
    lv=find_level(z)
    if lv is None:
        inner=[n for n in names if n.lower().endswith(".zip")]
        print("  外层没有 level.dat；内含 zip:", inner)
        for n in inner:
            data=z.read(n)
            iz=zipfile.ZipFile(io.BytesIO(data))
            print(f"  --- 内层 {n} 条目 {len(iz.namelist())} 个")
            for e in iz.namelist()[:20]: print("       ", e)
            ilv=find_level(iz)
            print("      内层最浅 level.dat:", ilv)
            if ilv: report(f"{os.path.basename(path)} → {n} → {ilv[0]}", iz.read(ilv[0]))
        return
    print("  最浅 level.dat:", lv[0])
    report(f"{os.path.basename(path)} → {lv[0]}", z.read(lv[0]))

for p in sys.argv[1:]:
    handle(p)
