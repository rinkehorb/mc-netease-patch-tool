import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 1) H5 index.html 结构
html = z.read('assets/web/index.html').decode('utf-8')
print('=== index.html 前 2000 字符 ===')
print(html[:2000])
print()

# 2) H5 里桥对象怎么调（python/native/nativeCall 等）
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')
print('=== 桥对象调用模式 ===')
# 找 python.xxx / native.xxx / mc.xxx
for m in set(re.findall(r'(window\.)?(python|native|nativeCall|jsBridge|gameBridge)\.(\w+)\s*\(', app)):
    print('  %s.%s()' % (m[1], m[2]))

# 3) sendMessage 的参数格式（找 json: 开头的）
print()
print('=== sendMessage / postMessage 传的字符串格式 ===')
for m in set(re.findall(r'sendMessage\s*\(\s*["\']([^"\']{0,80})["\']', app)):
    print('  sendMessage("%s")' % m[:80])
for m in set(re.findall(r'postMessage\s*\(\s*["\']([^"\']{0,80})["\']', app)):
    print('  postMessage("%s")' % m[:80])
