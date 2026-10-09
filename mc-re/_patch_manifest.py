"""
修改 AndroidManifest.xml：加刘海屏适配 + 全屏属性
然后用 apktool 重打包
"""
import os, re

DECODE_DIR = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\manifest_decoded3'
manifest_path = os.path.join(DECODE_DIR, 'AndroidManifest.xml')

with open(manifest_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 MainActivity 的 activity 标签里加属性
# 原标签：
# <activity android:alwaysRetainTaskState="true" ... android:windowSoftInputMode="adjustResize">
# 加：android:windowLayoutInDisplayCutoutMode="shortEdges"

old_activity = '<activity android:alwaysRetainTaskState="true" android:configChanges="fontScale|keyboard|keyboardHidden|locale|mcc|mnc|navigation|orientation|screenLayout|screenSize|smallestScreenSize|touchscreen|uiMode" android:debuggable="false" android:excludeFromRecents="false" android:label="@string/app_name_short" android:name="com.mojang.minecraftpe.MainActivity" android:screenOrientation="portrait" android:theme="@style/SplashTheme" android:windowSoftInputMode="adjustResize">'

new_activity = '<activity android:alwaysRetainTaskState="true" android:configChanges="fontScale|keyboard|keyboardHidden|locale|mcc|mnc|navigation|orientation|screenLayout|screenSize|smallestScreenSize|touchscreen|uiMode" android:debuggable="false" android:excludeFromRecents="false" android:label="@string/app_name_short" android:name="com.mojang.minecraftpe.MainActivity" android:screenOrientation="portrait" android:theme="@style/SplashTheme" android:windowLayoutInDisplayCutoutMode="shortEdges" android:windowSoftInputMode="adjustResize">'

assert old_activity in content, '找不到 MainActivity activity 标签！'
content = content.replace(old_activity, new_activity, 1)

with open(manifest_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('AndroidManifest.xml 已修改：加了 android:windowLayoutInDisplayCutoutMode="shortEdges"')
print()

# 验证
with open(manifest_path, 'r', encoding='utf-8') as f:
    c = f.read()
if 'windowLayoutInDisplayCutoutMode' in c:
    print('验证：属性已添加成功')
else:
    print('验证：属性添加失败！')
