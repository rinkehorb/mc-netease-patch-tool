"""
apktool 解包：只不解 smali，解码 manifest 成可读 XML
"""
import os, subprocess, shutil

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
DECODE_DIR = os.path.join(MC_RE, 'manifest_decoded2')

if os.path.exists(DECODE_DIR):
    shutil.rmtree(DECODE_DIR)

# 只用 -s（不解 smali），让 manifest 解码成可读 XML
cmd = [JAVA, '-jar', APKTOOL, 'd', '-s', '-f', SRC_APK, '-o', DECODE_DIR]
print('运行:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-2000:])
print('stderr:', r.stderr[-2000:])
print('返回码:', r.returncode)

# 看 manifest 是否解码成可读 XML
manifest_path = os.path.join(DECODE_DIR, 'AndroidManifest.xml')
if os.path.exists(manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        head = f.read(500)
    print()
    print('=== AndroidManifest.xml 前 500 字符 ===')
    print(head)
