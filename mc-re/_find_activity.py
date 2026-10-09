import os

DECODE_DIR = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\manifest_decoded3'
manifest_path = os.path.join(DECODE_DIR, 'AndroidManifest.xml')

with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找 application 标签
app_start = content.find('<application')
app_end = content.find('>', app_start) + 1
print('=== <application ...> 标签 ===')
print(content[app_start:app_end])
print()

# 找 MainActivity 的 activity 标签
# MainActivity 是 .mojang.minecraftpe.MainActivity
import re
# 找所有 activity 标签
for m in re.finditer(r'<activity[^>]*android:name="([^"]*)"[^>]*>', content):
    name = m.group(1)
    if 'MainActivity' in name or 'mojang' in name:
        print(f'=== activity: {name} ===')
        print(m.group(0))
        print()
