"""签名修改器 APK - 看完整错误"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SIGNER = os.path.join(MC_RE, 'tools', 'uber-apk-signer.jar')
UNSIGNED = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
OUT_DIR = os.path.join(MC_RE, 'patcher_output', 'signed')
KEYSTORE = os.path.join(MC_RE, 'tools', 'debug.keystore')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

os.makedirs(OUT_DIR, exist_ok=True)

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', SIGNER,
       '-a', UNSIGNED, '-o', OUT_DIR,
       '--allowResign', '--skipZipAlign',
       '--ks', KEYSTORE, '--ksAlias', 'androiddebugkey',
       '--ksPass', 'android', '--ksKeyPass', 'android', '--verbose']

r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print('=== STDOUT ===')
print(r.stdout)
print('=== STDERR ===')
print(r.stderr)
print('返回码:', r.returncode)
