import re, os
# 1) mcWebViewDialog 里 onWebappCallback / calljs / sendMessage 的实现
p = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v3\com\mojang\minecraftpe\mcWebViewDialog.smali'
src = open(p, encoding='utf-8').read()

def extract_method(src, name):
    # 找 .method ... name(...) 到 .end method
    m = re.search(r'\.method[^\n]*\s' + re.escape(name) + r'\(.*?\.end method', src, re.S)
    return m.group(0) if m else None

for m in ['onWebappCallback', 'calljs', 'sendMessage', 'openInvestigate']:
    body = extract_method(src, m)
    if body:
        print('='*20, m, '='*20)
        print(body[:1200])
        print()
