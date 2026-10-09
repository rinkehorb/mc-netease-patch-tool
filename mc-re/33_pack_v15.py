"""
v15 重打包：v14 资源 + 全屏 dex
"""
import zipfile, os

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
OUT_APK = os.path.join(MC_RE, 'patched_v15', 'Minecraft-unsigned.apk')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'
NEW_DEX = os.path.join(MC_RE, 'patched_v15', 'classes.dex')

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)
zin = zipfile.ZipFile(SRC_APK, 'r')

# v14 的 index.html（隐藏材质/玩法按钮）
html = zin.read('assets/web/index.html').decode('utf-8')

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

with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()

def patch_lang(data, name):
    text = data.decode('utf-8')
    lines = []
    for line in text.splitlines():
        if line.startswith('skin.name.alex='):
            lines.append(f'skin.name.alex={name}')
        else:
            lines.append(line)
    return '\n'.join(lines).encode('utf-8')

zh_cn = patch_lang(zin.read('assets/resource_packs/vanilla/texts/zh_CN.lang'), 'Miku')
en_us = patch_lang(zin.read('assets/resource_packs/vanilla/texts/en_US.lang'), 'Miku')

with open(NEW_DEX, 'rb') as f:
    new_dex = f.read()

replacements = {
    'classes.dex': new_dex,
    'assets/web/index.html': new_html.encode('utf-8'),
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}

zout = zipfile.ZipFile(OUT_APK, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename in replacements:
        data = replacements[item.filename]
        print('  替换:', item.filename)
    zout.writestr(item, data)

zin.close()
zout.close()
print()
print('输出:', OUT_APK, os.path.getsize(OUT_APK), 'bytes')
