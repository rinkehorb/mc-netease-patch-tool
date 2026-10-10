/* =====================================================================
   MC 皮肤通道探针 v2 —— 由 MCPatchTool 注入到 assets/web/index.html
   =====================================================================
   目的（2026-10-10）：
     从 H5 的桥接调用表里发现游戏有【皮肤列表 + 皮肤目录】机制：
         setting.get_raw_skins_path          "原始皮肤"目录
         resource_management.init_skin_list  初始化皮肤列表
     而 h5adaptor.decompress_map(源zip, 目录, true) 能往【任意目录】写文件。
     串起来就可能是「不改 APK、不用 root 换皮肤」。第一步先问出那个绝对路径。

   v1 的教训：覆盖 window.ComPyCallback.resolve/reject 收不到回调（一行日志都没有）。
   官方写法是 ComPyCallback.addToTagData([resolve, reject]) —— 由原生按 tag 回调，
   所以 v2 用它，并在 resolve/reject 里各自打日志。

   自查：还先把 window.mc / window.ComPyCallback 的类型和键名打出来，
   这样一来"桥接到底存不存在"一眼可见（省得又白跑一趟）。

   本探针只做「读」和「问路径」，不写任何文件。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_SKIN2__) return;
  window.__MCPROBE_SKIN2__ = 1;

  var MAXLINES = 300;
  var lines = [];
  var elBox = null, elPre = null;

  function brief(x) {
    var s;
    try { s = (typeof x === 'string') ? x : JSON.stringify(x); } catch (e) { s = String(x); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 300 ? s.slice(0, 300) + ' …(' + s.length + ')' : s;
  }

  function add(kind, text) {
    lines.push('[' + kind + '] ' + text);
    if (lines.length > MAXLINES) lines.splice(0, lines.length - MAXLINES);
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = elPre.scrollHeight; }
  }

  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:45%;z-index:2147483647;' +
      'background:#001a12;color:#7dffb0;font:11px/1.35 monospace;padding:6px;box-sizing:border-box;' +
      'border-top:2px solid #0f0;';
    elPre = document.createElement('pre');
    elPre.style.cssText = 'margin:0;height:100%;overflow:auto;white-space:pre-wrap;';
    elBox.appendChild(elPre);
    document.body.appendChild(elBox);
    return true;
  }

  /* ---------------- 桥接（官方写法：addToTagData） ---------------- */
  function call(module, useInstance, func, args) {
    return new Promise(function (resolve, reject) {
      var settled = false;
      function ok(d) { if (!settled) { settled = true; add('OK  ', func + ' → ' + brief(d)); resolve(d); } }
      function bad(e) { if (!settled) { settled = true; add('FAIL', func + ' → ' + brief(e)); reject(e); } }

      var tag = null;
      try {
        var cc = window.ComPyCallback;
        if (cc && typeof cc.addToTagData === 'function') tag = cc.addToTagData([ok, bad]);
      } catch (e) {
        add('WARN', 'addToTagData 失败: ' + brief(e));
      }
      if (tag === null || tag === undefined) tag = (Math.random() * 4294967296) >>> 0;

      var payload = {
        module_name: module,
        func_name: func,
        use_instance: !!useInstance,
        args: args || [],
        tag: tag,
        return_callback: 'ComPyCallback.resolve',
        exception_callback: 'ComPyCallback.reject'
      };
      try {
        add('SEND', module + '.' + func + '  tag=' + tag);
        window.mc.sendMessage('json:' + JSON.stringify(payload));
      } catch (e) {
        bad('sendMessage: ' + brief(e));
      }
      // 兜底：8 秒没回调就报出来，免得"静悄悄什么都没发生"
      setTimeout(function () { if (!settled) { settled = true; add('TIMEOUT', func + ' 8 秒无回调'); reject(new Error('timeout')); } }, 8000);
    });
  }

  /* ---------------- 探测流程 ---------------- */
  var SETTING_CALLS = ['get_raw_skins_path', 'get_minecraftWorlds_path', 'get_resource_packs_path'];

  function probeOnce(round) {
    add('----', '第 ' + round + ' 轮 ----');
    var p = Promise.resolve();
    SETTING_CALLS.forEach(function (fn) {
      p = p.then(function () {
        return call('setting', true, fn, []).catch(function () {});
      });
    });
    return p.then(function () {
      return call('resource_management', true, 'init_skin_list', []).catch(function () {});
    }).then(function () {
      add('DONE', '第 ' + round + ' 轮结束');
    });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', 'MC 皮肤通道探针 v2');
    add('ENV ', 'mc=' + (typeof window.mc) +
        '  ComPyCallback=' + (typeof window.ComPyCallback));
    try {
      if (window.ComPyCallback) {
        add('ENV ', 'ComPyCallback 键 = ' + Object.keys(window.ComPyCallback).join(','));
      }
      if (window.mc) {
        add('ENV ', 'mc 键 = ' + Object.keys(window.mc).join(','));
      }
    } catch (e) { add('ENV ', '列键失败 ' + brief(e)); }

    var n = 0;
    (function loop() {
      n++;
      if (n > 3) return;
      probeOnce(n);
      setTimeout(loop, 9000);
    })();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
