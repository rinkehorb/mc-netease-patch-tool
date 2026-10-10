"""比对两份 /data/data/<包名> 快照，找出"玩家档案"到底在哪个文件。

背景
    手臂粗细（3px/4px）在首次运行时写死，之后改 APK 不生效（见 README §2.2.1）。
    档案在 /data/data/com.netease.mc.qihoo/ 里，只有 root 能看到。
    于是做两次快照——
        ① 装 3px 底包 → 全新安装 → 首次运行进一次世界 → root_snapshot.sh 3px
        ② 卸载 → 装 4px 底包 → 首次运行进一次世界 → root_snapshot.sh 4px
    —— 这两次的**唯一差别就是手臂体型**，那么两份快照里"唯一变了的东西"就是它。

用法
    python root_diff.py <3px目录> <4px目录>
    （先把两个 tgz 解到目录：tar xzf dd_3px.tgz -C dd_3px/）

输出
    1. 新增 / 删除 / 内容变化的文件清单
    2. 对变化的小文本文件，直接打印内容差异（并高亮 3/4、slim、custom、skin 等关键字）
    3. 如果什么都没变 → 说明档案在 SQLite/二进制里，会再给二进制文件的对比提示
"""
import hashlib
import os
import sys

KEYWORDS = [b"skin", b"Skin", b"geometry", b"slim", b"Slim", b"custom", b"Custom",
            b"alex", b"steve", b"persona", b"Persona", b"model", b"Model",
            b"arm", b"Arm", b"body", b"Body"]


def walk(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            try:
                data = open(p, "rb").read()
            except OSError:
                continue
            out[rel] = (len(data), hashlib.sha256(data).hexdigest(), data)
    return out


def summarize(tag, files):
    print("  %s: %d 个文件, 合计 %.1f KB" % (tag, len(files), sum(v[0] for v in files.values()) / 1024))
    for rel in sorted(files, key=lambda r: -files[r][0])[:10]:
        print("     %9d  %s" % (files[rel][0], rel))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    a, b = walk(sys.argv[1]), walk(sys.argv[2])
    print("=" * 70)
    summarize("第一份", a)
    summarize("第二份", b)

    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = sorted(r for r in set(a) & set(b) if a[r][1] != b[r][1])

    print()
    print("=" * 70)
    print("差异：新增 %d，删除 %d，内容变化 %d" % (len(added), len(removed), len(changed)))
    for label, items in (("新增", added), ("删除", removed)):
        for r in items:
            src = b if label == "新增" else a
            print("  [%s] %s (%d 字节)" % (label, r, src[r][0]))

    if not (added or removed or changed):
        print("  ⚠️ 两份快照完全一样 —— 说明体型没存在 /data/data 的普通文件里，")
        print("     可能在 SQLite 数据库里，或者根本不在这个目录（那就在世界存档或 .so 里）。")
        return 0

    print()
    print("=" * 70)
    print("变化文件的细节：")
    for r in changed + added:
        data = b[r][2]
        size = b[r][0]
        print()
        print("--- %s (%d 字节) ---" % (r, size))
        if size > 200_000:
            print("    （太大，跳过内容打印，只列出命中关键字）")
            hits = [k.decode() for k in KEYWORDS if k in data]
            print("    命中关键字: %s" % (hits or "无"))
            continue
        if b"\x00" in data[:4000]:
            print("    二进制文件，命中关键字: %s" % [k.decode() for k in KEYWORDS if k in data])
            print("    开头 64 字节: %s" % data[:64].hex(" "))
            continue
        try:
            old = a.get(r, (0, "", b""))[2].decode("utf-8", "replace").splitlines()
            new = data.decode("utf-8", "replace").splitlines()
        except Exception as e:
            print("    解码失败: %s" % e)
            continue
        n = 0
        for i in range(max(len(old), len(new))):
            x = old[i] if i < len(old) else "(缺)"
            y = new[i] if i < len(new) else "(缺)"
            if x != y:
                n += 1
                if n <= 20:
                    print("    第%d行  旧: %s" % (i + 1, x[:160]))
                    print("            新: %s" % y[:160])
        print("    共 %d 行不同" % n)

    print()
    print("=" * 70)
    print("下一步：改动最小的那个文件大概率就是玩家档案。")
    print("  用 root 直接改它里面的体型字段 → 重启游戏 → 看手臂是否变了。")
    print("  变了的话，就找到了「不用卸载重装也能换粗细」的办法。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
