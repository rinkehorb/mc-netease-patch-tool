import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,50}', so))

# 找 UI 导航/命令类字符串（可能是 nativeJsCall 的 cmd）
print('=== UI/screen/navigation 命令候选 ===')
cmds = set()
for s in strs:
    sl = s.lower()
    # 驼峰或下划线，跟 screen/page/view/show/open/goto/navigate/dialog/picker 相关
    if re.match(r'^[a-z][a-zA-Z]{3,30}$', s) and any(k in sl for k in
        ['screen','page','view','show','open','goto','navigate','dialog','picker','popup','window','panel','menu']):
        if not s.startswith('_Z') and '::' not in s and 'ScreenController' not in s:
            cmds.add(s)
for c in sorted(cmds): print('  ', c)

# 也找 json method 风格的
print()
print('=== json method 风格（驼峰，跟 skin/profile/player 相关）===')
for s in sorted(strs):
    sl = s.lower()
    if re.match(r'^[a-z][a-zA-Z]{4,30}$', s) and ('skin' in sl or 'profile' in sl or 'player' in sl) \
       and not s.startswith('_Z') and '::' not in s and 'ScreenController' not in s \
       and 'SkinPicker' not in s and 'SkinPack' not in s and 'SkinInfo' not in s \
       and not s.startswith('get_') and not s.startswith('set_') and not s.startswith('is_') \
       and not s.startswith('delete_') and not s.startswith('on') and not s.startswith('can') \
       and 'MinecraftScreenModel' not in s and 'Social' not in s:
        print('  ', s)
