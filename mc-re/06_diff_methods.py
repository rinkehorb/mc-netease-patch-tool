#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比 补丁smali树(smali_v2) 与 最终dex反向还原树(smali_v2_verify) 的方法级差异。"""
import os
import re

A = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v2"
B = r"C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v2_verify"

def methods(path):
    src = open(path, encoding="utf-8").read()
    return re.findall(r"\.method (?:public|private|protected|static|final|synthetic|constructor)? ?(?:\(.*?\))*?([A-Za-z0-9_$<>]+)\(.*?\)", src, re.S)

diff = []
for root, _, files in os.walk(A):
    rel = os.path.relpath(root, A)
    for f in files:
        if not f.endswith(".smali"):
            continue
        pa = os.path.join(root, f)
        pb = os.path.join(B, rel, f)
        ma = sorted(methods(pa))
        mb = sorted(methods(pb)) if os.path.exists(pb) else []
        if ma != mb:
            diff.append((rel, f, ma, mb))

for rel, f, ma, mb in diff:
    print("== %s\\%s" % (rel, f))
    print("   patched :", ma)
    print("   verify  :", mb)
if not diff:
    print("两个树的方法完全一致")
