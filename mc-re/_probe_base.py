import zipfile
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
base = z.read('assets/resource_packs/skins/skinpacks/Base/base.json').decode('utf-8')
print(base[:2000])
