#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minecraft 0.2.0.25445 (com.netease.mc.qihoo) 补丁脚本 —— 第 1 步：改写 smali

根因（已溯源确认）：
  native(libminecraftpe.so) --JNI--> MainActivity.openWebview(int isopen, String url)
    isopen==1 -> MainActivity$23.run() -> MainActivity.showWebviewDialog(url)
      -> mcWebViewDialog.set_loadurl(url) + show_a(FragmentManager,"WebviewDialog")
      -> DialogFragment(全屏 / setCancelable(false)) 里的 WebView 直接 loadUrl(url)

  该 url 指向网易 2017 年 OBT 构建的 CDN：
      http://g79.gdl.netease.com/obt20171212182501/...
  对象已从阿里云 OSS 删除 -> HTTP 404，响应体是 OSS 的 XML 错误页：
      <Code>NoSuchKey</Code>...<HostId>scdn-netease-hangzhou-gdl17.oss-cn-hangzhou.aliyuncs.com</HostId>
  WebView 把这段 XML 当普通文档渲染出来；又因为 DialogFragment 不可取消、
  要等 H5 回调 mc.closeMe() 才消失，回调永远不来 -> 表现为"弹 XML + 卡死"。

  WebView 的请求走 Chromium 自己的网络栈，不经过 Java 的 NetUtil / AppsFlyerLib /
  iapppay / heepay，所以之前改那些类无效。

补丁内容（全部只动 Java 层，不碰 30MB 的 libminecraftpe.so，不重编译 resources.arsc）：
  A. mcWebViewClient
     A1. onReceivedHttpError（API23+）：主文档 HTTP 状态 >=400 时，改载本地
         file:///android_asset/storge/asset/networkerror.html（游戏自带的友好错误页），
         从 HTTP 层直接掐掉 XML 的渲染。
     A2. onPageFinished：注入一次性 JS 守卫，覆盖 API<23 以及"XML 以 200 返回"的情况。
         检测到 OSS 报错特征（nosuchkey / aliyuncs.com / <error> / specified key does not exist）
         就把页面替换成中文友好提示 + 「关 闭」按钮，按钮调用游戏自己的
         mc.closeMe()（@JavascriptInterface，正是官方 H5 关闭弹窗的通道）。
  B. mcWebViewDialog：setCancelable(false) -> true（逃生口）
  C. mcWebViewDialog$1：BACK 键除通知 native 外，再 dismiss() 一次，保证永远能关掉。

用法： python 01_patch_smali.py [smali_root]
默认 smali_root = 与本脚本同级的 smali/
脚本可重复执行（幂等）。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SMALI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "smali")

PKG = os.path.join(SMALI, "com", "mojang", "minecraftpe")
ERROR_PAGE = "file:///android_asset/storge/asset/networkerror.html"

# ---------------------------------------------------------------- JS 守卫
# 只用单引号、不含 # % & \ 与双引号，避免 javascript: URL 的解析歧义
JS = (
    "javascript:(function(){try{"
    "var b=document.documentElement;"
    "var t=(b?(b.innerHTML+' '+(b.textContent||'')):'').toLowerCase();"
    "if(t.indexOf('nosuchkey')<0&&t.indexOf('aliyuncs.com')<0&&"
    "t.indexOf('<error>')<0&&t.indexOf('specified key does not exist')<0)return;"
    "var q=String.fromCharCode(39);"
    "var h='<html><head><meta charset=utf-8>"
    "<meta name='+q+'viewport'+q+' content='+q+'width=device-width,initial-scale=1'+q+'>"
    "</head><body style='+q+'margin:0;background:rgb(233,209,159);color:rgb(59,59,59);"
    "font-family:sans-serif;text-align:center;padding-top:22vh'+q+'>'+"
    "'<div style='+q+'font-size:21px;font-weight:bold'+q+'>在线内容无法加载</div>'+"
    "'<div style='+q+'font-size:14px;line-height:1.8;margin:20px 30px'+q+'>"
    "该在线页面已从服务器下线（2017 年资源已删除）。<br>"
    "不影响单机游玩，点下面按钮关掉即可。</div>'+"
    "'<button style='+q+'font-size:17px;padding:12px 46px;border:0;border-radius:6px;"
    "background:rgb(106,168,79);color:rgb(255,255,255)'+q+' "
    "onclick='+q+'try{mc.closeMe()}catch(e){}'+q+'>关 闭</button>'+"
    "'</body></html>';"
    "document.open();document.write(h);document.close();"
    "}catch(e){}})()"
)


def to_smali_literal(s: str) -> str:
    """把 Python 字符串转成 smali const-string 的双引号字面量。"""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or ord(ch) > 0x7E:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


JS_LIT = to_smali_literal(JS)

# ------------------------------------------------------------ 新方法源码
NEW_ONPAGEFINISHED = """\
.method public onPageFinished(Landroid/webkit/WebView;Ljava/lang/String;)V
    .registers 5
    .param p1, "view"    # Landroid/webkit/WebView;
    .param p2, "url"    # Ljava/lang/String;

    .prologue
    invoke-super {p0, p1, p2}, Landroid/webkit/WebViewClient;->onPageFinished(Landroid/webkit/WebView;Ljava/lang/String;)V

    # 一次性守卫：避免 javascript: 载入可能引发的重入
    iget-boolean v1, p0, Lcom/mojang/minecraftpe/mcWebViewClient;->injected:Z

    if-eqz v1, :done

    const/4 v1, 0x1

    iput-boolean v1, p0, Lcom/mojang/minecraftpe/mcWebViewClient;->injected:Z

    const-string v0, {JS}

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    :done
    return-void
.end method
""".replace("{JS}", JS_LIT)

NEW_HTTP_ERROR = """\
.method public onReceivedHttpError(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;Landroid/webkit/WebResourceResponse;)V
    .registers 5
    .param p1, "view"    # Landroid/webkit/WebView;
    .param p2, "request"    # Landroid/webkit/WebResourceRequest;
    .param p3, "errorResponse"    # Landroid/webkit/WebResourceResponse;

    .prologue
    # API23+ 才回调；只处理主文档，避免子资源 404 误触
    invoke-interface {p2}, Landroid/webkit/WebResourceRequest;->isForMainFrame()Z

    move-result v0

    if-nez v0, :done

    const-string v0, "{ERR}"

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    :done
    return-void
.end method
""".replace("{ERR}", ERROR_PAGE)


def patch(path: str, fn) -> bool:
    abspath = os.path.join(PKG, path)
    with open(abspath, "r", encoding="utf-8") as f:
        src = f.read()
    new = fn(src)
    if new is None:
        print("  [skip] %s (already patched)" % path)
        return False
    with open(abspath, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print("  [ ok ] %s" % path)
    return True


# ---------------------------------------------------------------- A: client
def patch_client(src: str):
    changed = False

    if "injected:Z" not in src:
        anchor = '.super Landroid/webkit/WebViewClient;\n.source "mcWebViewClient.java"\n'
        assert anchor in src, "anchor not found in mcWebViewClient"
        src = src.replace(
            anchor,
            anchor + "\n\n# 本补丁新增：注入守卫\n.field private injected:Z\n",
            1,
        )
        changed = True

    if "onReceivedHttpError" not in src:
        m = re.search(
            r"\.method public onPageFinished\(Landroid/webkit/WebView;Ljava/lang/String;\)V.*?\n\.end method\n",
            src,
            re.S,
        )
        assert m, "onPageFinished not found"
        src = src[: m.start()] + NEW_ONPAGEFINISHED + "\n" + NEW_HTTP_ERROR + src[m.end():]
        changed = True

    return src if changed else None


# ---------------------------------------------------------------- B: dialog
def patch_dialog(src: str):
    old = "    const/4 v2, 0x0\n\n    invoke-virtual {p0, v2}, Lcom/mojang/minecraftpe/mcWebViewDialog;->setCancelable(Z)V"
    if old not in src:
        return None
    src = src.replace(
        old,
        "    const/4 v2, 0x1\n\n    invoke-virtual {p0, v2}, Lcom/mojang/minecraftpe/mcWebViewDialog;->setCancelable(Z)V",
        1,
    )
    return src


# ------------------------------------------------------------ C: back button
def patch_backkey(src: str):
    old = "    invoke-virtual {v1}, Lcom/mojang/minecraftpe/MainActivity;->nativeWebviewBackPressed()V\n"
    if old not in src:
        return None
    add = (
        "\n    # 本补丁新增：通知 native 之后再主动 dismiss 一次，保证弹窗一定能关掉\n"
        "    iget-object v1, p0, Lcom/mojang/minecraftpe/mcWebViewDialog$1;->this$0:Lcom/mojang/minecraftpe/mcWebViewDialog;\n\n"
        "    invoke-virtual {v1}, Lcom/mojang/minecraftpe/mcWebViewDialog;->dismiss()V\n"
    )
    src = src.replace(old, old + add, 1)
    return src


def main():
    if not os.path.isdir(PKG):
        sys.exit("找不到 smali 目录: %s" % PKG)
    print("smali 根目录: %s" % SMALI)
    print("[A] mcWebViewClient")
    patch("mcWebViewClient.smali", patch_client)
    print("[B] mcWebViewDialog")
    patch("mcWebViewDialog.smali", patch_dialog)
    print("[C] mcWebViewDialog$1 (BACK)")
    patch("mcWebViewDialog$1.smali", patch_backkey)
    print("\nJS 长度 = %d 字节, smali 字面量长度 = %d" % (len(JS), len(JS_LIT)))
    print("完成。")


if __name__ == "__main__":
    main()
