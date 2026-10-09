import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,80}', so))

# 1) FilePathManager 相关
print('=== FilePathManager 方法 ===')
for s in sorted(strs):
    if 'FilePathManager' in s:
        print('  ', s)

# 2) rootPath / setRootPath / getRootPath
print()
print('=== rootPath 相关 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'rootpath' in sl or 'root_path' in sl or 'setroot' in sl or 'getroot' in sl:
        print('  ', s)

# 3) filesDir / getFilesDir / files/
print()
print('=== filesDir / files/ 路径 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'filesdir' in sl or 'getfilesdir' in sl or s.endswith('/files') or '/files/' in s:
        print('  ', s)

# 4) 找 .minecraft 或 minecraftpe 目录
print()
print('=== minecraftpe / .minecraft 目录 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'minecraftpe' in sl or '.minecraft' in sl:
        print('  ', s)
