/* =====================================================================
   MC 世界导入器 —— 由 MCPatchTool 注入到 assets/web/index.html
   =====================================================================
   为什么需要它：
     网易版的世界列表读的是「世界记录」（storge/stream/resource_management/
     world_records/<level_id>.json），不是扫目录。所以基岩版自己的导入器把世界
     装进 minecraftWorlds/ 之后，列表永远看不到它。

   它怎么做到不用 root：
     H5 能调的原生接口里，h5adaptor.decompress_map(源zip, 目标目录, true)
     的「目标目录」是任意的 —— 于是把「世界记录 JSON」也打成一个包，
     就能直接解压进记录目录。

   三个必须尊重的特性：
     1) decompress_map 会把包内目录结构【完全压平】→ 所以按顶层目录分组，
        每组一个包，目标目录直接指向对应子目录（db.zip → <世界>/db）。
     2) decompress_map 成功后会【消耗掉源 zip】→ 于是"已导入的槽位"天然消失，
        不需要任何状态记录，下次点击自动落到下一个槽位。
     3) 源 zip 必须【别的 App 也读得到】。工具的包放在
        /sdcard/Android/media/com.mctool.mcpatch/ —— 那是 Android 留给跨 App
        共享的目录。候选目录列表见 DIRS，会按顺序尝试，失败原因会打出来，
        方便在别的机型上定位问题。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__MCIMPORT__) return;
  window.__MCIMPORT__ = 1;

  var SLOTS = 9;                       // 与工具体的 SLOTS 一致
  var TOOL_PKG = 'com.mctool.mcpatch';

  // 按顺序尝试的候选位置。
  //
  // 为什么后缀是 .png：Android 11+ 的分区存储规定，别的 App 创建的【非媒体文件】
  // （.zip 就是）**任何位置、任何权限都读不到**；而【媒体文件】（图片/音频/视频）
  // 只要有 READ_EXTERNAL_STORAGE / READ_MEDIA_* 就能按路径读。
  // 所以工具用 MediaStore 把包登记成图片（.png / image/png），这里就按 .png 找。
  // 文件内容仍然是标准 zip —— decompress_map 只把它当 zip 解，不看后缀。
  //
  // 真机实测（Android 15、未 root、游戏 READ_EXTERNAL_STORAGE 已授予）：
  //   .zip 放 Download/          → Errno 13
  //   .zip 放 Android/media/     → Errno 13
  //   .png 放 Download/          → 通过
  var CANDS = [
    { dir: '/sdcard/Download/', ext: '.png' },
    { dir: '/storage/emulated/0/Download/', ext: '.png' },
    { dir: '/sdcard/Android/media/' + TOOL_PKG + '/', ext: '.png' },
    { dir: '/sdcard/Download/', ext: '.zip' },
    { dir: '/sdcard/Android/media/' + TOOL_PKG + '/', ext: '.zip' }
  ];

  // 世界内部的顶层目录分组（root 表示世界根目录）
  var SUFFIXES = ['root', 'db', 'players', 'resource_packs', 'behavior_packs', 'structures'];
  var MAXLINES = 60;

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
      var to = setTimeout(function () {
        if (!done) { done = true; delete waiters[tag]; reject(new Error('超时（20 秒）')); }
      }, 20000);
      var tag = allocTag(
        function (s) { if (done) return; done = true; clearTimeout(to); resolve(ret(s)); },
        function (e) { if (done) return; done = true; clearTimeout(to); reject(new Error(str(e))); }
      );
      waiters[tag] = {
        res: function (s) { if (done) return; done = true; clearTimeout(to); resolve(ret(s)); },
        rej: function (e) { if (done) return; done = true; clearTimeout(to); reject(new Error(str(e))); }
      };
      window.mc.sendMessage('json:' + JSON.stringify({
        module_name: mod, func_name: fn, use_instance: !!inst, args: args || [],
        tag: tag,
        return_callback: 'ComPyCallback.resolve',
        exception_callback: 'ComPyCallback.reject'
      }));
    });
  }

  function str(e) {
    return (typeof e === 'string') ? e : (e && e.message ? e.message : JSON.stringify(e));
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
  // 把异常分成三类，好在别的机型上远程定位问题
  function reasonOf(e) {
    var s = str(e);
    if (/Errno 2\b|No such file|not exist/i.test(s)) return 'missing';
    if (/Errno 13\b|Permission denied|EACCES/i.test(s)) return 'denied';
    return 'error';
  }

  // 解压一个包：{ok:true} / {ok:false, why:'missing'|'denied'|'error', msg:...}
  function tryPartOnce(src, dest) {
    return call('h5adaptor', false, 'decompress_map', [src, dest, true])
      .then(function () { return { ok: true }; },
            function (e) { return { ok: false, why: reasonOf(e), msg: str(e) }; });
  }

  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }

  /* 带重试的 tryPart。
     为什么要重试：工具是通过 MediaStore 把包写成 .png 的，写完清掉 IS_PENDING 之后
     别的 App 才看得见；游戏若在这之前就去读，会报「权限不足（游戏读不了这个文件）」。
     真机实测：第一次点「导入世界」必失败，要再点一次才行。
     这里改成原地等一会儿重试，用户点一次就能成。 */
  function tryPartWithRetry(src, dest) {
    var tries = 0;
    function once() {
      return tryPartOnce(src, dest).then(function (r) {
        if (r.ok) return r;
        tries++;
        if (tries >= 2) return r;
        return sleep(250).then(once);
      });
    }
    return once();
  }

  function importSlot(slot) {
    var id = 'mcw' + slot;
    return call('setting', false, 'get_minecraftWorlds_path').then(function (w) {
      var worldsPath = w;
      if (!worldsPath || typeof worldsPath !== 'string') throw new Error('拿不到世界目录');
      var recordsPath = worldsPath.replace(/\/minecraftWorlds\/?$/,
        '/storge/stream/resource_management/world_records');
      var worldDir = worldsPath + '/' + id;

      // 依次试候选位置，第一个能解出 root 包的就是它
      var tries = [];
      var i = 0;
      log('槽位 ' + slot + '：世界目录 = ' + w);
      function nextCand() {
        if (i >= CANDS.length) return Promise.resolve(null);
        var c = CANDS[i++];
        var base = c.dir + 'mcweb_' + slot + '_root' + c.ext;
        return tryPartWithRetry(base, worldDir).then(function (r) {
          if (r.ok) return c;
          // "找不到"是正常的（这个位置没放包），另外两种要记下来给用户看
          if (r.why !== 'missing') {
            tries.push(base + '  →  ' + (r.why === 'denied'
              ? '权限不足（游戏读不了这个文件）' : r.msg));
          }
          return nextCand();
        });
      }

      return nextCand().then(function (cand) {
        if (!cand) return { slot: slot, tries: tries };
        log('槽位 ' + slot + '：世界文件已解压（来自 ' + cand.dir + ' *' + cand.ext + '）');

        var chain = Promise.resolve();
        SUFFIXES.forEach(function (suf) {
          if (suf === 'root') return;
          chain = chain.then(function () {
            return tryPartWithRetry(cand.dir + 'mcweb_' + slot + '_' + suf + cand.ext,
                           worldDir + '/' + suf)
              .then(function (r) { if (r.ok) log('  ' + suf + '/ 已解压'); });
          });
        });
        return chain.then(function () {
          return tryPartWithRetry(cand.dir + 'mcweb_' + slot + '_record' + cand.ext, recordsPath)
            .then(function (r) {
              if (!r.ok) throw new Error('写世界记录失败: ' + r.msg);
              log('  ✅ 世界记录已写入');
              return { slot: slot, id: id };
            });
        });
      });
    });
  }

  function makeStep(slot) {
    return function (done) {
      if (done && done.id) return done;              // 已经成功过了，后面槽位不用看
      return importSlot(slot).then(function (r) {
        if (r && r.id) { log('槽位 ' + slot + ' 导入完成'); return r; }
        return done || r;
      });
    };
  }

  function doImport() {
    if (elBtn.disabled) return;
    elBtn.disabled = true;
    elBtn.textContent = '导入中…';
    log('开始检查槽位 1…' + SLOTS);
    log('候选位置: ' + CANDS.length + ' 个（首选 Download/ 里的 .png）');

    var chain = Promise.resolve(null);
    for (var k = 1; k <= SLOTS; k++) chain = chain.then(makeStep(k));
    chain.then(function (r) {
      if (r && r.id) {
        log('🎉 导入完成！请【完全退出游戏再重新打开】，世界就会出现在列表里');
        elBtn.textContent = '已导入 ✔';
        elBtn.style.background = '#2a6';
        return;
      }
      // 没成功：把每个目录的失败原因摊开，方便截图发回来
      if (r && r.tries && r.tries.length) {
        log('导入失败 —— 找到了包，但游戏打不开：', true);
        r.tries.forEach(function (t) { log('  ' + t, true); });
      } else {
        log('没有找到待导入的包（已重试）。请先在工具里点「② 准备导入」。', true);
        log('  找过这些位置:', true);
        CANDS.forEach(function (c) { log('    ' + c.dir + ' *' + c.ext, true); });
      }
      elBtn.textContent = '导入世界';
      elBtn.disabled = false;
    }).catch(function (e) {
      log('导入出错：' + str(e), true);
      elBtn.textContent = '导入世界';
      elBtn.disabled = false;
    });
  }

  /* ---------------- 界面 ---------------- */
  function ui() {
    if (elBox) return;
    elBox = document.createElement('div');
    elBox.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:2147483000;' +
      'font:12px/1.4 monospace;max-width:78vw;';

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
    elLog.style.cssText = 'display:none;margin:4px 0 0;padding:4px 6px;max-height:34vh;' +
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
    // 换手臂粗细（免 root）：工具会把 Download/mcarm_3px|4px.png 放好，
    // 这里启动时检查一次 —— 有就写进游戏私有目录。
    // 没有任何包时完全静默（绝大多数情况）。
    setTimeout(tryArmSwitch, 1500);
  }

  /* ================= 换手臂粗细（免 root） =================
     手臂体型存在游戏私有目录的 options.txt 里（game_skintypefull 那一行），
     普通应用碰不到，但游戏里的 h5adaptor.decompress_map 能以【游戏身份】写进去。
     工具（ArmSwitch.java）把改好的 options.txt 打成 zip、伪装成 .png 放进 Download/，
     这里负责把它落盘。详见 ArmSwitch.java 的类注释。
     decompress_map 成功后会【吃掉源文件】，所以同一个包天然只能生效一次。 */
  var ARM_DEST = '/data/data/com.netease.mc.qihoo/games/com.netease/minecraftpe';
  var ARM_BASES = ['mcarm_3px', 'mcarm_4px'];
  var ARM_DIRS = [
    '/sdcard/Download/',
    '/storage/emulated/0/Download/',
    '/sdcard/Android/media/' + TOOL_PKG + '/'
  ];
  var armDone = false;

  function tryArmSwitch() {
    if (armDone) return;
    armDone = true;
    var cands = [];
    ARM_DIRS.forEach(function (d) {
      ARM_BASES.forEach(function (b) { cands.push(d + b + '.png'); });
    });
    (function next(i) {
      if (i >= cands.length) return;          // 全失败 = 没有待切换的包，静默退出
      var p = cands[i];
      call('h5adaptor', false, 'decompress_map', [p, ARM_DEST, true])
        .then(function () {
          var px = (p.indexOf('_3px') >= 0) ? '3px 细（Alex）' : '4px 粗（Steve）';
          log('✅ 已写入手臂配置：' + px);
          log('   请【完全关掉游戏】再重新打开（切后台 / 划掉都行）');
          log('   ⚠️ 会重置游戏设置；期间别在游戏运行时覆盖安装 APK');
          if (elLog) elLog.style.display = 'block';
        })
        .catch(function () { next(i + 1); });
    })(0);
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
