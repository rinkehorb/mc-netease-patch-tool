"""
v7 补丁：在 H5 index.html 注入 JS，自动隐藏"纹理材质"、"炫酷光影"、"玩法拓展"、"功能玩法"按钮
基于 v6（Miku 皮肤 + 细手臂）
"""
import zipfile, os

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
SRC_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')
OUT_APK = os.path.join(MC_RE, 'patched_v7', 'Minecraft-unsigned.apk')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'

os.makedirs(os.path.dirname(OUT_APK), exist_ok=True)

zin = zipfile.ZipFile(SRC_APK, 'r')

# 读原 index.html
html = zin.read('assets/web/index.html').decode('utf-8')

# 注入的隐藏按钮 JS
inject = '''
<script>
(function(){
  // 要隐藏的按钮关键词
  var hideTexts = ['纹理材质', '炫酷光影', '玩法拓展', '功能玩法'];
  function hideButtons(){
    try {
      // 遍历所有元素，找包含目标文字的按钮/卡片
      var all = document.querySelectorAll('div,span,a,button,li');
      all.forEach(function(el){
        var t = (el.textContent || '').trim();
        for(var i=0; i<hideTexts.length; i++){
          if(t === hideTexts[i] || t.indexOf(hideTexts[i]) === 0){
            // 找到按钮容器，往上找几层父元素隐藏
            var node = el;
            for(var j=0; j<5; j++){
              if(node.parentElement) node = node.parentElement;
              if(node.className && typeof node.className === 'string' && node.className.indexOf('item') >= 0){
                node.style.display = 'none';
                break;
              }
            }
            // 直接隐藏自己
            el.style.display = 'none';
            break;
          }
        }
      });
    } catch(e){ console.log('[HIDE] error: '+e); }
  }
  // 页面加载后定时检查（Vue 异步渲染）
  window.addEventListener('load', function(){
    setTimeout(hideButtons, 500);
    setTimeout(hideButtons, 1500);
    setTimeout(hideButtons, 3000);
    // 监听 DOM 变化
    var obs = new MutationObserver(function(){ hideButtons(); });
    obs.observe(document.body, {childList: true, subtree: true});
  });
})();
</script>
'''

# 在 </body> 前注入
new_html = html.replace('</body>', inject + '</body>')
print('注入后 index.html 大小:', len(new_html), '(原', len(html), ')')

# 准备替换的资源
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

# v4 classes.dex（含 v2/v3 Java 补丁）
v4_dex_path = os.path.join(MC_RE, 'patched_v3', 'classes.dex')
with open(v4_dex_path, 'rb') as f:
    v4_dex = f.read()

# 写新 APK
zout = zipfile.ZipFile(OUT_APK, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == 'classes.dex':
        data = v4_dex
        print('  替换: classes.dex')
    elif item.filename in replacements:
        data = replacements[item.filename]
        print('  替换:', item.filename)
    zout.writestr(item, data)

zin.close()
zout.close()

print()
print('输出:', OUT_APK)
print('大小:', os.path.getsize(OUT_APK))
