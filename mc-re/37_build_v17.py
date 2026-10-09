"""
v17 补丁：在 onCreate 里加运行时设置 layoutInDisplayCutoutMode = SHORT_EDGES
因为 targetSdk 22 太低，manifest 属性不生效，必须代码里强制设置
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

# 从 v15 的 smali 树继续改
src_smali = os.path.join(MC_RE, 'smali_v15')
dst_smali = os.path.join(MC_RE, 'smali_v17')
if os.path.exists(dst_smali):
    shutil.rmtree(dst_smali)
shutil.copytree(src_smali, dst_smali)
print('复制 smali_v15 -> smali_v17 完成')

main_activity = os.path.join(dst_smali, 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')
with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到之前加的 setSystemUiVisibility 行，在它后面加 layoutInDisplayCutoutMode 设置
# 之前加的是：
#     const v4, 0x1706
#     invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V

old_code = '''    .line 636  # 全屏沉浸模式补丁
    const v4, 0x1706
    invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V'''

new_code = '''    .line 636  # 全屏沉浸模式补丁
    const v4, 0x1706
    invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V

    # 运行时强制设置刘海屏适配（targetSdk 22 太低，manifest 属性不生效）
    invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
    move-result-object v5
    invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
    move-result-object v6
    const/4 v0, 0x1
    iput v0, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V'''

assert old_code in content, '找不到之前加的 setSystemUiVisibility 代码！'
content = content.replace(old_code, new_code, 1)

with open(main_activity, 'w', encoding='utf-8') as f:
    f.write(content)
print('MainActivity.smali 已修改（加 layoutInDisplayCutoutMode 运行时设置）')

# 重编译 dex
out_dex = os.path.join(MC_RE, 'patched_v17', 'classes.dex')
os.makedirs(os.path.dirname(out_dex), exist_ok=True)

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', dst_smali, '-o', out_dex]
print('运行 smali 重编译...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('stdout:', r.stdout[-500:])
print('stderr:', r.stderr[-500:])
print('返回码:', r.returncode)

if r.returncode == 0:
    print('dex 大小:', os.path.getsize(out_dex))
