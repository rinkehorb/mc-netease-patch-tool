import zipfile
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
base = z.read('assets/resource_packs/skins/skinpacks/Base/base.json').decode('utf-8')
# 找 customSlim 部分
idx = base.find('customSlim')
print('customSlim 在位置:', idx)
print(base[idx-100:idx+800])
