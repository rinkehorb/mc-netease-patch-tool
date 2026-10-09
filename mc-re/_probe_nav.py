import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,50}', so))

# 找 onJsCallback 可能处理的命令名（短、驼峰、跟 UI/导航相关）
print('=== UI 导航命令候选（短驼峰字符串）===')
cmds = set()
for s in strs:
    # 驼峰命名，4-30 字符，不含下划线，不含 ::
    if re.match(r'^[a-z][a-zA-Z]{3,30}$', s) and '_' not in s and '::' not in s:
        sl = s.lower()
        # 跟 screen/page/view/open/show/goto/navigate/switch/push/jump/enter/close/back/home/main/menu/skin/profile 相关
        if any(k in sl for k in ['screen','page','view','open','show','goto','navigate','switch','push','jump','enter','close','back','home','main','menu','skin','profile','wardrobe','closet','hanger','avatar','character']):
            if not s.startswith('_Z') and not s.startswith('get') and not s.startswith('set') and not s.startswith('is') and not s.startswith('on'):
                cmds.add(s)

for c in sorted(cmds):
    print('  ', c)
