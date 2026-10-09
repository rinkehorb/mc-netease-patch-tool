import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')
for kw in ['skin','Skin','skinpack','profile','/user','setting']:
    hits = set(re.findall(r'["\']([^"\']{0,50}' + kw + r'[^"\']{0,50})["\']', app))
    if hits:
        print('===', kw, '===')
        for h in sorted(hits)[:12]: print('  ', h)
