"""
v5 补丁：在 H5 index.html 注入悬浮"换肤"按钮，点击跳转到 /profile/view/ 档案页
同时保留 v2/v3/v4 的所有补丁
"""
import zipfile, shutil, os, re

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
OUT_APK = os.path.join(MC_RE, 'patched_v5', 'Minecraft-unsigned.apk')
V4_ASSETS = os.path.join(MC_RE, 'v4_assets')

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)

# 读取原 APK
zin = zipfile.ZipFile(SRC_APK, 'r')

# 新的 H5 index.html —— 注入悬浮按钮
original_html = zin.read('assets/web/index.html').decode('utf-8')

# 注入的悬浮按钮 HTML+CSS+JS
inject_html = '''
<div id="mc-skin-fab" style="position:fixed;top:60px;right:16px;z-index:99999;
  width:56px;height:56px;border-radius:50%;background:#4CAF50;color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:24px;
  box-shadow:0 2px 8px rgba(0,0,0,0.4);cursor:pointer;user-select:none;
  font-family:sans-serif;" onclick="mcSkinFabClick()">&#128104;&#8205;&#127918;</div>
<script>
function mcSkinFabClick(){
  try {
    // 尝试跳转到档案/皮肤页面
    window.location.hash = '#/profile/view/';
    console.log('[MC-SKIN] jumped to #/profile/view/');
  } catch(e) {
    console.log('[MC-SKIN] jump failed: ' + e);
    alert('跳转失败: ' + e);
  }
}
// 页面加载后自动打个日志，确认按钮注入成功
window.addEventListener('load', function(){
  console.log('[MC-SKIN] FAB injected, ready.');
});
</script>
'''

# 在 </body> 前注入
new_html = original_html.replace('</body>', inject_html + '</body>')

print('原始 index.html 大小:', len(original_html))
print('注入后 index.html 大小:', len(new_html))
print('注入内容长度:', len(new_html) - len(original_html))

# 写入新 APK
zout = zipfile.ZipFile(OUT_APK, 'w', zipfile.ZIP_DEFLATED)

# v4 的 classes.dex（包含 v1+v2+v3+v4 所有 Java 层补丁：XML 弹窗自动关闭、360 浮窗 NOP）
v4_dex_path = os.path.join(MC_RE, 'patched_v3', 'classes.dex')
print('v4 classes.dex 存在:', os.path.exists(v4_dex_path))

# 复制所有条目，替换需要改的
for item in zin.infolist():
    data = zin.read(item.filename)
    
    # 替换 classes.dex 为 v4 版本（含所有 Java 层补丁）
    if item.filename == 'classes.dex':
        with open(v4_dex_path, 'rb') as f:
            data = f.read()
        print('  替换: classes.dex (v4 补丁版)')
    
    # 替换 H5 index.html
    elif item.filename == 'assets/web/index.html':
        data = new_html.encode('utf-8')
        print('  替换: assets/web/index.html')
    
    # 替换 v4 的 assets 文件（lang 改名 + base.json 粗手臂 + 皮肤替换）
    elif item.filename in (
        'assets/resource_packs/vanilla/texts/zh_CN.lang',
        'assets/resource_packs/vanilla/texts/en_US.lang',
        'assets/resource_packs/skins/skinpacks/Base/base.json',
        'assets/resource_packs/skins/skinpacks/Base/skindefs.json',
        'assets/resource_packs/skins/skinpacks/Base/alex.png',
        'assets/resource_packs/skins/skinpacks/Base/alex_dev.png',
    ):
        v4_path = os.path.join(V4_ASSETS, os.path.basename(item.filename))
        if os.path.exists(v4_path):
            with open(v4_path, 'rb') as f:
                data = f.read()
            print('  替换:', item.filename)
    
    # 其他文件原样复制
    zout.writestr(item, data)

zin.close()
zout.close()

print()
print('输出:', OUT_APK)
print('大小:', os.path.getsize(OUT_APK))
