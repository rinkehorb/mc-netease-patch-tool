"""
apktool 重打包（指定 tmpdir）
"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
DECODE_DIR = os.path.join(MC_RE, 'manifest_decoded3')
OUT_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-unsigned.apk')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', APKTOOL, 'b', DECODE_DIR,
       '--frame-path', FRAME_DIR,
       '-o', OUT_APK, '-f']
print('运行:', ' '.join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-2000:])
print('stderr:', r.stderr[-2000:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
