"""
修复 v17 闪退：把 onCreate 的 .registers 7 改成 .registers 9
这样 v5、v6 就变成了局部寄存器，不会覆盖参数寄存器
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

# 从 smali_v17 继续改
main_activity = os.path.join(MC_RE, 'smali_v17', 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')

with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 把 onCreate 方法里的 .registers 7 改成 .registers 9
# 只改 onCreate 方法里的那一行
old = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 7'
new = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 9'

assert old in content, '找不到 onCreate 的 .registers 7！'
content = content.replace(old, new, 1)

with open(main_activity, 'w', encoding='utf-8') as f:
    f.write(content)

print('已修复：.registers 7 -> .registers 9')
print('v5、v6 现在是局部寄存器，不会覆盖 p0(this) 和 p1(savedInstanceState)')

# 重编译 dex
out_dex = os.path.join(MC_RE, 'patched_v17', 'classes.dex')
# 先删旧 dex
if os.path.exists(out_dex):
    os.remove(out_dex)

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', 
       os.path.join(MC_RE, 'smali_v17'), '-o', out_dex]
print('重编译 dex...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('stdout:', r.stdout[-500:])
print('stderr:', r.stderr[-500:])
print('返回码:', r.returncode)

if r.returncode == 0:
    print('dex 大小:', os.path.getsize(out_dex))
