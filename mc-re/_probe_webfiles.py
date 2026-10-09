import zipfile
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
print('=== assets/web/ 下的文件 ===')
for n in sorted(z.namelist()):
    if n.startswith('assets/web/'):
        print('  ', n, z.getinfo(n).file_size)
