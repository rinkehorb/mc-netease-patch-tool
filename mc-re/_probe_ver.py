import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,60}', so))

# MCPE 版本号常见格式
print('=== 版本号候选 ===')
for s in sorted(strs):
    sl = s.lower()
    # 1.x.x 格式
    if re.match(r'^1\.\d+\.\d+(\.\d+)?$', s):
        print('  ', s)
    # version 相关
    if 'version' in sl and len(s) < 40 and not s.startswith('_Z'):
        print('  [ver]', s)
    # 1\.2 相关
    if re.search(r'1\.2\.\d+', s) and len(s) < 50:
        print('  [1.2]', s)
