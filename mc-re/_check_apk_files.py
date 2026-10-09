import zipfile

BASE_APK = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\patched_v16\Minecraft-unsigned.apk'
z = zipfile.ZipFile(BASE_APK, 'r')

print('=== APK 里的文件（前 30 个）===')
for i, n in enumerate(z.namelist()[:30]):
    print(f'  {i}: {n}')

print()
print('=== 找 classes.dex ===')
for n in z.namelist():
    if 'classes.dex' in n:
        print('  ', n, z.getinfo(n).file_size)

print()
print('=== 找 alex.png ===')
for n in z.namelist():
    if 'alex.png' in n:
        print('  ', n, z.getinfo(n).file_size)

print()
print('=== 找 zh_CN.lang ===')
for n in z.namelist():
    if 'zh_CN.lang' in n:
        print('  ', n, z.getinfo(n).file_size)
