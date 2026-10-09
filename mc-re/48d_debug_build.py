"""看完整的构建错误"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', APKTOOL, 'b', DST,
       '--frame-path', FRAME_DIR, '-f', '--verbose']

r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('=== STDOUT (最后 2000 字符) ===')
print(r.stdout[-2000:])
print()
print('=== STDERR (最后 2000 字符) ===')
print(r.stderr[-2000:])
