import zipfile
z = zipfile.ZipFile(r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\original\Minecraft.apk')
html = z.read('assets/web/index.html').decode('utf-8')

# 看 index.html 的结尾结构（</body> 前注入点）
print('=== index.html 最后 1500 字符 ===')
print(html[-1500:])
