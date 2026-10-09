import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

print('=== H5 里 sendMessage(...) 调用参数 ===')
for m in sorted(set(re.findall(r'sendMessage\s*\(\s*["\']([^"\']+)["\']', app))):
    print('  sendMessage("%s")' % m)

print()
print('=== H5 里 calljs(...) 调用参数 ===')
for m in sorted(set(re.findall(r'calljs\s*\(\s*["\']([^"\']+)["\']', app))):
    print('  calljs("%s")' % m)

print()
print('=== H5 里 mc.xxx() 调用 ===')
for m in sorted(set(re.findall(r'mc\.(\w+)\s*\(', app))):
    print('  mc.%s()' % m)

# 也看其他 js chunk 里的
print()
print('=== 其他 js chunk 里的 mc./sendMessage ===')
for jf in [n for n in z.namelist() if n.startswith('assets/web/static/js/') and n.endswith('.js')]:
    t = z.read(jf).decode('utf-8','ignore')
    ms = set(re.findall(r'mc\.(\w+)\s*\(', t))
    sm = set(re.findall(r'sendMessage\s*\(\s*["\']([^"\']+)["\']', t))
    if ms or sm:
        print(' ', jf.split('/')[-1])
        for x in sorted(ms): print('    mc.%s()' % x)
        for x in sorted(sm): print('    sendMessage("%s")' % x)
