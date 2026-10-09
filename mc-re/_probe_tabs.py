import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,60}', so))

# 找设置标签相关的字符串
print('=== 设置标签 / tab 相关字符串 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'tab' in sl and len(s) < 50:
        # 过滤掉明显无关的
        if not s.startswith('_Z') and not s.startswith('case') and 'label' not in sl:
            print('  ', s)

# 找 profile / archive / 档案 相关
print()
print('=== profile / 档案 / 用户 相关 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'profile' in sl and len(s) < 50 and not s.startswith('_Z'):
        print('  ', s)

# 找 options. 开头的 lang key
print()
print('=== options. 开头的 lang key（在 .so 里）===')
for s in sorted(strs):
    if s.startswith('options.') and len(s) < 50:
        print('  ', s)
