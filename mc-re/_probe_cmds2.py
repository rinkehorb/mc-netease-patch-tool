import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
so = z.read('lib/armeabi-v7a/libminecraftpe.so')
strs = set(s.decode('ascii','ignore') for s in re.findall(rb'[\x20-\x7e]{4,60}', so))

# 1) nativeJsCall / jsCall 相关
print('=== jsCall / nativeCall / message handler 相关 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'jscall' in sl or 'nativecall' in sl or 'jshandler' in sl or 'onjs' in sl or 'jsbridge' in sl:
        print('  ', s)

# 2) ComPy / Python 桥相关命令
print()
print('=== ComPy / python bridge 命令 ===')
for s in sorted(strs):
    sl = s.lower()
    if 'compy' in sl or 'pycallback' in sl or 'python_' in sl or 'pyfunc' in sl:
        print('  ', s)

# 3) 找 skin picker / open skin 相关命令
print()
print('=== open_skin / show_skin / goto_skin 命令候选 ===')
for s in sorted(strs):
    sl = s.lower()
    if re.match(r'^(open|show|goto|navigate|push|enter|jump)_', sl) and 'skin' in sl:
        print('  ', s)

# 4) 找 tag / command / method 字段名
print()
print('=== 消息字段名候选 ===')
for s in sorted(strs):
    if s in ('tag','command','method','action','cmd','type','event','name','func','function'):
        print('  ', s)
