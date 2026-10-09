import re
p = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v3\com\mojang\minecraftpe\MainActivity.smali'
src = open(p, encoding='utf-8').read()

# native 方法声明
print('=== MainActivity native 方法 ===')
for m in re.finditer(r'\.method.*native.*\n\.method[^\n]*', src):
    print('  ', m.group(0).strip())

# nativeJsCall 实现
m = re.search(r'\.method[^\n]*nativeJsCall\(.*?\.end method', src, re.S)
if m:
    print()
    print('=== nativeJsCall 实现 ===')
    print(m.group(0)[:2000])

# openWebview 实现（已知 JNI 入口）
m = re.search(r'\.method[^\n]*openWebview\(.*?\.end method', src, re.S)
if m:
    print()
    print('=== openWebview 实现 ===')
    print(m.group(0)[:1500])
