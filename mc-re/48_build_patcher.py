"""用 apktool 构建修改器 APK"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', APKTOOL, 'b', DST,
       '--frame-path', FRAME_DIR, '-o', OUT_APK, '-f']

print('运行 apktool b...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-1500:])
print('stderr:', r.stderr[-1000:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
