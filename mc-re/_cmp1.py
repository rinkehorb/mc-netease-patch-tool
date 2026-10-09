import zipfile, os
native_apk = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft PEB 1.2.0.7 v7a.apk'
netease_apk = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk'

print('=== 原生 1.2.0.7 基本信息 ===')
z = zipfile.ZipFile(native_apk)
print('大小:', os.path.getsize(native_apk))
print('条目数:', len(z.namelist()))
# lib
for n in z.namelist():
    if n.startswith('lib/') and n.endswith('.so'):
        print('  ', n, z.getinfo(n).file_size)
# dex
for n in z.namelist():
    if n.endswith('.dex'):
        print('  ', n, z.getinfo(n).file_size)

print()
print('=== 网易 0.2.0.25445 基本信息 ===')
z2 = zipfile.ZipFile(netease_apk)
print('大小:', os.path.getsize(netease_apk))
print('条目数:', len(z2.namelist()))
for n in z2.namelist():
    if n.startswith('lib/') and n.endswith('.so'):
        print('  ', n, z2.getinfo(n).file_size)

# 对比 strings 里的关键 UI 字符串
print()
print('=== 原生 .so 里换肤/档案相关字符串 ===')
so = z.read('lib/armeabi-v7a/libminecraftpe.so') if 'lib/armeabi-v7a/libminecraftpe.so' in z.namelist() else None
if so:
    import re
    strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,60}', so))
    for kw in ['SkinPicker','skin_picker','Profile','profile','wardrobe','hanger','closet','customSkin','skinCustomisation']:
        hits = sorted(s for s in strs if kw.lower() in s.lower())[:5]
        if hits:
            print(f'  [{kw}]')
            for h in hits: print('    ', h)
