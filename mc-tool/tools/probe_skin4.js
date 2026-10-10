/* =====================================================================
   MC 皮肤通道探针 v4 —— 只问路径，别的不做
   =====================================================================
   v3 已经确认：
     ✅ use_instance 必须传 false（压缩 JS 里 `!1` 才是真值对照）
     ✅ resource_management.init_skin_list 存在，传 1 个参数即调用成功（返回 null）

   v4 只问三件事，总共不到 10 行日志，保证一屏看完：
     setting.get_raw_skins_path        "原始皮肤"目录 ← 换皮肤要写进去的地方
     setting.get_minecraftWorlds_path  世界目录（做对照）
     setting.get_resource_packs_path   资源包目录（做对照）

   读到路径后就能用 root 去看那个目录里有什么，进而判断
   「decompress_map 写皮肤 + init_skin_list 刷新」这条路走不走得通。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_SKIN4__) return;
  window.__MCPROBE_SKIN4__ = 1;

  var lines = [], elBox = null, elPre = null;

  function brief(x) {
    var s;
    try { s = (typeof x === 'string') ? x : JSON.stringify(x); } catch (e) { s = String(x); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 220 ? s.slice(0, 220) + ' …(' + s.length + ')' : s;
  }
  function add(k, t) {
    lines.push('[' + k + '] ' + t);
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = 0; }  // 不自动滚到底，从头看
  }
  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:34%;z-index:2147483647;' +
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
      function fin(k, v) { if (!done) { done = true; add(k, func + ' → ' + brief(v)); resolve(v); } }
      var tag = null;
      try {
        var cc = window.ComPyCallback;
        if (cc && typeof cc.addToTagData === 'function') {
          tag = cc.addToTagData([function (d) { fin('OK  ', d); }, function (e) { fin('FAIL', e); }]);
        }
      } catch (e) { add('WARN', 'addToTagData: ' + brief(e)); }
      if (tag === null || tag === undefined) tag = (Math.random() * 4294967296) >>> 0;
      try {
        window.mc.sendMessage('json:' + JSON.stringify({
          module_name: module, func_name: func, use_instance: !!useInstance, args: args || [],
          tag: tag, return_callback: 'ComPyCallback.resolve', exception_callback: 'ComPyCallback.reject'
        }));
      } catch (e) { fin('FAIL', 'sendMessage: ' + brief(e)); }
      setTimeout(function () { fin('TIMEOUT', '8 秒无回调'); }, 8000);
    });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', '皮肤通道探针 v4：只问路径');
    add('ENV ', 'mc=' + (typeof window.mc) + ' cc=' + (typeof window.ComPyCallback));
    var q = Promise.resolve();
    [['get_raw_skins_path', '★ 皮肤目录'],
     ['get_minecraftWorlds_path', '世界目录'],
     ['get_resource_packs_path', '资源包目录']].forEach(function (p) {
      q = q.then(function () {
        add('----', p[1]);
        return call('setting', false, p[0], []);
      });
    });
    q.then(function () { add('DONE', '问完了'); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
