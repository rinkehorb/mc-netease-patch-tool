#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把签名后 APK 的 dex 里注入 JS 字符串提取出来，与设计稿逐字节比对。"""
import re
import sys

SMALI_CLIENT = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v2_verify\com\mojang\minecraftpe\mcWebViewClient.smali"

EXPECTED_GUARD = (
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
EXPECTED_AUTO = "javascript:window.__mcAutoClosed=true;try{mc.autoClose()}catch(e){}"


def unescape_smali(s: str) -> str:
    """把 smali 源码字符串字面量还原为 dex 中的实际字符串。"""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "u":
                out.append(chr(int(s[i + 2:i + 6], 16)))
                i += 6
            elif n == "n":
                out.append("\n"); i += 2
            elif n == "t":
                out.append("\t"); i += 2
            else:
                out.append(n); i += 2
        else:
            out.append(c); i += 1
    return "".join(out)


def main():
    src = open(SMALI_CLIENT, encoding="utf-8").read()
    literals = re.findall(r'const-string v0, "((?:[^"\\]|\\.)*)"', src)
    js = [unescape_smali(x) for x in literals if x.startswith("javascript:")]
    print("注入 JS 字符串数:", len(js))
    for i, s in enumerate(js):
        kind = "unknown"
        if s == EXPECTED_GUARD:
            kind = "GUARD (onPageFinished)"
        elif s == EXPECTED_AUTO:
            kind = "AUTO (onReceivedHttpError)"
        print("  [%d] len=%d  kind=%s" % (i, len(s), kind))
    ok = (EXPECTED_GUARD in js) and (EXPECTED_AUTO in js)
    print("\n结果:", "通过 —— 两条 JS 与设计稿完全一致" if ok else "失败")
    # 中文标记确认（\u7f51\u7edc\u4e0d\u7ed9\u529b = 网络不给力）
    if EXPECTED_GUARD in js:
        g = js[js.index(EXPECTED_GUARD)]
        print("中文标记 '网络不给力' 在守卫中:", "网络不给力" in g)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
