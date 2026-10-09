"""检查 JDK 里的工具"""
import os

jdk_dir = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\tools\jdk'
print('JDK 目录:', jdk_dir)

# 找 javac
for root, dirs, files in os.walk(jdk_dir):
    for f in files:
        if 'javac' in f.lower() or 'd8' in f.lower() or 'dx' in f.lower():
            print('  找到:', os.path.join(root, f))

# 列出 bin 目录
bin_dir = os.path.join(jdk_dir, 'bin')
if os.path.exists(bin_dir):
    print()
    print('bin 目录内容:')
    for f in sorted(os.listdir(bin_dir)):
        if f.endswith('.exe') or f.endswith('.bat'):
            print(f'  {f}')
