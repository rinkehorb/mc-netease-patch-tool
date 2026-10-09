"""
v14 补丁：回到 v7 成功逻辑——前缀匹配 + 找 className 含 item 的父元素隐藏
关键词改成正确的"材质光影"和"功能玩法"
基于 v6（Miku 皮肤 + 细手臂）
"""
import zipfile, os

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
OUT_APK = os.path.join(MC_RE, 'patched_v14', 'Minecraft-unsigned.apk')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)
zin = zipfile.ZipFile(SRC_APK, 'r')

html = zin.read('assets/web/index.html').decode('utf-8')

# 回到 v7 的逻辑：前缀匹配 + 找 className 含 item 的父元素
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
          // 前缀匹配：文字以关键词开头
          if(t.indexOf(hideTexts[i]) === 0 && t.length < 20){
            // 往上找父元素，找 className 含 'item' 的列表项容器隐藏
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
print('注入后大小:', len(new_html))

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

replacements = {
    'assets/web/index.html': new_html.encode('utf-8'),
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}

v4_dex_path = os.path.join(MC_RE, 'patched_v3', 'classes.dex')
with open(v4_dex_path, 'rb') as f:
    v4_dex = f.read()

zout = zipfile.ZipFile(OUT_APK, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == 'classes.dex':
        data = v4_dex
    elif item.filename in replacements:
        data = replacements[item.filename]
    zout.writestr(item, data)

zin.close()
zout.close()
print('输出:', OUT_APK, os.path.getsize(OUT_APK), 'bytes')
