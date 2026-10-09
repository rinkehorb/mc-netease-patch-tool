"""
v16 最终组装：确保所有补丁文件都正确替换
"""
import zipfile, os

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
BASE_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-unsigned.apk')
V15_DEX = os.path.join(MC_RE, 'patched_v15', 'classes.dex')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'
FINAL_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-final-unsigned.apk')

# 读所有要替换的文件
with open(V15_DEX, 'rb') as f:
    v15_dex = f.read()
print('v15 dex 大小:', len(v15_dex))

with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()
print('Miku 皮肤大小:', len(miku_data))

# 从原 APK 读 lang 和 html
orig = zipfile.ZipFile(os.path.join(MC_RE, 'original', 'Minecraft.apk'), 'r')

def patch_lang(data, name):
    text = data.decode('utf-8')
    lines = [f'skin.name.alex={name}' if line.startswith('skin.name.alex=') else line for line in text.splitlines()]
    return '\n'.join(lines).encode('utf-8')

zh_cn = patch_lang(orig.read('assets/resource_packs/vanilla/texts/zh_CN.lang'), 'Miku')
en_us = patch_lang(orig.read('assets/resource_packs/vanilla/texts/en_US.lang'), 'Miku')

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
new_html = html.replace('</body>', inject + '</body>').encode('utf-8')
orig.close()

# 替换映射
replacements = {
    'classes.dex': v15_dex,
    'assets/web/index.html': new_html,
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}
print('替换映射文件数:', len(replacements))

# 基于 apktool 构建的 APK，替换文件
zin = zipfile.ZipFile(BASE_APK, 'r')
zout = zipfile.ZipFile(FINAL_APK, 'w', zipfile.ZIP_DEFLATED)

replaced = []
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename in replacements:
        data = replacements[item.filename]
        replaced.append(item.filename)
    zout.writestr(item, data)

zin.close()
zout.close()

print()
print('实际替换的文件:')
for r in replaced:
    print('  ', r)
print()
print('最终 APK:', FINAL_APK)
print('大小:', os.path.getsize(FINAL_APK))
