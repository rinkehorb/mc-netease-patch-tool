"""
apktool 解包：指定 frame-path，解码 manifest
"""
import os, subprocess, shutil

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
DECODE_DIR = os.path.join(MC_RE, 'manifest_decoded3')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')

os.makedirs(FRAME_DIR, exist_ok=True)
if os.path.exists(DECODE_DIR):
    shutil.rmtree(DECODE_DIR)

cmd = [JAVA, '-jar', APKTOOL, 'd', '-s', '-f',
       '--frame-path', FRAME_DIR,
       SRC_APK, '-o', DECODE_DIR]
print('运行:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-2000:])
print('stderr:', r.stderr[-2000:])
print('返回码:', r.returncode)

manifest_path = os.path.join(DECODE_DIR, 'AndroidManifest.xml')
if os.path.exists(manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
    print()
    print('=== AndroidManifest.xml 前 1000 字符 ===')
    print(content[:1000])
    print()
    print('总长度:', len(content))
