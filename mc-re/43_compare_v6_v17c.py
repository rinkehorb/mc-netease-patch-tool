"""
对比 v6 和 v17c 的 MainActivity.smali
1. 从两个 APK 提取 classes.dex
2. 用 baksmali 反编译
3. 对比 onCreate 方法
"""
import os, zipfile, subprocess, shutil

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
BAKSMALI = os.path.join(MC_RE, 'tools', 'baksmali.jar')

V6_APK = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft-0.2.0.25445-offline-v6.apk'
V17C_APK = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Minecraft-0.2.0.25445-offline-v17c.apk'

WORK = os.path.join(MC_RE, 'compare_v6_v17c')
if os.path.exists(WORK):
    shutil.rmtree(WORK)
os.makedirs(WORK)

# 提取两个 APK 的 classes.dex
def extract_dex(apk_path, out_path):
    z = zipfile.ZipFile(apk_path, 'r')
    with open(out_path, 'wb') as f:
        f.write(z.read('classes.dex'))
    z.close()
    print(f'提取 {os.path.basename(apk_path)} classes.dex: {os.path.getsize(out_path)} bytes')

extract_dex(V6_APK, os.path.join(WORK, 'v6.dex'))
extract_dex(V17C_APK, os.path.join(WORK, 'v17c.dex'))

# baksmali 反编译
for tag in ['v6', 'v17c']:
    smali_dir = os.path.join(WORK, f'smali_{tag}')
    cmd = [JAVA, '-Xmx4g', '-jar', BAKSMALI, 'disassemble', 
           os.path.join(WORK, f'{tag}.dex'), '-o', smali_dir]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(f'baksmali {tag}: 返回码 {r.returncode}')
    if r.returncode != 0:
        print('  stderr:', r.stderr[-500:])

# 对比 MainActivity.smali
def get_oncreate(smali_dir):
    path = os.path.join(smali_dir, 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # 提取 onCreate 方法
    result = []
    in_method = False
    for line in lines:
        if '.method public onCreate(Landroid/os/Bundle;)V' in line:
            in_method = True
        if in_method:
            result.append(line)
        if in_method and line.strip() == '.end method':
            break
    return result

v6_oncreate = get_oncreate(os.path.join(WORK, 'smali_v6'))
v17c_oncreate = get_oncreate(os.path.join(WORK, 'smali_v17c'))

print()
print('=== v6 onCreate 行数:', len(v6_oncreate))
print('=== v17c onCreate 行数:', len(v17c_oncreate))

# 逐行对比
print()
print('=== 差异行 ===')
max_lines = max(len(v6_oncreate), len(v17c_oncreate))
for i in range(max_lines):
    l6 = v6_oncreate[i].rstrip() if i < len(v6_oncreate) else '(无)'
    l17 = v17c_oncreate[i].rstrip() if i < len(v17c_oncreate) else '(无)'
    if l6 != l17:
        print(f'行 {i+1}:')
        print(f'  v6:   {l6}')
        print(f'  v17c: {l17}')
