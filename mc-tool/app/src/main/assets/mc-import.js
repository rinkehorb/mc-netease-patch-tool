/* =====================================================================
   MC 世界导入器 —— 由 MCPatchTool 注入到 assets/web/index.html
   =====================================================================
   为什么需要它：
     网易版的世界列表读的是「世界记录」（storge/stream/resource_management/
     world_records/<level_id>.json），不是扫目录。所以基岩版自己的导入器把世界
     装进 minecraftWorlds/ 之后，列表永远看不到它。

   它怎么做到不用 root：
     H5 能调的原生接口里，h5adaptor.decompress_map(源zip, 目标目录, true)
     的「目标目录」是任意的 —— 于是把「世界记录 JSON」也打成一个 zip，
     就能直接解压进记录目录。

   两个必须尊重的特性：
     1) decompress_map 会把包内目录结构【完全压平】→ 所以按顶层目录分组，
        每组一个包，目标目录直接指向对应子目录（db.zip → <世界>/db）。
     2) decompress_map 成功后会【消耗掉源 zip】→ 于是"已导入的槽位"天然消失，
        不需要任何状态记录，下次点击自动落到下一个槽位。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCIMPORT__) return;
  window.__MCIMPORT__ = 1;

  var SLOTS = 9;                       // 与工具体的 SLOTS 一致
  var DIR = '/sdcard/Download/';       // 工具体把包写在这里
  // 世界内部的顶层目录分组（root 表示世界根目录）
  var SUFFIXES = ['root', 'db', 'players', 'resource_packs', 'behavior_packs', 'structures'];
  var MAXLINES = 40;

  var lines = [];
  var waiters = {};
  var elBox = null, elLog = null, elBtn = null;

  /* ---------------- 桥接 ---------------- */
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

  function hookCC() {
    var cc = window.ComPyCallback;
    if (!cc || cc.__mcimport) return !!cc;
    try {
      var or = cc.resolve, oe = cc.reject;
      cc.resolve = function (json, tag) {
        var s = (typeof json === 'string') ? json : JSON.stringify(json);
        if (waiters[tag]) { var w = waiters[tag]; delete waiters[tag]; try { w.res(s); } catch (e) {} return; }
        return or ? or.apply(this, arguments) : undefined;
      };
      cc.reject = function (err, tag) {
        var s = (typeof err === 'string') ? err : JSON.stringify(err);
        if (waiters[tag]) { var w = waiters[tag]; delete waiters[tag]; try { w.rej(s); } catch (e) {} return; }
        return oe ? oe.apply(this, arguments) : undefined;
      };
      cc.__mcimport = 1;
    } catch (e) {}
    return true;
  }
  try {
    var cur = window.ComPyCallback;
    Object.defineProperty(window, 'ComPyCallback', {
      configurable: true,
      get: function () { return cur; },
      set: function (v) { cur = v; hookCC(); }
    });
  } catch (e) {}

  function ret(s) {
    if (typeof s !== 'string') return s;
    try { var o = JSON.parse(s); return (o && 'return' in o) ? o.return : o; }
    catch (e) { return s; }
  }

  function call(mod, inst, fn, args) {
    return new Promise(function (resolve, reject) {
      if (!window.mc || typeof window.mc.sendMessage !== 'function') {
        reject(new Error('window.mc.sendMessage 不可用')); return;
      }
      var done = false;
      var to = setTimeout(function () { if (!done) { done = true; delete waiters[tag];
        reject(new Error('超时')); } }, 20000);
      var tag = allocTag(
        function (s) { if (done) return; done = true; clearTimeout(to); resolve(ret(s)); },
        function (e) { if (done) return; done = true; clearTimeout(to);
          reject(new Error(typeof e === 'string' ? e : JSON.stringify(e))); }
      );
      waiters[tag] = {
        res: function (s) { if (done) return; done = true; clearTimeout(to); resolve(ret(s)); },
        rej: function (e) { if (done) return; done = true; clearTimeout(to);
          reject(new Error(typeof e === 'string' ? e : JSON.stringify(e))); }
      };
      window.mc.sendMessage('json:' + JSON.stringify({
        module_name: mod, func_name: fn, use_instance: !!inst, args: args || [],
        tag: tag,
        return_callback: 'ComPyCallback.resolve',
        exception_callback: 'ComPyCallback.reject'
      }));
    });
  }

  /* ---------------- 日志 ---------------- */
  function log(s, bad) {
    lines.push(s);
    if (lines.length > MAXLINES) lines.shift();
    if (elLog) {
      elLog.textContent = lines.join('\n');
      elLog.scrollTop = elLog.scrollHeight;
      elLog.style.color = bad ? '#ff8080' : '#8f8';
    }
  }

  /* ---------------- 导入 ---------------- */
  function isMissing(e) {
    return /Errno 2|No such file/i.test(String(e && e.message ? e.message : e));
  }

  // 尝试解压一个包；返回 true=成功，false=这个包不存在（正常跳过）
  function tryPart(part, dest) {
    return call('h5adaptor', false, 'decompress_map', [DIR + part, dest, true])
      .then(function () { return true; }, function (e) {
        if (isMissing(e)) return false;
        throw e;
      });
  }

  function importSlot(slot) {
    var id = 'mcw' + slot;
    var worldsPath = null, recordsPath = null;
    return call('setting', false, 'get_minecraftWorlds_path').then(function (w) {
      worldsPath = w;
      if (!worldsPath || typeof worldsPath !== 'string') throw new Error('拿不到世界目录');
      recordsPath = worldsPath.replace(/\/minecraftWorlds\/?$/,
        '/storge/stream/resource_management/world_records');
      var worldDir = worldsPath + '/' + id;
      // 先探 root：不存在就说明这个槽位没准备（或已经被导入过、源包被消耗掉了）
      return tryPart('mcweb_' + slot + '_root.zip', worldDir).then(function (ok) {
        if (!ok) return null;
        log('槽位 ' + slot + '：世界文件已解压');
        var chain = Promise.resolve();
        SUFFIXES.forEach(function (suf) {
          if (suf === 'root') return;
          chain = chain.then(function () {
            return tryPart('mcweb_' + slot + '_' + suf + '.zip', worldDir + '/' + suf)
              .then(function (got) { if (got) log('  ' + suf + '/ 已解压'); });
          });
        });
        return chain.then(function () {
          return call('h5adaptor', false, 'decompress_map',
            [DIR + 'mcweb_' + slot + '_record.zip', recordsPath, true]).then(function () {
              log('  ✅ 世界记录已写入');
              return id;
            });
        });
      });
    });
  }

  function makeStep(slot) {
    return function (doneId) {
      if (doneId) return doneId;                 // 已经成功过了，后面的槽位不用看
      return importSlot(slot).then(function (id) {
        if (id) log('槽位 ' + slot + ' 导入完成');
        return id;
      });
    };
  }

  function doImport() {
    if (elBtn.disabled) return;
    elBtn.disabled = true;
    elBtn.textContent = '导入中…';
    log('开始检查槽位 1…' + SLOTS);

    var chain = Promise.resolve(null);
    for (var k = 1; k <= SLOTS; k++) chain = chain.then(makeStep(k));
    chain.then(function (id) {
      if (id) {
        log('🎉 导入完成！请【完全退出游戏再重新打开】，世界就会出现在列表里');
        elBtn.textContent = '已导入 ✔';
        elBtn.style.background = '#2a6';
      } else {
        log('没有找到待导入的包。请先在工具里点「准备导入」。', true);
        elBtn.textContent = '导入世界';
        elBtn.disabled = false;
      }
    }).catch(function (e) {
      log('导入失败：' + (e && e.message ? e.message : e), true);
      elBtn.textContent = '导入世界';
      elBtn.disabled = false;
    });
  }

  /* ---------------- 界面 ---------------- */
  function ui() {
    if (elBox) return;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:2147483000;' +
      'font:12px/1.4 monospace;max-width:70vw;';

    elBtn = document.createElement('button');
    elBtn.textContent = '导入世界';
    elBtn.style.cssText = 'font:13px monospace;padding:5px 10px;border-radius:6px;' +
      'background:#3a7;color:#fff;border:1px solid #fff;opacity:0.85;';
    elBtn.onclick = function (ev) {
      ev.stopPropagation(); ev.preventDefault();
      if (elLog) elLog.style.display = 'block';
      doImport();
    };

    elLog = document.createElement('pre');
    elLog.style.cssText = 'display:none;margin:4px 0 0;padding:4px 6px;max-height:30vh;' +
      'overflow:auto;background:rgba(0,0,0,0.85);color:#8f8;white-space:pre-wrap;' +
      'word-break:break-all;border-radius:4px;font-size:11px;';

    // 注意顺序：日志放在按钮【上面】。
    // 这个盒子是 bottom:8px 锚定的，日志加在按钮下面的话会把按钮顶上去，
    // 用户第二次点就会点到日志上（真机实测踩过）。
    elBox.appendChild(elLog);
    elBox.appendChild(elBtn);
    (document.body || document.documentElement).appendChild(elBox);
  }

  function boot() {
    try {
      hookCC();
      ui();
    } catch (e) {}
  }
  var n = 0;
  var iv = setInterval(function () {
    n++;
    hookCC();
    if ((window.ComPyCallback && window.ComPyCallback.__mcimport) || n > 100) {
      clearInterval(iv);
      boot();
    }
  }, 200);
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(boot, 300);
  } else {
    window.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 300); });
  }
})();
