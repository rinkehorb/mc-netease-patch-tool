"""v5 签名脚本"""
import os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SIGNER = os.path.join(MC_RE, 'tools', 'uber-apk-signer.jar')
UNSIGNED = os.path.join(MC_RE, 'patched_v5', 'Minecraft-unsigned.apk')
OUT_DIR = os.path.join(MC_RE, 'patched_v5', 'signed')
KEYSTORE = os.path.join(MC_RE, 'tools', 'debug.keystore')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

cmd = [
    JAVA,
    f'-Djava.io.tmpdir={TMP_DIR}',
    '-jar', SIGNER,
    '-a', UNSIGNED,
    '-o', OUT_DIR,
    '--allowResign',
    '--skipZipAlign',
    '--ks', KEYSTORE,
    '--ksAlias', 'androiddebugkey',
    '--ksPass', 'android',
    '--ksKeyPass', 'android',
]

print('运行签名...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print('STDOUT:')
print(r.stdout[-2000:])
print('STDERR:')
print(r.stderr[-1000:])
print('返回码:', r.returncode)
