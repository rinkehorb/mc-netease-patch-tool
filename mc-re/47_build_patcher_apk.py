"""
MC 修改器 APK 生成器
"""
import os, shutil, subprocess, re

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
APKTOOL = os.path.join(MC_RE, 'tools', 'apktool.jar')
FRAME_DIR = os.path.join(MC_RE, 'tools', 'framework')

SRC = os.path.join(MC_RE, 'manifest_decoded3')
DST = os.path.join(MC_RE, 'patcher_apk')

if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
print('复制 apktool 项目完成')

# 删除不需要的目录
for d in ['lib', 'assets', 'unknown']:
    p = os.path.join(DST, d)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f'删除 {d}/')

# 删除 res/ 里除了 values/ 之外的所有目录
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

# 清空 smali 目录
smali_dir = os.path.join(DST, 'smali')
if os.path.exists(smali_dir):
    shutil.rmtree(smali_dir)
os.makedirs(os.path.join(smali_dir, 'com', 'example', 'mcpatcher'))
print('清空 smali/ 目录')

# 写 MainActivity.smali
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

# 写 AndroidManifest.xml
new_manifest = """<?xml version="1.0" encoding="utf-8" standalone="no"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.mcpatcher"
    android:versionCode="1"
    android:versionName="1.0">
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="28" />
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
    <application android:label="MC Patcher">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

with open(os.path.join(DST, 'AndroidManifest.xml'), 'w', encoding='utf-8') as f:
    f.write(new_manifest)
print('修改 AndroidManifest.xml')

# 写 apktool.yml
new_yml = """!!brut.androlib.meta.ApkInfo
versionCode: '1'
versionName: '1.0'
apkFileName: null
isFrameworkApk: false
packageId: '7f'
sharedLibrary: false
sparseResources: false
sdkInfo:
  minSdkVersion: '21'
  targetSdkVersion: '28'
sharedLibrary: false
sparseResources: false
useAaptPlugin: false
compileSdkVersion: '28'
compileSdkVersionCodename: '9'
"""

with open(os.path.join(DST, 'apktool.yml'), 'w', encoding='utf-8') as f:
    f.write(new_yml)
print('修改 apktool.yml')

print()
print('项目结构准备完成！')
