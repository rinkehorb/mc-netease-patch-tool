/* =====================================================================
   MC 手臂切换探针 v6 —— 验证「不用 root 换手臂粗细」这条路
   =====================================================================
   思路：
     手臂体型存在 /data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe/options.txt
     的 game_skintypefull 这一行（已实测：Standard_Alex=3px / Standard_Steve=4px）。
     那个文件在游戏自己的私有目录里 —— 游戏自己能写，所以 H5 也能写。
     h5adaptor.decompress_map(源zip, 目标目录, true) 是以**游戏身份**解压的，
     于是把一份改好的 options.txt 打成一个 zip，就能让游戏自己覆盖自己。

     本条路线的意义：**不需要 root、不需要卸载重装** 就能切 3px/4px。
     代价：H5 没有"读文本文件"的接口，只能整份覆盖 —— 用户其他设置（画质/控制）
           会回到这份 options.txt 里的值。

   本探针做的事：
     调用 decompress_map(ARMZIP, MINECRAFT_PE_DIR, true)，然后报告结果。
     ARMZIP 由外部用 root 预先放进游戏目录（测试阶段图省事；
     正式用法可以走工具那套 MediaStore .png 通道，不需要 root）。

   结果怎么看：
     探针会把 OK/FAIL 打在屏幕上；同时我可以用 root 直接查 options.txt 有没有变。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_ARM__) return;
  window.__MCPROBE_ARM__ = 1;

  var DATA = '/data/data/com.netease.mc.qihoo';
  var PE_DIR = DATA + '/games/com.netease/minecraftpe';
  var ARMZIP = DATA + '/games/com.netease/arm_switch.zip';

  var lines = [], elBox = null, elPre = null;

  function fmt(v) {
    var s;
    try { s = (typeof v === 'string') ? v : JSON.stringify(v); } catch (e) { s = String(v); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 90 ? '<' + s.length + ' 字节> ' + s.slice(0, 60) + ' …' : s;
  }
  function add(k, t) {
    lines.push('[' + k + '] ' + t);
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = 0; }
  }
  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:40%;z-index:2147483647;' +
      'background:#001a12;color:#7dffb0;font:12px/1.4 monospace;padding:8px;box-sizing:border-box;' +
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
      function fin(k, v) { if (!done) { done = true; add(k, func + ' → ' + fmt(v)); resolve(v); } }
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
    add('BOOT', '手臂切换探针 v6');
    add('INFO', '源 zip: ' + ARMZIP);
    add('INFO', '目标  : ' + PE_DIR);
    add('----', '第 1 次：切到 3px（options.txt 里是 Standard_Alex）');
    call('h5adaptor', false, 'decompress_map', [ARMZIP, PE_DIR, true]).then(function () {
      add('----', '第 2 次：切回 4px（先等 zip 被换掉，3 秒后重试）');
      setTimeout(function () {
        call('h5adaptor', false, 'decompress_map', [ARMZIP, PE_DIR, true]);
      }, 3000);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
