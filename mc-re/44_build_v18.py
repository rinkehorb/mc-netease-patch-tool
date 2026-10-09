"""
v18 修复：回到 v6 的打包方式（原 APK 直接替换文件，不动 manifest）
dex 用 v17c 的（带全屏 flags + 刘海屏运行时设置）
其他资源（alex.png、lang、index.html）也替换
"""
import zipfile, os, subprocess

MC_RE = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re'
ORIG_APK = os.path.join(MC_RE, 'original', 'Minecraft.apk')  # 原始 APK
V17C_DEX = os.path.join(MC_RE, 'patched_v17', 'classes.dex')  # v17c 的 dex
MIKU_PNG = r'C:\Users\Administrator\DoubaoWork\chats\2026-10-08\new-chat\Miku.png'
FINAL_APK = os.path.join(MC_RE, 'patched_v18', 'Minecraft-final-unsigned.apk')
JAVA = os.path.join(MC_RE, 'tools', 'jre', 'jdk-17.0.20.1+1-jre', 'bin', 'java.exe')
SIGNER = os.path.join(MC_RE, 'tools', 'uber-apk-signer.jar')
OUT_DIR = os.path.join(MC_RE, 'patched_v18', 'signed')
KEYSTORE = os.path.join(MC_RE, 'tools', 'debug.keystore')
TMP_DIR = os.path.join(MC_RE, 'JtmpDir')

os.makedirs(os.path.dirname(FINAL_APK), exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# 读所有要替换的文件
with open(V17C_DEX, 'rb') as f:
    v17c_dex = f.read()
print('v17c dex 大小:', len(v17c_dex))

with open(MIKU_PNG, 'rb') as f:
    miku_data = f.read()

orig = zipfile.ZipFile(ORIG_APK, 'r')

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
    'classes.dex': v17c_dex,
    'assets/web/index.html': new_html,
    'assets/resource_packs/vanilla/texts/zh_CN.lang': zh_cn,
    'assets/resource_packs/vanilla/texts/en_US.lang': en_us,
    'assets/resource_packs/skins/skinpacks/Base/alex.png': miku_data,
    'assets/resource_packs/skins/skinpacks/Base/alex_dev.png': miku_data,
}
print('替换文件数:', len(replacements))

# 基于原始 APK，只替换指定文件（不动 manifest！）
zin = zipfile.ZipFile(ORIG_APK, 'r')
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

print('替换的文件:')
for r in replaced:
    print('  ', r)
print()
print('最终 APK:', FINAL_APK)
print('大小:', os.path.getsize(FINAL_APK))

# 签名
cmd = [JAVA, f'-Djava.io.tmpdir={TMP_DIR}', '-jar', SIGNER,
       '-a', FINAL_APK, '-o', OUT_DIR,
       '--allowResign', '--skipZipAlign',
       '--ks', KEYSTORE, '--ksAlias', 'androiddebugkey',
       '--ksPass', 'android', '--ksKeyPass', 'android']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(r.stdout[-600:])
print('签名返回码:', r.returncode)
