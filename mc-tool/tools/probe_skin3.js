/* =====================================================================
   MC 皮肤通道探针 v3 —— 由 MCPatchTool 注入到 assets/web/index.html
   =====================================================================
   v2 的收获与教训：
     ✅ 回调写法用 window.ComPyCallback.addToTagData([ok, bad]) 是通的（v1 覆盖 resolve
        完全收不到，v2 立刻有日志）。
     ❌ use_instance 被我搞反了：压缩 JS 里 `!1` 是 false、`!0` 是 true，
        我把 `!1` 当成"1=true"传了 true，于是 setting 模块报
        "Can not find get_raw_skins_path in setting"。
        （对照：探针文档里 decompress_map 传的就是 false，而它在我表里正是 `!1`。）
     💡 init_skin_list 找到了，但"takes exactly 1 argument" → 它要一个参数。

   v3 要问清楚的：
     1) setting.get_raw_skins_path 到底返回哪个绝对路径（换皮肤要写进去的目录）
     2) resource_management.init_skin_list 要的那个参数是什么形状
     3) 顺手用一个已知能用的函数（get_sorted_world_records）做对照，确认调用格式没写错

   只做读和问路径，不写任何文件。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCPROBE_SKIN3__) return;
  window.__MCPROBE_SKIN3__ = 1;

  var MAXLINES = 400;
  var lines = [];
  var elBox = null, elPre = null;

  function brief(x) {
    var s;
    try { s = (typeof x === 'string') ? x : JSON.stringify(x); } catch (e) { s = String(x); }
    if (s === undefined || s === null) s = String(s);
    return s.length > 260 ? s.slice(0, 260) + ' …(' + s.length + ')' : s;
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
    return new Promise(function (resolve, reject) {
      var settled = false;
      function ok(d) { if (!settled) { settled = true; add('OK  ', tagline + ' → ' + brief(d)); resolve(d); } }
      function bad(e) { if (!settled) { settled = true; add('FAIL', tagline + ' → ' + brief(e)); reject(e); } }
      var tagline = module + '.' + func + (useInstance ? '(inst)' : '(noInst)') + ' args=' + brief(args);

      var tag = null;
      try {
        var cc = window.ComPyCallback;
        if (cc && typeof cc.addToTagData === 'function') tag = cc.addToTagData([ok, bad]);
      } catch (e) { add('WARN', 'addToTagData: ' + brief(e)); }
      if (tag === null || tag === undefined) tag = (Math.random() * 4294967296) >>> 0;

      try {
        add('SEND', tagline + '  tag=' + tag);
        window.mc.sendMessage('json:' + JSON.stringify({
          module_name: module, func_name: func, use_instance: !!useInstance,
          args: args || [], tag: tag,
          return_callback: 'ComPyCallback.resolve', exception_callback: 'ComPyCallback.reject'
        }));
      } catch (e) { bad('sendMessage: ' + brief(e)); }
      setTimeout(function () { if (!settled) { settled = true; add('TIMEOUT', tagline); reject(new Error('timeout')); } }, 8000);
    });
  }

  function probeOnce(round) {
    add('----', '第 ' + round + ' 轮 ----');
    var q = Promise.resolve();

    // 对照：已知能用（表里 `!0` = true）
    q = q.then(function () { return call('resource_management', true, 'get_sorted_world_records', []).catch(function () {}); });
    q = q.then(function () { return call('resource_management', false, 'get_sorted_world_records', []).catch(function () {}); });

    // 重点：setting 的两个写法都试
    ['get_raw_skins_path', 'get_minecraftWorlds_path', 'get_resource_packs_path'].forEach(function (fn) {
      q = q.then(function () { return call('setting', false, fn, []).catch(function () {}); });
      q = q.then(function () { return call('setting', true, fn, []).catch(function () {}); });
    });

    // init_skin_list 需要 1 个参数 —— 试几种形状
    var tries = [[], [''], [[]], ['[]'], [{}], ['{}'], ['skinpacks/Base']];
    tries.forEach(function (a) {
      q = q.then(function () { return call('resource_management', false, 'init_skin_list', a).catch(function () {}); });
    });

    return q.then(function () { add('DONE', '第 ' + round + ' 轮结束'); });
  }

  function boot() {
    if (!ensurePanel()) { setTimeout(boot, 300); return; }
    add('BOOT', 'MC 皮肤通道探针 v3');
    add('ENV ', 'mc=' + (typeof window.mc) + '  ComPyCallback=' + (typeof window.ComPyCallback));
    var n = 0;
    (function loop() {
      n++;
      if (n > 2) return;
      probeOnce(n);
      setTimeout(loop, 22000);
    })();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
