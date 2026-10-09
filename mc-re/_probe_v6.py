import zipfile, json
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 1) base.json - 看 customSlim 手臂定义
base = json.loads(z.read('assets/resource_packs/skins/skinpacks/Base/base.json'))
print('=== base.json geometry 骨架 ===')
for name, geom in base.get('geometry', {}).items():
    print(f'  [{name}]')
    bones = geom.get('bones', [])
    for b in bones:
        if 'arm' in b.get('name','').lower() or 'Arm' in b.get('name',''):
            print(f'    bone: {b.get("name")}, pivot={b.get("pivot")}, size={b.get("size")}')

# 2) lang 文件里 skin.name.alex
print()
print('=== zh_CN.lang 里 skin.name 相关 ===')
for line in z.read('assets/resource_packs/vanilla/texts/zh_CN.lang').decode('utf-8').splitlines():
    if 'skin.name' in line:
        print('  ', line)

print()
print('=== en_US.lang 里 skin.name 相关 ===')
for line in z.read('assets/resource_packs/vanilla/texts/en_US.lang').decode('utf-8').splitlines():
    if 'skin.name' in line:
        print('  ', line)

# 3) skindefs.json
print()
print('=== skindefs.json 前 500 字符 ===')
sd = z.read('assets/resource_packs/skins/skinpacks/Base/skindefs.json').decode('utf-8')
print(sd[:500])
