import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 1) Vue 路由定义（path: '/xxx'）
print('=== Vue 路由 path ===')
for m in sorted(set(re.findall(r'path\s*:\s*["\']([^"\']+)["\']', app))):
    print('  ', m)

# 2) 找 skin 相关的路由/页面
print()
print('=== skin 相关路由/组件名 ===')
for m in sorted(set(re.findall(r'["\']([^"\']*skin[^"\']*)["\']', app))):
    if len(m) < 60 and not m.startswith('http') and ' ' not in m:
        print('  ', m)

# 3) 找 router.push / this.$router 调用
print()
print('=== router.push 调用 ===')
for m in set(re.findall(r'router\.push\s*\(\s*["\']([^"\']+)["\']', app)):
    print('  push(%s)' % m)
for m in set(re.findall(r'\$router\.push\s*\(\s*["\']([^"\']+)["\']', app)):
    print('  $router.push(%s)' % m)
