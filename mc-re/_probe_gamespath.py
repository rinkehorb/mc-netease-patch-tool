import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,100}', so))

# 1) games/ 完整路径
print('=== 含 games/ 的完整路径字符串 ===')
for s in sorted(strs):
    if 'games/' in s and len(s) < 100:
        print('  ', repr(s))

# 2) minecraftWorlds 路径
print()
print('=== minecraftWorlds 路径 ===')
for s in sorted(strs):
    if 'minecraftWorlds' in s:
        print('  ', repr(s))

# 3) com.netease 相关路径
print()
print('=== com.netease 相关路径 ===')
for s in sorted(strs):
    if 'com.netease' in s and len(s) < 100:
        print('  ', repr(s))

# 4) getExternalStorageDirectory / /sdcard
print()
print('=== sdcard / external storage ===')
for s in sorted(strs):
    sl = s.lower()
    if 'sdcard' in sl or 'external_storage' in sl or 'emulated/0' in sl:
        print('  ', repr(s))
