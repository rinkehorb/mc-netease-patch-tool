import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 搜所有 chunk JS 里的"材质"、"光影"、"资源"
for i in range(9):
    fname = f'assets/web/static/js/{i}.'
    # 找完整文件名
    for n in z.namelist():
        if n.startswith(fname):
            data = z.read(n).decode('utf-8','ignore')
            # 找中文文案
            hits = set()
            for m in re.findall(r'["\']([^"\']{2,30})["\']', data):
                if any(k in m for k in ['材质','光影','资源','纹理','皮肤','玩法','插件','模组','世界','设置']):
                    hits.add(m)
            if hits:
                print(f'=== {n.split("/")[-1]} ===')
                for h in sorted(hits):
                    print('  ', h)
                print()
            break
