#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minecraft 0.2.0.25445 (com.netease.mc.qihoo) 补丁 v2 —— 在【原始】smali 树上一键打全

背景（v1 实测反馈）：
  联网启动 -> WebView 打开已下线的网易 CDN 地址 -> HTTP 404 + OSS XML 一闪
  -> v1 的 onReceivedHttpError 把 XML 换成 networkerror.html（"哎呀！网络不给力呀！"）
  -> 页面没有自动退出机制，用户被卡在这张错误页上。

v2 目标：
  * 联网启动时【完全不弹 WebView】：
      native openWebview(1, url) 的 URL 命中已下线特征（netease.com / aliyuncs.com）
      -> 直接 nativeWebviewBackPressed()（等价于用户按了返回键），不显示弹窗。
  * 万一还有别的坏 URL 进了 WebView（门卫没拦住 / 已显示时二次 load_url）：
      onReceivedHttpError(API23+) 或 onPageFinished 注入的 JS 守卫命中错误特征
      -> 自动走 mc.autoClose() = nativeWebviewBackPressed() + dismiss()，
         不再停留错误页。
  * 保留逃生口：setCancelable(true) + 返回键 dismiss；hideWebview 加 isAdded 保护，
    避免"从未 show 过的 DialogFragment 被 dismiss"引发崩溃。

改动文件（全部 Java 层，不碰 .so、不重编译资源）：
  A. mcWebViewClient.smali
       A1. onReceivedHttpError：主文档 HTTP 错误 -> 注入 JS 自动关闭（不再载错误页）
       A2. onPageFinished：每次注入 JS 守卫，命中 nosuchkey/aliyuncs/<error>/
           specified key does not exist/网络不给力 -> mc.autoClose()
  B. mcWebViewDialog.smali
       B1. setCancelable(false) -> true
       B2. 新增 autoClose() @JavascriptInterface（UI 线程：nativeWebviewBackPressed + dismiss）
       B3. 新增内部类 mcWebViewDialog$4（Runnable）
  C. mcWebViewDialog$1.smali：返回键在通知 native 后追加 dismiss
  D. MainActivity$23.smali：URL 门卫（命中特征 -> nativeWebviewBackPressed，不弹窗）
  E. MainActivity.smali：hideWebview 增加 null/isAdded 保护

用法： python 04_patch_smali_v2.py [smali_root]
默认 smali_root = 与本脚本同级的 smali_v2/（必须是未打过补丁的原始树）
脚本幂等，可重复执行。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SMALI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "smali_v2")

PKG = os.path.join(SMALI, "com", "mojang", "minecraftpe")

# ---------------------------------------------------------------- JS 常量
# 只用单引号、不含双引号 # % & \ 原始反斜杠（中文标记用 \uXXXX 转义），避免 javascript: URL 解析歧义
JS_GUARD = (
    "javascript:(function(){try{"
    "if(window.__mcAutoClosed)return;"
    "var b=document.documentElement;"
    "var t=(b?(b.innerHTML+' '+(b.textContent||'')):'').toLowerCase();"
    "if(t.indexOf('nosuchkey')<0&&t.indexOf('aliyuncs.com')<0&&"
    "t.indexOf('<error>')<0&&t.indexOf('specified key does not exist')<0&&"
    "t.indexOf('\\u7f51\\u7edc\\u4e0d\\u7ed9\\u529b')<0)return;"
    "window.__mcAutoClosed=true;"
    "try{mc.autoClose()}catch(e){}"
    "}catch(e){}})()"
)
JS_AUTO = (
    "javascript:window.__mcAutoClosed=true;try{mc.autoClose()}catch(e){}"
)


def to_smali_literal(s: str) -> str:
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


# ------------------------------------------------------------ 新方法源码
NEW_ONPAGEFINISHED = """\
.method public onPageFinished(Landroid/webkit/WebView;Ljava/lang/String;)V
    .registers 4
    .param p1, "view"    # Landroid/webkit/WebView;
    .param p2, "url"    # Ljava/lang/String;

    .prologue
    invoke-super {p0, p1, p2}, Landroid/webkit/WebViewClient;->onPageFinished(Landroid/webkit/WebView;Ljava/lang/String;)V

    # 本补丁新增：每次页面加载完成后注入守卫，命中 OSS/网易错误特征即自动关闭
    const-string v0, {JS_GUARD}

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    return-void
.end method
""".replace("{JS_GUARD}", to_smali_literal(JS_GUARD))

NEW_HTTP_ERROR = """\
.method public onReceivedHttpError(Landroid/webkit/WebView;Landroid/webkit/WebResourceRequest;Landroid/webkit/WebResourceResponse;)V
    .registers 5
    .param p1, "view"    # Landroid/webkit/WebView;
    .param p2, "request"    # Landroid/webkit/WebResourceRequest;
    .param p3, "errorResponse"    # Landroid/webkit/WebResourceResponse;

    .prologue
    # API23+ 才回调；只处理主文档 HTTP 错误，注入 JS 自动关闭（不再载入错误页）
    invoke-interface {p2}, Landroid/webkit/WebResourceRequest;->isForMainFrame()Z

    move-result v0

    if-nez v0, :done

    const-string v0, {JS_AUTO}

    invoke-virtual {p1, v0}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V

    :done
    return-void
.end method
""".replace("{JS_AUTO}", to_smali_literal(JS_AUTO))

NEW_AUTOCLOSE = """\
.method public autoClose()V
    .registers 3
    .annotation runtime Landroid/webkit/JavascriptInterface;
    .end annotation

    .prologue
    # 本补丁新增：JS 守卫的自动关闭通道 —— 切到 UI 线程后通知 native 并 dismiss
    invoke-virtual {p0}, Lcom/mojang/minecraftpe/mcWebViewDialog;->getActivity()Landroid/app/Activity;

    move-result-object v0

    if-eqz v0, :done

    new-instance v1, Lcom/mojang/minecraftpe/mcWebViewDialog$4;

    invoke-direct {v1, p0}, Lcom/mojang/minecraftpe/mcWebViewDialog$4;-><init>(Lcom/mojang/minecraftpe/mcWebViewDialog;)V

    invoke-virtual {v0, v1}, Landroid/app/Activity;->runOnUiThread(Ljava/lang/Runnable;)V

    :done
    return-void
.end method
"""

NEW_INNER4 = """\
.class Lcom/mojang/minecraftpe/mcWebViewDialog$4;
.super Ljava/lang/Object;
.source "mcWebViewDialog.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/mojang/minecraftpe/mcWebViewDialog;->autoClose()V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic this$0:Lcom/mojang/minecraftpe/mcWebViewDialog;


# direct methods
.method constructor <init>(Lcom/mojang/minecraftpe/mcWebViewDialog;)V
    .registers 3
    .param p1, "this$0"    # Lcom/mojang/minecraftpe/mcWebViewDialog;

    .prologue
    iput-object p1, p0, Lcom/mojang/minecraftpe/mcWebViewDialog$4;->this$0:Lcom/mojang/minecraftpe/mcWebViewDialog;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .registers 3

    .prologue
    # 本补丁新增：等价于用户按返回键 —— 通知 native 关闭，再 dismiss 弹窗
    invoke-static {}, Lcom/mojang/minecraftpe/MainActivity;->getInstance()Lcom/mojang/minecraftpe/MainActivity;

    move-result-object v0

    invoke-virtual {v0}, Lcom/mojang/minecraftpe/MainActivity;->nativeWebviewBackPressed()V

    iget-object v1, p0, Lcom/mojang/minecraftpe/mcWebViewDialog$4;->this$0:Lcom/mojang/minecraftpe/mcWebViewDialog;

    invoke-virtual {v1}, Lcom/mojang/minecraftpe/mcWebViewDialog;->dismiss()V

    return-void
.end method
"""

NEW_RUN23 = """\
.method public run()V
    .registers 4

    .prologue
    # 本补丁新增：URL 门卫 —— 网易已下线 CDN/OSS 地址直接按返回键处理，不弹 WebView
    iget-object v1, p0, Lcom/mojang/minecraftpe/MainActivity$23;->val$url:Ljava/lang/String;

    if-eqz v1, :show

    const-string v0, "netease.com"

    invoke-virtual {v1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v2

    if-nez v2, :back

    const-string v0, "aliyuncs.com"

    invoke-virtual {v1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v2

    if-nez v2, :back

    :show
    iget-object v0, p0, Lcom/mojang/minecraftpe/MainActivity$23;->this$0:Lcom/mojang/minecraftpe/MainActivity;

    iget-object v1, p0, Lcom/mojang/minecraftpe/MainActivity$23;->val$url:Ljava/lang/String;

    invoke-virtual {v0, v1}, Lcom/mojang/minecraftpe/MainActivity;->showWebviewDialog(Ljava/lang/String;)V

    iget-object v0, p0, Lcom/mojang/minecraftpe/MainActivity$23;->this$0:Lcom/mojang/minecraftpe/MainActivity;

    invoke-virtual {v0}, Lcom/mojang/minecraftpe/MainActivity;->getWindow()Landroid/view/Window;

    move-result-object v0

    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;

    move-result-object v0

    const/4 v1, 0x0

    invoke-virtual {v0, v1}, Landroid/view/View;->setOnSystemUiVisibilityChangeListener(Landroid/view/View$OnSystemUiVisibilityChangeListener;)V

    return-void

    :back
    iget-object v0, p0, Lcom/mojang/minecraftpe/MainActivity$23;->this$0:Lcom/mojang/minecraftpe/MainActivity;

    invoke-virtual {v0}, Lcom/mojang/minecraftpe/MainActivity;->nativeWebviewBackPressed()V

    return-void
.end method
"""

NEW_HIDEWEBVIEW = """\
.method private hideWebview()V
    .registers 3

    .prologue
    # 本补丁新增：弹窗从未显示过（URL 门卫拦截）时跳过 dismiss，避免 Fragment 未添加崩溃
    iget-object v0, p0, Lcom/mojang/minecraftpe/MainActivity;->m_webViewDialog:Lcom/mojang/minecraftpe/mcWebViewDialog;

    if-eqz v0, :done

    invoke-virtual {v0}, Lcom/mojang/minecraftpe/mcWebViewDialog;->isAdded()Z

    move-result v1

    if-eqz v1, :done

    invoke-virtual {v0}, Lcom/mojang/minecraftpe/mcWebViewDialog;->dismiss()V

    :done
    return-void
.end method
"""


def patch_file(rel: str, fn):
    abspath = os.path.join(PKG, rel)
    with open(abspath, "r", encoding="utf-8") as f:
        src = f.read()
    new = fn(src)
    if new is None:
        print("  [skip] %s (already patched)" % rel)
        return False
    with open(abspath, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print("  [ ok ] %s" % rel)
    return True


# ---------------------------------------------------------------- A: client
def patch_client(src: str):
    changed = False

    # 1) 替换空实现 onPageFinished 为守卫版
    if "onReceivedHttpError" in src and "window.__mcAutoClosed" in src:
        return None  # 已打过 v2
    m = re.search(
        r"\.method public onPageFinished\(Landroid/webkit/WebView;Ljava/lang/String;\)V.*?\n\.end method\n",
        src,
        re.S,
    )
    assert m, "onPageFinished 未找到"
    src = src[: m.start()] + NEW_ONPAGEFINISHED + src[m.end():]
    changed = True

    # 2) 追加 onReceivedHttpError
    if "onReceivedHttpError" not in src:
        src += "\n" + NEW_HTTP_ERROR
        changed = True

    return src if changed else None


# ------------------------------------------------- B: dialog（取消 + autoClose）
def patch_dialog(src: str):
    changed = False
    old = "    const/4 v2, 0x0\n\n    invoke-virtual {p0, v2}, Lcom/mojang/minecraftpe/mcWebViewDialog;->setCancelable(Z)V"
    if old in src:
        src = src.replace(old, old.replace("const/4 v2, 0x0", "const/4 v2, 0x1"), 1)
        changed = True

    if "autoClose()V" not in src:
        anchor = ".method public closeMe()V"
        idx = src.find(anchor)
        assert idx != -1, "closeMe 未找到"
        end = src.find(".end method", idx)
        assert end != -1
        # 保留 closeMe 自己的 .end method，在其后插入 autoClose 方法
        src = src[:end] + ".end method\n\n" + NEW_AUTOCLOSE + src[end + len(".end method"):]
        changed = True

    return src if changed else None


# ---------------------------------------------------------- C: 返回键 dismiss
def patch_backkey(src: str):
    if "本补丁新增：通知 native 之后再主动 dismiss" in src:
        return None  # 已打过
    old = "    invoke-virtual {v1}, Lcom/mojang/minecraftpe/MainActivity;->nativeWebviewBackPressed()V\n"
    if old not in src:
        return None
    add = (
        "\n    # 本补丁新增：通知 native 之后再主动 dismiss 一次，保证弹窗一定能关掉\n"
        "    iget-object v1, p0, Lcom/mojang/minecraftpe/mcWebViewDialog$1;->this$0:Lcom/mojang/minecraftpe/mcWebViewDialog;\n\n"
        "    invoke-virtual {v1}, Lcom/mojang/minecraftpe/mcWebViewDialog;->dismiss()V\n"
    )
    return src.replace(old, old + add, 1)


# ----------------------------------------------------------- D: URL 门卫
def patch_run23(src: str):
    m = re.search(
        r"\.method public run\(\)V.*?\n\.end method\n",
        src,
        re.S,
    )
    assert m, "MainActivity$23.run 未找到"
    if "netease.com" in src and "nativeWebviewBackPressed" in src:
        return None  # 已打过
    return src[: m.start()] + NEW_RUN23 + src[m.end():]


# ------------------------------------------------------- E: hideWebview 保护
def patch_hidewebview(src: str):
    m = re.search(
        r"\.method private hideWebview\(\)V.*?\n\.end method\n",
        src,
        re.S,
    )
    assert m, "hideWebview 未找到"
    if "isAdded()Z" in m.group(0):
        return None  # 已打过
    return src[: m.start()] + NEW_HIDEWEBVIEW + src[m.end():]


def count_smali(root):
    n = 0
    for _, _, fs in os.walk(root):
        n += len([f for f in fs if f.endswith(".smali")])
    return n


def main():
    if not os.path.isdir(PKG):
        sys.exit("找不到 smali 目录: %s" % PKG)
    n0 = count_smali(SMALI)
    print("smali 根目录: %s (初始 %d 个 .smali)" % (SMALI, n0))
    print("[A] mcWebViewClient")
    patch_file("mcWebViewClient.smali", patch_client)
    print("[B] mcWebViewDialog")
    patch_file("mcWebViewDialog.smali", patch_dialog)
    print("[B3] 新增 mcWebViewDialog$4")
    p4 = os.path.join(PKG, "mcWebViewDialog$4.smali")
    if os.path.exists(p4):
        print("  [skip] mcWebViewDialog$4 (exists)")
    else:
        with open(p4, "w", encoding="utf-8", newline="\n") as f:
            f.write(NEW_INNER4)
        print("  [ ok ] mcWebViewDialog$4.smali (new)")
    print("[C] mcWebViewDialog$1 (BACK)")
    patch_file("mcWebViewDialog$1.smali", patch_backkey)
    print("[D] MainActivity$23 (URL gate)")
    patch_file("MainActivity$23.smali", patch_run23)
    print("[E] MainActivity.hideWebview")
    patch_file("MainActivity.smali", patch_hidewebview)

    # 自检
    checks = [
        ("mcWebViewClient.smali", ["onReceivedHttpError", "window.__mcAutoClosed", "mc.autoClose"]),
        ("mcWebViewDialog.smali", ["autoClose()V", "setCancelable", "const/4 v2, 0x1"]),
        ("mcWebViewDialog$4.smali", ["nativeWebviewBackPressed", "dismiss()V"]),
        ("mcWebViewDialog$1.smali", ["nativeWebviewBackPressed", "dismiss()V"]),
        ("MainActivity$23.smali", ["netease.com", "aliyuncs.com", "nativeWebviewBackPressed"]),
        ("MainActivity.smali", ["isAdded()Z", "dismiss()V"]),
    ]
    print("\n== 自检 ==")
    ok = True
    for rel, needles in checks:
        with open(os.path.join(PKG, rel), "r", encoding="utf-8") as f:
            txt = f.read()
        missing = [n for n in needles if n not in txt]
        print("  %-32s %s" % (rel, "OK" if not missing else "缺: %s" % missing))
        ok = ok and not missing
    print("自检结果:", "通过" if ok else "失败")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
