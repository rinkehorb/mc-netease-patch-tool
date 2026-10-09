"""
v16 组装：apktool 构建的 APK（刘海屏 manifest）+ v15 dex（全屏 flags）+ v14 资源（Miku 皮肤 + 隐藏按钮）
"""
import zipfile, os, shutil

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
BASE_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-unsigned.apk')  # apktool 构建的
V15_DEX = os.path.join(MC_RE, 'patched_v15', 'classes.dex')  # 带全屏 flags 的 dex
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'
FINAL_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-final-unsigned.apk')

# 读 v15 dex
with open(V15_DEX, 'rb') as f:
    v15_dex = f.read()

# 读 Miku 皮肤
with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()

# 读原 APK 的 lang 文件（用来改名字）
orig = zipfile.ZipFile(os.path.join(MC_RE, 'original', 'Minecraft.apk'), 'r')

def patch_lang(data, name):
    text = data.decode('utf-8')
    lines = []
    for line in text.splitlines():
        if line.startswith('skin.name.alex='):
            lines.append(f'skin.name.alex={name}')
        else:
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')

zh_cn = patch_lang(orig.read('assets/resource_packs/vanilla/texts/zh_CN.lang'), 'Miku')
en_us = patch_lang(orig.read('assets/resource_packs/vanilla/texts/en_US.lang'), 'Miku')

# 读原 index.html（用来注入隐藏按钮 JS）
html = orig.read('assets/web/index.html').decode('utf-8')
inject = '''
<script>
(function(){
  var hideTexts = ['材质光影', '功能玩法'];
  function hideButtons(){
    try {
      var all = document.querySelectorAll('div,span,a,button,li,p,h1,h2,h3');
      all.forEach(function(el){
        var t = (el.textContent || '').trim();
        for(var i=0; i<hideTexts.length; i++){
          if(t.indexOf(hideTexts[i]) === 0 && t.length < 20){
            var node = el;
            for(var j=0; j<6; j++){
              if(!node.parentElement) break;
              node = node.parentElement;
              var cls = typeof node.className === 'string' ? node.className : '';
              if(cls.indexOf('item') >= 0){
                node.style.display = 'none';
                break;
              }
            }
            el.style.display = 'none';
            break;
          }
        }
      });
    } catch(e){}
  }
  window.addEventListener('load', function(){
    setTimeout(hideButtons, 500);
    setTimeout(hideButtons, 1500);
    setTimeout(hideButtons, 3000);
    setTimeout(hideButtons, 5000);
  });
})();
</script>
'''
new_html = html.replace('</body>', inject + '</body>')

orig.close()

# 替换映射
replacements = {
    'classes.dex': v15_dex,
    'assets/web/index.html': new_html.encode('utf-8'),
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}

# 基于 apktool 构建的 APK，替换文件
zin = zipfile.ZipFile(BASE_APK, 'r')
zout = zipfile.ZipFile(FINAL_APK, 'w', zipfile.ZIP_DEFLATED)

for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename in replacements:
        data = replacements[item.filename]
        print('  替换:', item.filename)
    zout.writestr(item, data)

zin.close()
zout.close()

print()
print('最终 APK:', FINAL_APK)
print('大小:', os.path.getsize(FINAL_APK))
