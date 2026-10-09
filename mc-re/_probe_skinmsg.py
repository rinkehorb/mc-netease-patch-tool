import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')

# 所有 js chunk 里搜 skin/skinPicker/showSkin/openSkin 相关字符串
for jf in [n for n in z.namelist() if n.startswith('assets/web/') and n.endswith('.js')]:
    t = z.read(jf).decode('utf-8','ignore')
    # 找 skin 相关的字符串字面量
    hits = set()
    for m in re.finditer(r'["\']([^"\']{0,60})["\']', t):
        s = m.group(1)
        sl = s.lower()
        if ('skin' in sl and ('open' in sl or 'show' in sl or 'picker' in sl or 'choose' in sl or 'select' in sl or 'goto' in sl or 'navigate' in sl or 'screen' in sl or 'page' in sl or 'view' in sl)):
            hits.add(s)
        if re.match(r'^(open|show|goto|navigate|enter|push)_[a-z_]*skin', sl):
            hits.add(s)
    if hits:
        print('===', jf.split('/')[-1], '===')
        for h in sorted(hits): print('  ', h)

# 也搜 method/action/type 字段值（json RPC 格式）
print()
print('=== method/action 字段值候选 ===')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')
for m in set(re.findall(r'(?:method|action|type|cmd|command)\s*:\s*["\']([^"\']+)["\']', app)):
    if 'skin' in m.lower() or 'profile' in m.lower():
        print('  ', m)
