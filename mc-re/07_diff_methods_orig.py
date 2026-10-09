#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 原始树(重新baksmali) 与 补丁树(smali_v2) 的方法级差异。"""
import os
import re

A = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_orig_check"
B = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v2"

def methods(path):
    src = open(path, encoding="utf-8").read()
    return sorted(re.findall(r"\.method .*?([A-Za-z0-9_$<>]+)\(.*?\)(?:V|Z|I|J|Ljava/lang/String;|Landroid/.*?;|\[.*?;)?", src))

added, removed = [], []
for root, _, files in os.walk(A):
    rel = os.path.relpath(root, A)
    for f in files:
        if not f.endswith(".smali"):
            continue
        pa = os.path.join(root, f)
        pb = os.path.join(B, rel, f)
        ma = methods(pa)
        mb = methods(pb) if os.path.exists(pb) else []
        for m in mb:
            if m not in ma:
                added.append((rel, f, m))
        for m in ma:
            if m not in mb:
                removed.append((rel, f, m))
print("新增方法:")
for rel, f, m in added:
    print("   %s\\%s :: %s" % (rel, f, m))
print("移除方法:", removed or "无")
