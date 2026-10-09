import zipfile, re
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
app = z.read('assets/web/static/js/app.99ba093c66352ad3633f.js').decode('utf-8','ignore')

# 看 init_skin_list / set_modify_skin_path 等函数的调用上下文
for fn in ['init_skin_list', 'set_skin_list', 'set_modify_skin_path', 'set_costom_skin_path', 'get_raw_skins_path', 'add_skin_record']:
    idx = app.find(fn)
    if idx >= 0:
        ctx = app[max(0,idx-80):idx+len(fn)+80]
        print('=== %s ===' % fn)
        print('  ...', ctx, '...')
        print()

# 找桥对象名（xxx.init_skin_list 或 xxx.set_skin_list）
print('=== 桥对象调用模式 ===')
for m in set(re.findall(r'(\w+)\.(init_skin_list|set_skin_list|set_modify_skin_path|get_raw_skins_path)\s*\(', app)):
    print('  %s.%s()' % m)
