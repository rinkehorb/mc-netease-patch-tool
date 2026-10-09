import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 1) 找 g( 函数的定义（桥函数）
print('=== 桥函数 g(t) 定义上下文 ===')
# function g(t){...}
for m in re.finditer(r'function\s+g\s*\(\s*t\s*\)\s*\{[^}]{0,500}', app):
    print(m.group(0)[:500])
    print()

# 2) 找所有 g( 调用，看传什么参数
print('=== g( 调用上下文 ===')
for m in re.finditer(r'.{80}g\s*\(\s*[^)]{0,100}\).{20}', app):
    ctx = m.group(0)
    # 过滤掉太常见的
    if 'sendMessage' in ctx or 'postMessage' in ctx or 'json:' in ctx or 'python' in ctx.lower() or 'skin' in ctx.lower():
        print('  ...', ctx, '...')
        print()

# 3) 找 json: 开头的字符串
print('=== json: 开头的消息字符串 ===')
for m in set(re.findall(r'["\']json:([^"\']{0,150})["\']', app)):
    print('  json:%s' % m[:150])
