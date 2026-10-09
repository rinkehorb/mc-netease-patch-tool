import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 1) 找 ComPy / python bridge 调用方式
print('=== ComPy / python bridge 调用模式 ===')
for m in set(re.findall(r'(ComPy|pythonBridge|pyBridge|nativeBridge)\.\w+', app)):
    print('  ', m)

# 2) 找 $utility 里跟 python/native 相关的方法
print()
print('=== $utility 里 bridge 相关方法 ===')
for m in set(re.findall(r'\$utility\.(\w*[Bb]ridge\w*|\w*[Pp]ython\w*|\w*[Nn]ative\w*)', app)):
    print('  $utility.%s' % m)

# 3) 找 sendMessageToPython / callPython 等
print()
print('=== sendMessageToPython / callPython 调用 ===')
for m in set(re.findall(r'(sendMessageToPython|callPython|invokePython|callNative)\s*\(', app)):
    print('  ', m)

# 4) 找 _setting 模块相关调用
print()
print('=== _setting / setting 模块调用 ===')
for m in set(re.findall(r'["\']setting["\']', app)):
    print('  字符串 setting 出现')
    break
# 找 sendMessageToPython("setting", ...) 的上下文
for m in re.finditer(r'.{60}sendMessageToPython\s*\(\s*["\']setting["\'].{60}', app):
    print('  ...', m.group(0), '...')
    print()
