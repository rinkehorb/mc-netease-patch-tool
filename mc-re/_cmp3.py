import zipfile, re
native_apk = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft PEB 1.2.0.7 v7a.apk'
netease_apk = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk'

zo = zipfile.ZipFile(native_apk)
zn = zipfile.ZipFile(netease_apk)

# 对比 lang 文件里的设置标签
print('=== 原生 en_US.lang 里设置标签 ===')
lang_o = zo.read('assets/resource_packs/vanilla/texts/en_US.lang').decode('utf-8')
for line in lang_o.splitlines():
    if line.startswith('options.') and ('tab' in line.lower() or 'general' in line.lower() or 'profile' in line.lower()):
        print('  ', line)

print()
print('=== 网易 en_US.lang 里设置标签 ===')
lang_n = zn.read('assets/resource_packs/vanilla/texts/en_US.lang').decode('utf-8')
for line in lang_n.splitlines():
    if line.startswith('options.') and ('tab' in line.lower() or 'general' in line.lower() or 'profile' in line.lower()):
        print('  ', line)

# 原生 .so 里设置标签页相关
print()
print('=== 原生 .so 里 SettingsTab / 设置标签 ===')
so_o = zo.read('lib/armeabi-v7a/libminecraftpe.so')
strs_o = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,60}', so_o))
for s in sorted(strs_o):
    if 'SettingsTab' in s or 'settingstab' in s or 'tab_' in s.lower():
        print('  ', s)
