import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 1) .so 里跟 skin/换肤/js消息 相关的短字符串（可能作为消息名）
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,40}', so))
print('=== .so 里 skin 相关短字符串（可能是消息名）===')
for s in sorted(strs):
    sl = s.lower()
    if 'skin' in sl and not s.startswith('_Z') and not s.startswith('skin_') and 'Skin' not in s:
        # 过滤掉长类名
        if '::' not in s and len(s) < 30:
            print('  ', repr(s))

# 2) H5 app.js 里 sendMessage( / mc. 的调用
print()
print('=== H5 app.js 里 sendMessage 调用参数 ===')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')
for m in re.finditer(r'sendMessage\s*\(\s*["\']([^"\']+)["\']', app):
    print('  sendMessage("%s")' % m.group(1))
for m in re.finditer(r'calljs\s*\(\s*["\']([^"\']+)["\']', app):
    print('  calljs("%s")' % m.group(1))
# mc.xxx 调用
print()
print('=== H5 里 mc. 开头的调用 ===')
for m in set(re.findall(r'mc\.(\w+)\s*\(', app)):
    print('  mc.%s()' % m)
