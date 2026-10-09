"""修复寄存器 - 重新跑，加调试"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

main_activity = os.path.join(MC_RE, 'smali_v17', 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')

with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 验证 .registers 已经改成 9 了
if '.registers 9' in content:
    print('OK: .registers 9 已存在')
else:
    print('修改 .registers 7 -> 9...')
    old = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 7'
    new = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 9'
    content = content.replace(old, new, 1)
    with open(main_activity, 'w', encoding='utf-8') as f:
        f.write(content)

# 重编译
out_dex = os.path.join(MC_RE, 'patched_v17', 'classes.dex')
if os.path.exists(out_dex):
    os.remove(out_dex)
    print('旧 dex 已删除')

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', 
       os.path.join(MC_RE, 'smali_v17'), '-o', out_dex]
print('运行:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('stdout:', r.stdout)
print('stderr:', r.stderr)
print('返回码:', r.returncode)

if os.path.exists(out_dex):
    print('新 dex 大小:', os.path.getsize(out_dex))
else:
    print('错误：dex 未生成！')
