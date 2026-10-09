import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# sendMessage( 的上下文
print('=== sendMessage( 调用上下文 ===')
for m in re.finditer(r'.{60}sendMessage\s*\(.{60}', app):
    print('  ...', m.group(0), '...')
    print()

print('=== postMessage( 调用上下文 ===')
for m in re.finditer(r'.{60}postMessage\s*\(.{60}', app):
    print('  ...', m.group(0), '...')
    print()
