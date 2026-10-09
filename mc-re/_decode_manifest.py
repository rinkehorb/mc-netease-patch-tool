"""
用 apktool 只解包 manifest（不解资源、不解 smali），然后加 windowLayoutInDisplayCutoutMode
"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
DECODE_DIR = os.path.join(MC_RE, 'manifest_decoded')

# 清理旧目录
import shutil
if os.path.exists(DECODE_DIR):
    shutil.rmtree(DECODE_DIR)

# 只解 manifest：-s 不解 smali，-r 不解资源
cmd = [JAVA, '-jar', APKTOOL, 'd', '-s', '-r', '-f', SRC_APK, '-o', DECODE_DIR]
print('运行:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('stdout:', r.stdout[-1000:])
print('stderr:', r.stderr[-1000:])
print('返回码:', r.returncode)

# 看看解出来什么
if os.path.exists(DECODE_DIR):
    print()
    print('解包目录内容:')
    for root, dirs, files in os.walk(DECODE_DIR):
        for f in files:
            fp = os.path.join(root, f)
            print('  ', os.path.relpath(fp, DECODE_DIR), os.path.getsize(fp))
