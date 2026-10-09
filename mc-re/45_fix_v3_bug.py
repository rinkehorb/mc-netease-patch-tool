"""
v19 修复：正确获取 decorView，不再用未初始化的 v3
之前的 bug：直接在 v3 上调用 setSystemUiVisibility，但 v3 里是垃圾值
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

# 从 v17 的 smali 树继续改
src_smali = os.path.join(MC_RE, 'smali_v17')
dst_smali = os.path.join(MC_RE, 'smali_v19')
if os.path.exists(dst_smali):
    shutil.rmtree(dst_smali)
shutil.copytree(src_smali, dst_smali)

main_activity = os.path.join(dst_smali, 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')
with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到错误的代码，替换成正确的
# 错误的代码：
#     .line 636  # 全屏沉浸模式补丁
#     const v4, 0x1706
#     invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V
#
#     # 运行时强制设置刘海屏适配（targetSdk 22 太低，manifest 属性不生效）
#     invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
#     move-result-object v5
#     invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
#     move-result-object v6
#     const/4 v7, 0x1
#     iput v7, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
#     invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V

old_code = '''    .line 636  # 全屏沉浸模式补丁
    const v4, 0x1706
    invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V

    # 运行时强制设置刘海屏适配（targetSdk 22 太低，manifest 属性不生效）
    invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
    move-result-object v5
    invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
    move-result-object v6
    const/4 v7, 0x1
    iput v7, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V'''

# 正确的代码：先获取 Window，再获取 decorView，再设置 flags
new_code = '''    .line 636  # 全屏沉浸模式补丁
    # 先正确获取 Window 和 decorView
    invoke-virtual {p0}, Landroid/app/NativeActivity;->getWindow()Landroid/view/Window;
    move-result-object v5
    invoke-virtual {v5}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v3

    # 设置全屏 flags（在 decorView 上调用）
    const v4, 0x1706
    invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V

    # 运行时强制设置刘海屏适配
    invoke-virtual {v5}, Landroid/view/Window;->getAttributes()Landroid/view/WindowManager$LayoutParams;
    move-result-object v6
    const/4 v7, 0x1
    iput v7, v6, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I
    invoke-virtual {v5, v6}, Landroid/view/Window;->setAttributes(Landroid/view/WindowManager$LayoutParams;)V'''

assert old_code in content, '找不到旧的全屏代码！'
content = content.replace(old_code, new_code, 1)

with open(main_activity, 'w', encoding='utf-8') as f:
    f.write(content)

print('已修复：先获取 Window 和 decorView，再设置 flags')
print('不再用未初始化的 v3')

# 重编译 dex
out_dex = os.path.join(MC_RE, 'patched_v19', 'classes.dex')
os.makedirs(os.path.dirname(out_dex), exist_ok=True)
if os.path.exists(out_dex):
    os.remove(out_dex)

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', dst_smali, '-o', out_dex]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('编译返回码:', r.returncode)
if r.returncode == 0:
    print('dex 大小:', os.path.getsize(out_dex))
else:
    print('stderr:', r.stderr[-500:])
