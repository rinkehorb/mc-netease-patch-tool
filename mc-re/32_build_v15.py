"""
v15 补丁：在 MainActivity.onCreate 里加全屏沉浸模式（隐藏状态栏+导航栏，延伸到刘海区域）
基于 v14（Miku 皮肤 + 隐藏材质/玩法按钮）
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SMALI_JAR = os.path.join(MC_RE, 'tools', 'smali.jar')

# 1) 复制 smali_v3 到 smali_v15
src_smali = os.path.join(MC_RE, 'smali_v3')
dst_smali = os.path.join(MC_RE, 'smali_v15')
if os.path.exists(dst_smali):
    shutil.rmtree(dst_smali)
shutil.copytree(src_smali, dst_smali)
print('复制 smali_v3 -> smali_v15 完成')

# 2) 修改 MainActivity.smali
main_activity = os.path.join(dst_smali, 'com', 'mojang', 'minecraftpe', 'MainActivity.smali')
with open(main_activity, 'r', encoding='utf-8') as f:
    content = f.read()

# 插入点：在 onAppStart 调用之后
# 原代码：
#     invoke-virtual {v1, v3}, Lcom/mojang/minecraftpe/platforms/Platform;->onAppStart(Landroid/view/View;)V
#
# 插入全屏代码：
#     const v4, 0x1706   # IMMERSIVE_STICKY|FULLSCREEN|HIDE_NAVIGATION|LAYOUT_STABLE|LAYOUT_HIDE_NAVIGATION|LAYOUT_FULLSCREEN
#     invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V

old_line = '    invoke-virtual {v1, v3}, Lcom/mojang/minecraftpe/platforms/Platform;->onAppStart(Landroid/view/View;)V'
new_lines = old_line + '\n\n' + \
    '    .line 636  # 全屏沉浸模式补丁\n' + \
    '    const v4, 0x1706\n' + \
    '    invoke-virtual {v3, v4}, Landroid/view/View;->setSystemUiVisibility(I)V\n'

assert old_line in content, '找不到 onAppStart 调用行！'
content = content.replace(old_line, new_lines, 1)

with open(main_activity, 'w', encoding='utf-8') as f:
    f.write(content)
print('MainActivity.smali 已修改（加全屏 flags）')

# 3) 用 smali 重编译成 dex
out_dex = os.path.join(MC_RE, 'patched_v15', 'classes.dex')
os.makedirs(os.path.dirname(out_dex), exist_ok=True)

cmd = [JAVA, '-Xmx6g', '-jar', SMALI_JAR, 'assemble', dst_smali, '-o', out_dex]
print('运行 smali 重编译...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('stdout:', r.stdout[-500:])
print('stderr:', r.stderr[-500:])
print('返回码:', r.returncode)

if r.returncode == 0:
    print('dex 大小:', os.path.getsize(out_dex))
