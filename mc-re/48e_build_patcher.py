"""
修复：从 MC 原版 manifest 开始改，保持正确格式
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

# 先看看 MC 原版 manifest 开头是什么样的
orig_manifest = os.path.join(MC_RE, 'manifest_decoded3', 'AndroidManifest.xml')
with open(orig_manifest, 'r', encoding='utf-8') as f:
    orig_content = f.read()

# 打印前 500 字符，看看格式
print('=== MC 原版 manifest 前 500 字符 ===')
print(orig_content[:500])
print()

# 基于 MC 的 manifest 格式，写修改器的 manifest
# 保留命名空间声明、uses-sdk、application 标签的格式
new_manifest = '''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" android:compileSdkVersion="28" android:compileSdkVersionCodename="9" package="com.example.mcpatcher" platformBuildVersionCode="28" platformBuildVersionName="9">
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="28" />
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
    <application android:allowBackup="true" android:label="@string/app_name">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'''

with open(os.path.join(DST, 'AndroidManifest.xml'), 'w', encoding='utf-8') as f:
    f.write(new_manifest)
print('写入新的 AndroidManifest.xml')

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
print('stderr:', r.stderr[-1000:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
