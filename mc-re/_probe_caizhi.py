import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 找"材质光影"相关文案
print('=== 材质光影相关文案 ===')
for m in set(re.findall(r'["\']([^"\']*材质[^"\']*)["\']', app)):
    if len(m) < 40:
        print('  ', m)

print()
print('=== 光影相关文案 ===')
for m in set(re.findall(r'["\']([^"\']*光影[^"\']*)["\']', app)):
    if len(m) < 40:
        print('  ', m)

print()
print('=== 资源包/材质包相关文案 ===')
for m in set(re.findall(r'["\']([^"\']*(?:资源包|材质包|纹理包)[^"\']*)["\']', app)):
    if len(m) < 40:
        print('  ', m)
