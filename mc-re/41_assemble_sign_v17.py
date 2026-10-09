"""v17 修复后重新组装 + 签名"""
import zipfile, os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
BASE_APK = os.path.join(MC_RE, 'patched_v16', 'Minecraft-unsigned.apk')
V17_DEX = os.path.join(MC_RE, 'patched_v17', 'classes.dex')
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'
FINAL_APK = os.path.join(MC_RE, 'patched_v17', 'Minecraft-final-unsigned.apk')
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SIGNER = os.path.join(MC_RE, 'tools', 'uber-apk-signer.jar')
OUT_DIR = os.path.join(MC_RE, 'patched_v17', 'signed')
KEYSTORE = os.path.join(MC_RE, 'tools', 'debug.keystore')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

with open(V17_DEX, 'rb') as f:
    v17_dex = f.read()
with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()

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

replacements = {
    'classes.dex': v17_dex,
    'assets/web/index.html': new_html,
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}

if os.path.exists(FINAL_APK):
    os.remove(FINAL_APK)
zin = zipfile.ZipFile(BASE_APK, 'r')
zout = zipfile.ZipFile(FINAL_APK, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename in replacements:
        data = replacements[item.filename]
    zout.writestr(item, data)
zin.close()
zout.close()
print('组装完成:', FINAL_APK, os.path.getsize(FINAL_APK))

# 签名
os.makedirs(OUT_DIR, exist_ok=True)
cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', SIGNER,
       '-a', FINAL_APK, '-o', OUT_DIR,
       '--allowResign', '--skipZipAlign',
       '--ks', KEYSTORE, '--ksAlias', 'androiddebugkey',
       '--ksPass', 'android', '--ksKeyPass', 'android']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(r.stdout[-600:])
print('签名返回码:', r.returncode)
