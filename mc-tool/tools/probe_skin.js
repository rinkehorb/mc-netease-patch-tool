/* =====================================================================
   MC 皮肤通道探针 —— 由 MCPatchTool 注入到 assets/web/index.html
   =====================================================================
   目的（2026-10-10）：
     从 H5 的桥接调用表里发现游戏有一套【皮肤列表 + 皮肤目录】机制：
         setting.get_raw_skins_path              "原始皮肤"目录
         resource_management.init_skin_list      初始化皮肤列表
         resource_management.get_local_image_by_item_id
     而 h5adaptor.decompress_map(源zip, 目标目录, true) 能往【任意目录】写文件。

     如果这三样能串起来 → 就能做到「不改 APK、不用 root 换皮肤」。
     第一步必须先问出 get_raw_skins_path 返回的绝对路径。

   它怎么工作：
     直接走 window.mc.sendMessage 桥接（和导入器同一套写法），
     依次调用若干接口，把返回值和异常原样打在屏幕下半部分。
     **自动运行**，不需要点任何按钮 —— 启动游戏后看一眼/截个图即可。

   注意：本探针只做「读」和「问路径」，不写任何文件。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_SKIN__) return;
  window.__MCPROBE_SKIN__ = 1;

  var MAXLINES = 200;
  var lines = [];
  var waiters = {};
  var elBox = null, elPre = null;

  /* ---------------- 桥接（与 mc-import.js 相同写法） ---------------- */
  function allocTag(res, rej) {
    try {
      var cc = window.ComPyCallback;
      if (cc && typeof cc.addToTagData === 'function') {
        var t = cc.addToTagData([res, rej]);
        if (t !== undefined && t !== null) return t;
      }
    } catch (e) {}
    return Math.floor(Math.random() * 4294967296);
  }

  function call(module, useInstance, func, args) {
    return new Promise(function (resolve, reject) {
      var tag = Math.floor(Math.random() * 4294967296);
      waiters[tag] = { resolve: resolve, reject: reject, func: func };
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
        window.mc.sendMessage('json:' + JSON.stringify(payload));
      } catch (e) {
        delete waiters[tag];
        reject(new Error('sendMessage 失败: ' + e));
      }
    });
  }

  function installCallbacks() {
    var cc = window.ComPyCallback;
    if (!cc || cc.__probeHooked) return;
    var realResolve = cc.resolve, realReject = cc.reject;
    cc.resolve = function (tag, data) {
      if (waiters[tag]) {
        var w = waiters[tag]; delete waiters[tag];
        add('OK  ', w.func + ' → ' + brief(data));
        w.resolve(data);
      }
      if (realResolve) try { return realResolve.apply(cc, arguments); } catch (e) {}
    };
    cc.reject = function (tag, err) {
      if (waiters[tag]) {
        var w = waiters[tag]; delete waiters[tag];
        add('FAIL', w.func + ' → ' + brief(err));
        w.reject(err);
      }
      if (realReject) try { return realReject.apply(cc, arguments); } catch (e) {}
    };
    cc.__probeHooked = 1;
  }

  /* ---------------- 界面 ---------------- */
  function brief(x) {
    var s;
    try { s = (typeof x === 'string') ? x : JSON.stringify(x); } catch (e) { s = String(x); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 400 ? s.slice(0, 400) + ' …(共 ' + s.length + ')' : s;
  }

  function add(kind, text) {
    lines.push('[' + kind + '] ' + text);
    if (lines.length > MAXLINES) lines.splice(0, lines.length - MAXLINES);
    paint();
  }

  function paint() {
    if (elPre) { elPre.textContent = lines.join('\n'); elPre.scrollTop = elPre.scrollHeight; }
  }

  function ensurePanel() {
    if (elBox) return true;
    if (!document.body) return false;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:0;right:0;bottom:0;height:42%;z-index:2147483647;' +
      'background:#001a12;color:#7dffb0;font:11px/1.35 monospace;padding:6px;box-sizing:border-box;' +
      'border-top:2px solid #0f0;';
    elPre = document.createElement('pre');
    elPre.style.cssText = 'margin:0;height:100%;overflow:auto;white-space:pre-wrap;';
    elBox.appendChild(elPre);
    document.body.appendChild(elBox);
    paint();
    return true;
  }

  /* ---------------- 探测流程 ---------------- */
  var SETTING_CALLS = [
    'get_raw_skins_path',
    'get_minecraftWorlds_path',
    'get_resource_packs_path'
  ];

  function probeOnce(tag) {
    installCallbacks();
    var p = Promise.resolve();
    SETTING_CALLS.forEach(function (fn) {
      p = p.then(function () {
        return call('setting', true, fn, []).catch(function (e) {
          add('ERR ', fn + ' → ' + brief(e && e.message ? e.message : e));
        });
      });
    });
    p = p.then(function () {
      return call('resource_management', true, 'init_skin_list', []).catch(function (e) {
        add('ERR ', 'init_skin_list → ' + brief(e && e.message ? e.message : e));
      });
    });
    p = p.then(function () {
      add('DONE', '第 ' + tag + ' 轮探测结束');
    });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', 'MC 皮肤通道探针启动，自动开跑');
    var n = 0;
    (function loop() {
      n++;
      if (n > 4) return;
      probeOnce(n);
      setTimeout(loop, 6000);
    })();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
