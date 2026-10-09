import zipfile, re
netease_apk = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk'
native_apk = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft PEB 1.2.0.7 v7a.apk'

zn = zipfile.ZipFile(netease_apk)
zo = zipfile.ZipFile(native_apk)

so_n = zn.read('lib/armeabi-v7a/libminecraftpe.so')
so_o = zo.read('lib/armeabi-v7a/libminecraftpe.so')

strs_n = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,80}', so_n))
strs_o = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,80}', so_o))

print('=== 网易版 .so 里 MainMenu 相关 ===')
for s in sorted(strs_n):
    if 'MainMenu' in s or 'main_menu' in s:
        print('  ', s)

print()
print('=== 网易版 .so 里 SceneFactory / createScreen 相关 ===')
for s in sorted(strs_n):
    if 'SceneFactory' in s or 'createSkinPicker' in s or 'createProfile' in s:
        print('  ', s)

print()
print('=== 原生有但网易版没有的关键符号 ===')
key_syms = ['MainMenuScreen', 'SceneFactory', 'createSkinPickerScreen', 'createProfileScreen',
            'ProfileScreen', 'ProfileTab', 'navigateToProfile', 'pushProfileScreen']
for sym in key_syms:
    in_n = [s for s in strs_n if sym in s]
    in_o = [s for s in strs_o if sym in s]
    print(f'  {sym}: 网易={len(in_n)} 原生={len(in_o)}')
    if in_o and not in_n:
        print('    -> 网易删了!')
