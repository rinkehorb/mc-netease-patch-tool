import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
dex = z.read('classes.dex')

# 在 dex 里找字符串
strs = set(s.decode('utf-8','ignore') for s in re.findall(rb'[\x20-\x7e]{5,100}', dex))

# 1) games/ 相关路径
print('=== dex 里 games/ 路径 ===')
for s in sorted(strs):
    if 'games/' in s or '/games' in s:
        print('  ', repr(s))

# 2) sdcard / external storage
print()
print('=== dex 里 sdcard / external ===')
for s in sorted(strs):
    sl = s.lower()
    if 'sdcard' in sl or 'external' in sl or 'getexternalstorage' in sl:
        print('  ', repr(s))

# 3) com.netease.mc.qihoo 路径
print()
print('=== dex 里 com.netease.mc.qihoo 路径 ===')
for s in sorted(strs):
    if 'com.netease.mc.qihoo' in s and len(s) < 120:
        print('  ', repr(s))

# 4) resource_packs / behavior_packs
print()
print('=== dex 里 resource_packs / behavior_packs ===')
for s in sorted(strs):
    if 'resource_pack' in s.lower() or 'behavior_pack' in s.lower():
        if len(s) < 100:
            print('  ', repr(s))
