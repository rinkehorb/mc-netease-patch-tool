/* =====================================================================
   MC 手臂切换探针（vivo / 无 root 版）—— 验证「不 root 也能换粗细」
   =====================================================================
   背景：一加上（有 root）已验证 —— H5 用
       h5adaptor.decompress_map(源zip, '/data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe', true)
   能把 options.txt 覆盖掉，游戏下次启动就读到新的手臂体型。
   现在要在**没有 root 的 vivo** 上验证同一件事 —— 区别只有一个：
     源 zip 不能靠 root 塞进游戏私有目录，必须放在游戏「按路径读得到」的地方。

   而 Android 11+ 规定：别的 App 创建的**非媒体文件**任何位置、任何权限都读不到；
   **媒体文件**（.png 等）才读得到。所以工具一直把包写成 .png 走 MediaStore。
   本探针就把几个候选位置依次试一遍，看哪个真的能被游戏读到 —— 结论直接打在屏幕上。

   为了和探针 v6 一样"改完能看出来"，源 zip 里的 options.txt 写的是
       game_skintypefull:Standard_Steve   （粗手臂 4px）
   如果这次成功，游戏里手臂会从细变粗。

   ⚠️ 测试阶段先只试「读得到读不到」：只要某个候选返回 OK，就说明这条路在无 root 下通。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_ARMV__) return;
  window.__MCPROBE_ARMV__ = 1;

  var DEST = '/data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe';

  var CANDS = [
    '/sdcard/Download/arm_switch.png',
    '/storage/emulated/0/Download/arm_switch.png',
    '/sdcard/Android/media/com.mctool.mcpatch/arm_switch.png',
    '/sdcard/Download/mcweb_1_root.png',
    '/sdcard/Download/arm_switch.zip',
    '/sdcard/Android/media/com.mctool.mcpatch/arm_switch.zip'
  ];

  var lines = [], elBox = null, elPre = null;

  function fmt(v) {
    var s;
    try { s = (typeof v === 'string') ? v : JSON.stringify(v); } catch (e) { s = String(v); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 160 ? s.slice(0, 160) + ' …' : s;
  }
  function add(k, t) {
    lines.push('[' + k + '] ' + t);
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = 0; }
  }
  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:46%;z-index:2147483647;' +
      'background:#001a12;color:#7dffb0;font:11px/1.32 monospace;padding:6px;box-sizing:border-box;' +
      'border-top:2px solid #0f0;';
    elPre = document.createElement('pre');
    elPre.style.cssText = 'margin:0;height:100%;overflow:auto;white-space:pre-wrap;';
    elBox.appendChild(elPre);
    document.body.appendChild(elBox);
    return true;
  }

  function call(module, useInstance, func, args) {
    return new Promise(function (resolve) {
      var done = false;
      function fin(k, v) { if (!done) { done = true; add(k, func + ' → ' + fmt(v)); resolve({ ok: k === 'OK  ', val: v }); } }
      var tag = null;
      try {
        var cc = window.ComPyCallback;
        if (cc && typeof cc.addToTagData === 'function') {
          tag = cc.addToTagData([function (d) { fin('OK  ', d); }, function (e) { fin('FAIL', e); }]);
        }
      } catch (e) { add('WARN', 'addToTagData: ' + fmt(e)); }
      if (tag === null || tag === undefined) tag = (Math.random() * 4294967296) >>> 0;
      try {
        window.mc.sendMessage('json:' + JSON.stringify({
          module_name: module, func_name: func, use_instance: !!useInstance, args: args || [],
          tag: tag, return_callback: 'ComPyCallback.resolve', exception_callback: 'ComPyCallback.reject'
        }));
      } catch (e) { fin('FAIL', 'sendMessage: ' + fmt(e)); }
      setTimeout(function () { fin('TIMEOUT', '10 秒无回调'); }, 10000);
    });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', '手臂切换探针（无 root 版）');
    add('INFO', '目标: ' + DEST);
    var q = Promise.resolve();
    CANDS.forEach(function (src) {
      q = q.then(function () {
        add('----', '试源: ' + src);
        return call('h5adaptor', false, 'decompress_map', [src, DEST, true]).then(function (r) {
          if (r.ok) add('★★★', '这个源可用: ' + src);
        });
      });
    });
    q.then(function () { add('DONE', '全部试完（★ 那行就是可用的源）'); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
