"""
修复：保留完整的 res/values/ 目录，只删其他 res/ 子目录
这样 aapt 有完整的资源表可以用
"""
import os, shutil, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')
DST = os.path.join(MC_RE, 'patcher_apk')
OUT_APK = os.path.join(MC_RE, 'patcher_output', 'patcher-unsigned.apk')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

# 重新从 manifest_decoded3 复制一份
if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(os.path.join(MC_RE, 'manifest_decoded3'), DST)
print('重新复制 apktool 项目')

# 删除不需要的目录
for d in ['lib', 'assets', 'unknown', 'build']:
    p = os.path.join(DST, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f'删除 {d}/')

# 只删 res/ 里除了 values/ 之外的目录
res_dir = os.path.join(DST, 'res')
if os.path.exists(res_dir):
    for item in os.listdir(res_dir):
        item_path = os.path.join(res_dir, item)
        if item != 'values':
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            print(f'删除 res/{item}')

# 清空 smali 目录，写修改器代码
smali_dir = os.path.join(DST, 'smali')
if os.path.exists(smali_dir):
    shutil.rmtree(smali_dir)
os.makedirs(os.path.join(smali_dir, 'com', 'example', 'mcpatcher'))

main_activity_smali = """.class public Lcom/example/mcpatcher/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.smali"

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .registers 3
    .param p1, "savedInstanceState"
    .prologue
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    new-instance v0, Landroid/widget/LinearLayout;
    invoke-direct {v0, p0}, Landroid/widget/LinearLayout;-><init>(Landroid/content/Context;)V
    const/4 v1, 0x1
    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->setOrientation(I)V
    new-instance v1, Landroid/widget/TextView;
    invoke-direct {v1, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V
    const-string v2, "MC Skin Patcher v1.0"
    invoke-virtual {v1, v2}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    invoke-virtual {v0, v1}, Landroid/widget/LinearLayout;->addView(Landroid/view/View;)V
    invoke-virtual {p0, v0}, Lcom/example/mcpatcher/MainActivity;->setContentView(Landroid/view/View;)V
    return-void
.end method
"""

with open(os.path.join(smali_dir, 'com', 'example', 'mcpatcher', 'MainActivity.smali'), 'w', encoding='utf-8') as f:
    f.write(main_activity_smali)
print('写入 MainActivity.smali')

# 修改 AndroidManifest.xml：只改包名和 Activity，其他保持原样
manifest_path = os.path.join(DST, 'AndroidManifest.xml')
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = f.read()

# 替换包名
manifest = manifest.replace('package="com.netease.mc.qihoo"', 'package="com.example.mcpatcher"')

# 替换 application 标签：保留原来的，只改 name 和 label
# 先找到 application 标签
import re
# 把整个 application 标签替换掉
old_app = re.search(r'<application[^>]*>', manifest)
if old_app:
    new_app = '<application android:label="@string/app_name" android:name="android.app.Application">'
    manifest = manifest.replace(old_app.group(0), new_app)

# 把所有 activity 标签替换成我们自己的
# 先找到 </application>，在它前面插入我们的 activity
# 先删掉所有原来的 activity 标签
manifest = re.sub(r'<activity[^>]*>.*?</activity>', '', manifest, flags=re.DOTALL)
# 也删掉 activity-alias
manifest = re.sub(r'<activity-alias[^>]*>.*?</activity-alias>', '', manifest, flags=re.DOTALL)

# 在 </application> 前插入我们的 activity
new_activity = '''<activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>'''
manifest = manifest.replace('</application>', new_activity + '\n    </application>')

# 添加权限
if 'REQUEST_INSTALL_PACKAGES' not in manifest:
    manifest = manifest.replace('</manifest>', '<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />\n</manifest>')

with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(manifest)
print('修改 AndroidManifest.xml')

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
