import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{5,}', so))

# 1. SettingsTabIndex / 设置标签页相关
print('=== SettingsTab / 设置标签 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'settingstab' in sl or 'setting_tab' in sl or 'tabindex' in sl:
        print('  ', s)

# 2. 设置里的选项分组标题（lang key 风格）
print()
print('=== options.* 设置项（原生设置屏内容）===')
opts = sorted(s for s in strs if s.startswith('options.') and len(s) < 60)
for o in opts: print('  ', o)

# 3. 皮肤/个人资料入口
print()
print('=== profile/skin 入口相关 ===')
for s in sorted(strs):
    sl = s.lower()
    if ('profile' in sl or 'skin' in sl) and ('screen' in sl or 'button' in sl or 'button' in sl or 'navigate' in sl or 'push' in sl or 'open' in sl or 'show' in sl or 'setting' in sl):
        print('  ', s)
