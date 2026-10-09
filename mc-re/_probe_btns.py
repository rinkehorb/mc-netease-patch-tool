import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 找材质/光影/玩法/资源相关的中文文案
print('=== 材质/光影/玩法/资源相关文案 ===')
keywords = ['材质', '光影', '玩法', '资源', '纹理', '插件', '模组', 'mod', 'texture', 'resource', 'skin']
for kw in keywords:
    # 找包含关键词的字符串
    for m in set(re.findall(r'["\']([^"\']*' + kw + r'[^"\']*)["\']', app, re.IGNORECASE)):
        if len(m) < 40 and not m.startswith('http') and ' ' not in m[:5]:
            print(f'  [{kw}] {m}')

# 找世界设置页面相关的路由/组件名
print()
print('=== worldSetting / 世界设置 相关 ===')
for m in set(re.findall(r'["\']([^"\']*worldSetting[^"\']*)["\']', app)):
    print('  ', m)
for m in set(re.findall(r'["\']([^"\']*setting[^"\']*)["\']', app)):
    if len(m) < 40:
        print('  ', m)
