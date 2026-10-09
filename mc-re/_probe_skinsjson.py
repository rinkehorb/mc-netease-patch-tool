import zipfile, json
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 全局 skins.json
skins = json.loads(z.read('assets/resource_packs/skins/skinpacks/skins.json'))
print('=== skins.json keys ===')
for k in skins.keys():
    print(' ', k)

# 找 customSlim 的手臂
for name, geom in skins.items():
    if 'customSlim' in name:
        print(f'\n=== [{name}] ===')
        for bone in geom.get('bones', []):
            if 'arm' in bone.get('name','').lower():
                cubes = bone.get('cubes', [])
                for c in cubes:
                    print(f'  {bone["name"]}: size={c.get("size")}, origin={c.get("origin")}')
