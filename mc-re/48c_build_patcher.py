"""修复：加一个最基本的 res/values/ 目录，让 resources.arsc 有效"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

# 创建最基本的 res/values/ 目录
values_dir = os.path.join(DST, 'res', 'values')
os.makedirs(values_dir, exist_ok=True)

# 写最基本的 strings.xml
strings_xml = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">MC Patcher</string>
</resources>
"""
with open(os.path.join(values_dir, 'strings.xml'), 'w', encoding='utf-8') as f:
    f.write(strings_xml)
print('创建 res/values/strings.xml')

# 修改 AndroidManifest.xml，用 @string/app_name 代替硬编码
manifest_path = os.path.join(DST, 'AndroidManifest.xml')
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()
manifest = manifest.replace('android:label="MC Patcher"', 'android:label="@string/app_name"')
with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(manifest)
print('修改 AndroidManifest.xml 用 @string/app_name')

# 删掉 build 缓存
build_dir = os.path.join(DST, 'build')
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)

# 重新构建
if os.path.exists(OUT_APK):
    os.remove(OUT_APK)

cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', APKTOOL, 'b', DST,
       '--frame-path', FRAME_DIR, '-o', OUT_APK, '-f']

print('运行 apktool b...')
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print('stdout:', r.stdout[-1000:])
print('stderr:', r.stderr[-500:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
