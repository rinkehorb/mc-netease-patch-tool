"""
修复：res/values/ 里只保留 strings.xml，删掉 styles.xml 等其他文件
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

# 看 values/ 目录里有什么
values_dir = os.path.join(DST, 'res', 'values')
print('res/values/ 目录内容:')
for f in os.listdir(values_dir):
    print(f'  {f}')

# 只保留 strings.xml，删掉其他所有文件
for f in os.listdir(values_dir):
    if f != 'strings.xml':
        os.remove(os.path.join(values_dir, f))
        print(f'删除 res/values/{f}')

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
print('stderr:', r.stderr[-1500:])
print('返回码:', r.returncode)

if os.path.exists(OUT_APK):
    print()
    print('输出 APK 大小:', os.path.getsize(OUT_APK))
