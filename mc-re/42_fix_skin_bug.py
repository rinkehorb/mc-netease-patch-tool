"""
修复 v17b 皮肤 bug：v0 被覆盖导致联网时加载错误皮肤包
方案：不用 v0 存常量，改用新增的 v7 寄存器
.registers 9 → .registers 10（多一个局部寄存器）
const/4 v0, 0x1 → const/4 v7, 0x1
iput v0, ... → iput v7, ...
"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

main_activity = os.path.join(MC_RE, 'smali_v17', 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')

with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. .registers 9 → .registers 10
old_reg = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 9'
new_reg = '.method public onCreate(Landroid/os/Bundle;)V\n    .registers 10'
assert old_reg in content, '找不到 .registers 9！'
content = content.replace(old_reg, new_reg, 1)

# 2. const/4 v0, 0x1 → const/4 v7, 0x1
# 3. iput v0, v6 → iput v7, v6
old_code = '''    # 运行时强制设置刘海屏适配（targetSdk 22 太低，manifest 属性不生效）
    invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
    move-result-object v5
    invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
    move-result-object v6
    const/4 v0, 0x1
    iput v0, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V'''

new_code = '''    # 运行时强制设置刘海屏适配（targetSdk 22 太低，manifest 属性不生效）
    invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
    move-result-object v5
    invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
    move-result-object v6
    const/4 v7, 0x1
    iput v7, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V'''

assert old_code in content, '找不到刘海屏设置代码！'
content = content.replace(old_code, new_code, 1)

with open(main_activity, 'w', encoding='utf-8') as f:
    f.write(content)

print('已修复：')
print('  .registers 9 → .registers 10')
print('  const/4 v0, 0x1 → const/4 v7, 0x1（不再覆盖 v0）')

# 重编译 dex
out_dex = os.path.join(MC_RE, 'patched_v17', 'classes.dex')
if os.path.exists(out_dex):
    os.remove(out_dex)

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', 
       os.path.join(MC_RE, 'smali_v17'), '-o', out_dex]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('编译返回码:', r.returncode)
if r.returncode == 0:
    print('dex 大小:', os.path.getsize(out_dex))
