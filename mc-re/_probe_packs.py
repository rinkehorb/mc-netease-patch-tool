import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,80}', so))

# 1) 资源包/行为包路径
print('=== 资源包/行为包路径相关 ===')
for s in sorted(strs):
    sl = s.lower()
    if ('resource_pack' in sl or 'behavior_pack' in sl or 'texture_pack' in sl or 'resourcepack' in sl) and ('/' in s or 'path' in sl or 'dir' in sl):
        print('  ', s)

# 2) games/ 外部目录
print()
print('=== games/ 外部存储目录 ===')
for s in sorted(strs):
    if 'games/' in s or '/games' in s or 'minecraftWorlds' in s:
        print('  ', s)

# 3) sdcard / external storage
print()
print('=== sdcard / 外部存储 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'sdcard' in sl or 'external' in sl or 'getexternal' in sl or 'getfilesdir' in sl:
        print('  ', s)

# 4) resource_packs / behavior_packs 目录名
print()
print('=== resource_packs / behavior_packs 目录名 ===')
for s in sorted(strs):
    if s in ('resource_packs','behavior_packs','texture_packs','minecraftWorlds','games','com.netease.mc.qihoo'):
        print('  ', s)
