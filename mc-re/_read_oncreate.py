import os

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
smali_path = os.path.join(MC_RE, 'smali_v3', 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')

with open(smali_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找 onCreate 方法完整内容
start = content.find('.method public onCreate(Landroid/os/Bundle;)V')
# 找方法结束（.end method）
end = content.find('.end method', start)
method = content[start:end+len('.end method')]

lines = method.splitlines()
for i, line in enumerate(lines):
    print(f'{i:3d}: {line}')
