package com.mctool.mcpatch.core;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * 基岩版 {@code level.dat} 的版本字段读写。
 *
 * <h3>格式</h3>
 * 这个网易版本（以及 LevelDB 时代的基岩版）的 {@code level.dat} 是
 * <b>8 字节头 + 明文小端 NBT</b>，没有压缩。头 8 字节原样保留不动。
 *
 * <p>要注意的几个字段（都是定长，所以可以<b>原地改字节</b>，不必重新序列化整个 NBT）：
 * <ul>
 *   <li>{@code lastOpenedWithVersion} —— TAG_List，元素是 TAG_Int，形如 {@code [1,1,3,50]}。
 *       游戏拿它和 {@code GameVersion::current()} 比，<b>比客户端新就拒绝加载</b>
 *       （报 {@code disconnectionScreen.futureVersion}："更新版本的该游戏保存了这一等级"）</li>
 *   <li>{@code StorageVersion} —— TAG_Int。磁盘格式档位，比客户端的
 *       {@code SharedConstants::CurrentStorageVersion} 新同样加载不了</li>
 *   <li>{@code NetworkVersion} —— TAG_Int</li>
 * </ul>
 *
 * <p>实测（真机）：客户端 {@code GameVersion::current()} = {@code [1,1,3,50]}、
 * {@code CurrentStorageVersion} = {@code 5}、{@code NetworkVersion} = {@code 113}。
 */
public final class LevelDat {

    /** 8 字节头 + 明文 NBT 的包，头长度。 */
    private static final int HEADER = 8;

    // TAG 类型
    private static final int TAG_BYTE = 1, TAG_SHORT = 2, TAG_INT = 3, TAG_LONG = 4;
    private static final int TAG_FLOAT = 5, TAG_DOUBLE = 6, TAG_BYTE_ARRAY = 7;
    private static final int TAG_STRING = 8, TAG_LIST = 9, TAG_COMPOUND = 10, TAG_INT_ARRAY = 11;

    private LevelDat() {
    }

    /** 读出来的版本信息 + 各字段在字节数组里的偏移（用于原地改写）。 */
    public static final class Info {
        public int[] lastOpenedWithVersion;
        public Integer storageVersion;
        public Integer networkVersion;
        public String levelName;
        public boolean nbtOk;
        public String error;

        /** 是否 8 字节头 + 明文 NBT 这种布局。 */
        public boolean plainNbt;
        /** 是否（可能）被压缩过——那样这里就不做原地改写。 */
        public boolean compressed;

        int bodyStart;                 // NBT 起始偏移
        int versionOff = -1;           // lastOpenedWithVersion 的元素起始偏移
        int versionOffInBody = -1;     // 相对 NBT 起点
        int versionCount;
        int storageOff = -1;
        int storageOffInBody = -1;
        int networkOff = -1;
        int networkOffInBody = -1;

        public String versionString() {
            if (lastOpenedWithVersion == null || lastOpenedWithVersion.length == 0) return "(无)";
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < lastOpenedWithVersion.length; i++) {
                if (i > 0) sb.append('.');
                sb.append(lastOpenedWithVersion[i]);
            }
            return sb.toString();
        }

        /** 和目标版本比较：大于返回 1，等于 0，小于 -1，无法比较返回 0。 */
        public int compareVersion(int[] target) {
            if (lastOpenedWithVersion == null || target == null) return 0;
            int n = Math.max(lastOpenedWithVersion.length, target.length);
            for (int i = 0; i < n; i++) {
                int a = i < lastOpenedWithVersion.length ? lastOpenedWithVersion[i] : 0;
                int b = i < target.length ? target[i] : 0;
                if (a != b) return a > b ? 1 : -1;
            }
            return 0;
        }
    }

    // ------------------------------------------------------------------ 读

    public static Info read(byte[] dat) {
        Info info = new Info();
        if (dat == null || dat.length < 16) {
            info.error = "文件太小";
            return info;
        }
        byte[] body;
        if (dat[0] == TAG_COMPOUND || dat[0] == 0x0B) {
            // 没有头，直接是 NBT
            info.plainNbt = true;
            info.bodyStart = 0;
            body = dat;
        } else if (dat[HEADER] == TAG_COMPOUND || dat[HEADER] == 0x0B) {
            info.plainNbt = true;
            info.bodyStart = HEADER;
            body = new byte[dat.length - HEADER];
            System.arraycopy(dat, HEADER, body, 0, body.length);
        } else {
            // 头 2 字节像是 gzip/zlib 魔数
            int b0 = dat[0] & 0xFF, b1 = dat[1] & 0xFF;
            if (b0 == 0x1F && b1 == 0x8B) info.compressed = true;
            else if (b0 == 0x78) info.compressed = true;
            info.error = info.compressed ? "level.dat 是压缩的，本工具不处理" : "无法识别的 level.dat 布局";
            return info;
        }

        try {
            Cursor c = new Cursor(body);
            int type = c.u1();
            if (type != TAG_COMPOUND) throw new IllegalStateException("根不是 Compound: " + type);
            c.str();                                  // 根名（空串）
            while (true) {
                int t = c.u1();
                if (t == 0) break;
                String name = c.str();
                int mark = c.pos;
                skip(c, t);
                if ("lastOpenedWithVersion".equals(name) && t == TAG_LIST) {
                    // 回读一遍拿元素信息
                    Cursor c2 = new Cursor(body);
                    c2.pos = mark;
                    int elemType = c2.u1();
                    int n = c2.i4();
                    info.versionCount = n;
                    info.versionOffInBody = c2.pos;
                    info.versionOff = info.bodyStart + c2.pos;
                    info.lastOpenedWithVersion = new int[n];
                    for (int i = 0; i < n; i++) info.lastOpenedWithVersion[i] = c2.i4();
                } else if ("StorageVersion".equals(name) && t == TAG_INT) {
                    info.storageOffInBody = mark;
                    info.storageOff = info.bodyStart + mark;
                    info.storageVersion = i4(body, mark);
                } else if ("NetworkVersion".equals(name) && t == TAG_INT) {
                    info.networkOffInBody = mark;
                    info.networkOff = info.bodyStart + mark;
                    info.networkVersion = i4(body, mark);
                } else if ("LevelName".equals(name) && t == TAG_STRING) {
                    Cursor c2 = new Cursor(body);
                    c2.pos = mark;
                    info.levelName = c2.str();
                }
            }
            info.nbtOk = true;
        } catch (Throwable e) {
            info.error = "NBT 解析失败: " + e.getMessage();
        }
        return info;
    }

    // ------------------------------------------------------------------ 改

    /**
     * 原地把版本字段改写掉。只动那 4/4/4 个字节，其它字节一个不碰，长度不变。
     *
     * @return 实际改动的字节数；返回 -1 表示无法改（压缩 / 字段缺失）
     */
    public static int patch(byte[] dat, Info info, int[] version, Integer storage, Integer network) {
        if (info == null || !info.nbtOk || !info.plainNbt) return -1;
        int changed = 0;
        if (version != null && info.versionOff >= 0 && info.versionCount > 0) {
            for (int i = 0; i < info.versionCount; i++) {
                int v = i < version.length ? version[i] : 0;
                int off = info.versionOff + i * 4;
                if (i4(dat, off) != v) changed++;
                putI4(dat, off, v);
            }
        }
        if (storage != null && info.storageOff >= 0) {
            if (i4(dat, info.storageOff) != storage) changed++;
            putI4(dat, info.storageOff, storage);
        }
        if (network != null && info.networkOff >= 0) {
            if (i4(dat, info.networkOff) != network) changed++;
            putI4(dat, info.networkOff, network);
        }
        return changed;
    }

    // ------------------------------------------------------------------ NBT 小工具

    private static final class Cursor {
        final byte[] d;
        int pos;

        Cursor(byte[] d) {
            this.d = d;
        }

        int u1() {
            if (pos >= d.length) throw new IllegalStateException("越界");
            return d[pos++] & 0xFF;
        }

        int i4() {
            int v = LevelDat.i4(d, pos);
            pos += 4;
            return v;
        }

        String str() {
            // 注意：基岩版 NBT 是【小端】—— 字符串长度也是小端。
            // （真实 level.dat 里 "CenterMapsToOrigin" 前面是 12 00，即 0x0012=18，
            //   如果是大端会读成 0x1200=4608，整个解析就崩了。这里踩过。）
            int n = (d[pos] & 0xFF) | ((d[pos + 1] & 0xFF) << 8);
            pos += 2;
            String s = new String(d, pos, n, java.nio.charset.StandardCharsets.UTF_8);
            pos += n;
            return s;
        }
    }

    private static void skip(Cursor c, int type) {
        byte[] d = c.d;
        switch (type) {
            case TAG_BYTE:
                c.pos += 1;
                return;
            case TAG_SHORT:
                c.pos += 2;
                return;
            case TAG_INT:
                c.pos += 4;
                return;
            case TAG_LONG:
                c.pos += 8;
                return;
            case TAG_FLOAT:
                c.pos += 4;
                return;
            case TAG_DOUBLE:
                c.pos += 8;
                return;
            case TAG_BYTE_ARRAY: {
                int n = c.i4();
                c.pos += n;
                return;
            }
            case TAG_STRING:
                c.str();
                return;
            case TAG_LIST: {
                int elem = c.u1();
                int n = c.i4();
                for (int i = 0; i < n; i++) skip(c, elem);
                return;
            }
            case TAG_COMPOUND: {
                while (true) {
                    int t = c.u1();
                    if (t == 0) return;
                    c.str();
                    skip(c, t);
                }
            }
            case TAG_INT_ARRAY: {
                int n = c.i4();
                c.pos += 4 * n;
                return;
            }
            default:
                throw new IllegalStateException("未知 TAG: " + type);
        }
    }

    static int i4(byte[] d, int off) {
        return (d[off] & 0xFF) | ((d[off + 1] & 0xFF) << 8)
                | ((d[off + 2] & 0xFF) << 16) | ((d[off + 3] & 0xFF) << 24);
    }

    static void putI4(byte[] d, int off, int v) {
        d[off] = (byte) (v & 0xFF);
        d[off + 1] = (byte) ((v >>> 8) & 0xFF);
        d[off + 2] = (byte) ((v >>> 16) & 0xFF);
        d[off + 3] = (byte) ((v >>> 24) & 0xFF);
    }

    /** 把 {"a":1} 形式的 JSON 拼出来（只用于生成世界记录，不需要完整 JSON 库）。 */
    static String jsonEscape(String s) {
        if (s == null) return "";
        StringBuilder sb = new StringBuilder(s.length() + 8);
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '"' || ch == '\\') sb.append('\\').append(ch);
            else if (ch < 0x20) sb.append(String.format("\\u%04x", (int) ch));
            else if (ch > 0x7E) sb.append(String.format("\\u%04x", (int) ch));
            else sb.append(ch);
        }
        return sb.toString();
    }

    /** 供测试/调试：把若干 int 拼成 [1,1,3,50] 这样的字符串。 */
    public static String join(int[] a) {
        if (a == null) return "(null)";
        List<String> l = new ArrayList<String>();
        for (int v : a) l.add(String.valueOf(v));
        return l.toString();
    }

    static byte[] concat(List<byte[]> parts) {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        for (byte[] p : parts) bos.write(p, 0, p.length);
        return bos.toByteArray();
    }
}
