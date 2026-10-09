import os, re

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
smali_path = os.path.join(MC_RE, 'smali_v3', 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')

if os.path.exists(smali_path):
    with open(smali_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 找 onCreate 方法
    idx = content.find('.method public onCreate(Landroid/os/Bundle;)V')
    if idx >= 0:
        # 打印 onCreate 方法的前 80 行
        lines = content[idx:].splitlines()
        for i, line in enumerate(lines[:60]):
            print(f'{i:3d}: {line}')
    else:
        print('没找到 onCreate')
else:
    print('文件不存在:', smali_path)
    # 找找 smali 树在哪
    for d in os.listdir(MC_RE):
        if 'smali' in d.lower():
            print('  找到目录:', d)
