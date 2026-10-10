/* =====================================================================
   MC 皮肤通道探针 v5 —— 要完整路径 + 试探读取接口
   =====================================================================
   v4 拿到了三个路径，但被面板右边缘截断了（只看到 .../com.netease.mc.）。
   v5 改成【每段一行】打印，保证完整可读。

   同时试一下 resource_management.get_local_image_by_item_id(itemId)：
     H5 里它是这么用的 ——
        console.log("load skin from local disk files")
        sendMessageToPython("resource_management", false,
                            "get_local_image_by_item_id", [itemId])
        → addNewModelBase64(结果)          // 返回 base64 图片
     说明它能把【本地磁盘上的皮肤图】读出来。如果传对 item_id 能拿到 base64，
     就证明这条路能读、也就能读出来——配合 decompress_map 写、init_skin_list 注册，
     理论上可以不用 root、不改 APK 换皮肤。

   大字符串只打印长度（base64 图会很长），避免把面板刷爆。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_SKIN5__) return;
  window.__MCPROBE_SKIN5__ = 1;

  var lines = [], elBox = null, elPre = null;

  function fmt(v) {
    var s;
    try { s = (typeof v === 'string') ? v : JSON.stringify(v); } catch (e) { s = String(v); }
    if (s === undefined || s === null) s = String(s);
    if (s.length > 90) return '<' + s.length + ' 字节> ' + s.slice(0, 60) + ' …';
    return s;
  }
  function add(k, t) {
    lines.push('[' + k + '] ' + t);
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = 0; }
  }
  function addPath(label, p) {
    add('PATH', label);
    String(p).split('/').forEach(function (seg, i) {
      add('    ', (i === 0 ? '' : '/') + seg);
    });
  }
  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:62%;z-index:2147483647;' +
      'background:#001a12;color:#7dffb0;font:11px/1.3 monospace;padding:6px;box-sizing:border-box;' +
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
      function fin(k, v) { if (!done) { done = true; resolve(v); return k; } }
      var tag = null, res = null;
      try {
        var cc = window.ComPyCallback;
        if (cc && typeof cc.addToTagData === 'function') {
          tag = cc.addToTagData([
            function (d) { var k = fin('OK  ', d); if (k) add(k, func + ' → ' + fmt(d)); },
            function (e) { var k = fin('FAIL', e); if (k) add(k, func + ' → ' + fmt(e)); }
          ]);
        }
      } catch (e) { add('WARN', 'addToTagData: ' + fmt(e)); }
      if (tag === null || tag === undefined) tag = (Math.random() * 4294967296) >>> 0;
      try {
        window.mc.sendMessage('json:' + JSON.stringify({
          module_name: module, func_name: func, use_instance: !!useInstance, args: args || [],
          tag: tag, return_callback: 'ComPyCallback.resolve', exception_callback: 'ComPyCallback.reject'
        }));
      } catch (e) { add('FAIL', func + ' sendMessage: ' + fmt(e)); }
      setTimeout(function () { var k = fin('TIMEOUT', null); if (k) add(k, func + ' 8 秒无回调'); }, 8000);
    });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', '皮肤通道探针 v5：完整路径 + 试读接口');
    var q = Promise.resolve();

    // ① 三个路径，每段一行
    [['get_raw_skins_path', '★ RAW SKINS'],
     ['get_minecraftWorlds_path', 'WORLDS'],
     ['get_resource_packs_path', 'RESOURCE PACKS']].forEach(function (p) {
      q = q.then(function () { return call('setting', false, p[0], []); })
           .then(function (v) { if (typeof v === 'string') addPath(p[1], v); });
    });

    // ② 试探读取接口：几种可能的 item_id 形状
    ['skinpacks/Base/alex', 'skinpacks/Base/steve', 'alex', 'steve', '0', ''].forEach(function (id) {
      q = q.then(function () { return call('resource_management', false, 'get_local_image_by_item_id', [id]); });
    });

    q.then(function () { add('DONE', '跑完了'); });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
