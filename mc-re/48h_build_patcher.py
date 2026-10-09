"""
修复：删掉 manifest 里所有 MC 特有的残留标签
"""
import os, re, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

manifest_path = os.path.join(DST, 'AndroidManifest.xml')
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()

print('=== 修改前的 manifest ===')
print(manifest[:2000])
print('...')

# 删掉所有 provider、receiver、service、meta-data 标签（MC 特有的）
# 只保留 application 和我们的 activity
manifest = re.sub(r'<provider[^>]*>.*?</provider>', '', manifest, flags=re.DOTALL)
manifest = re.sub(r'<receiver[^>]*>.*?</receiver>', '', manifest, flags=re.DOTALL)
manifest = re.sub(r'<service[^>]*>.*?</service>', '', manifest, flags=re.DOTALL)
manifest = re.sub(r'<meta-data[^>]*/>', '', manifest)

# 删掉 uses-feature 标签（MC 特有的）
manifest = re.sub(r'<uses-feature[^>]*/>', '', manifest)

with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(manifest)

print()
print('=== 修改后的 manifest ===')
print(manifest)

# 重新构建
build_dir = os.path.join(DST, 'build')
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)

if os.path.exists(OUT_APK):
    os.remove(OUT_APK)

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', APKTOOL, 'b', DST,
       '--frame-path', FRAME_DIR, '-o', OUT_APK, '-f']

print()
print('运行 apktool b...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-1000:])
print('stderr:', r.stderr[-1000:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
