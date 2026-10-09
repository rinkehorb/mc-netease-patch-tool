"""
v6 补丁：恢复原始 Alex 细手臂，皮肤换成 Miku.png，名字改成 Miku
- base.json / skins.json 用原包原始（细手臂 3 宽）
- alex.png / alex_dev.png 替换成 Miku.png
- lang 文件 skin.name.alex = Miku
- 保留 v2/v3/v4 所有 Java 层补丁（XML 弹窗自动关闭、360 浮窗 NOP）
"""
import zipfile, os, json

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
OUT_APK = os.path.join(MC_RE, 'patched_v6', 'Minecraft-unsigned.apk')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)

zin = zipfile.ZipFile(SRC_APK, 'r')

# --- 准备要替换的文件内容 ---

# 1) lang 文件：把 skin.name.alex 改成 Miku
def patch_lang(data: bytes, new_name: str) -> bytes:
    text = data.decode('utf-8')
    # 替换 skin.name.alex=xxx
    lines = []
    for line in text.splitlines():
        if line.startswith('skin.name.alex='):
            lines.append(f'skin.name.alex={new_name}')
        else:
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')

zh_cn = patch_lang(zin.read('assets/resource_packs/vanilla/texts/zh_CN.lang'), 'Miku')
en_us = patch_lang(zin.read('assets/resource_packs/vanilla/texts/en_US.lang'), 'Miku')

# 2) Miku 皮肤图
with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()

# 3) base.json / skins.json / skindefs.json 直接用原包原始的（细手臂 3 宽）
#    不需要修改，原样复制即可

# --- 替换映射 ---
replacements = {
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
    # base.json / skins.json / skindefs.json 用原包原始的，不需要替换
}

# --- 写入新 APK ---
zout = zipfile.ZipFile(OUT_APK, 'w', zipfile.ZIP_DEFLATED)

# v4 的 classes.dex（包含 v1+v2+v3+v4 所有 Java 层补丁）
v4_dex_path = os.path.join(MC_RE, 'patched_v3', 'classes.dex')
with open(v4_dex_path, 'rb') as f:
    v4_dex = f.read()

for item in zin.infolist():
    data = zin.read(item.filename)
    
    if item.filename == 'classes.dex':
        data = v4_dex
        print('  替换: classes.dex (v4 补丁版)')
    elif item.filename in replacements:
        data = replacements[item.filename]
        print('  替换:', item.filename)
    
    zout.writestr(item, data)

zin.close()
zout.close()

print()
print('输出:', OUT_APK)
print('大小:', os.path.getsize(OUT_APK))
