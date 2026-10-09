"""检查环境里有没有 Android SDK、gradle、javac 等编译工具"""
import os, shutil, subprocess

# 检查 javac
javac = shutil.which('javac')
print('javac:', javac or '未找到')

# 检查 gradle
gradle = shutil.which('gradle')
print('gradle:', gradle or '未找到')

# 检查 Android SDK
android_home = os.environ.get('ANDROID_HOME', '')
print('ANDROID_HOME:', android_home or '未设置')

# 检查常见路径
paths_to_check = [
    r'C:\Users\Administrator\AppData\Local\Android\Sdk',
    r'C:\Android\Sdk',
    r'C:\Users\Administrator\AppData\Local\Programs\Android Studio',
]
for p in paths_to_check:
    if os.path.exists(p):
        print(f'找到: {p}')
        for root, dirs, files in os.walk(p):
            depth = root.replace(p, '').count(os.sep)
            if depth < 2:
                print(f'  {root}')

# 检查 JDK（不是 JRE）
java_home = os.environ.get('JAVA_HOME', '')
print('JAVA_HOME:', java_home or '未设置')

# 检查 mc-re/tools 里有什么
mc_tools = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\tools'
if os.path.exists(mc_tools):
    print()
    print('mc-re/tools 目录:')
    for f in os.listdir(mc_tools):
        print(f'  {f}')
