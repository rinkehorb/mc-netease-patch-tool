package com.mctool.mcpatch.core;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * 把外部 {@code .mcworld} / 世界 zip 处理成「可以在游戏里一键导入」的几个包。
 *
 * <h3>为什么要拆包</h3>
 * 网易版 H5 里唯一能写文件的接口是
 * {@code h5adaptor.decompress_map(源zip, 目标目录, true)}，它的特点是：
 * <ol>
 *   <li><b>目标目录是任意的</b> —— 所以把「世界记录 JSON」也打成一个 zip，
 *       就能直接解压进网易的记录目录，<b>不需要 root</b>；</li>
 *   <li><b>会把包内目录结构完全压平</b> —— 所以 {@code db/xxx} 打进包再解出来，
 *       {@code db/} 前缀会消失。对策是<b>按顶层目录分组</b>：
 *       每个组一个包，解压时把目标目录直接指向那个子目录
 *       （{@code db.zip → <世界目录>/db}）。</li>
 * </ol>
 *
 * <h3>产出（按顶层目录分组）</h3>
 * <pre>
 *   root   → 世界根目录下的散文件（level.dat / levelname.txt / world_icon.jpeg …）
 *   db     → db/ 下的 LevelDB 文件
 *   &lt;其它顶层目录名&gt; → 各自一个包（players / structures / resource_packs …）
 *   record → 世界记录 JSON，文件名 = &lt;slotId&gt;.json
 * </pre>
 *
 * <h3>版本降级</h3>
 * 客户端（网易 0.2.0.25445）能力值：{@code lastOpenedWithVersion=[1,1,3,50]}、
 * {@code StorageVersion=5}、{@code NetworkVersion=113}。
 * 世界比它新的话，游戏会报 "更新版本的该游戏保存了这一等级" 而拒绝加载；
 * 本类可以原地把这三个字段改到客户端支持的档位（只动 4/4/4 个字节）。
 */
public final class WorldImportPrep {

    /** 客户端能力值（从客户端自建世界 + .so 里读出来的，见 README 8.3 / 实测发现 14）。 */
    public static final int[] CLIENT_VERSION = {1, 1, 3, 50};
    public static final int CLIENT_STORAGE = 5;
    public static final int CLIENT_NETWORK = 113;

    /** 可用的导入槽位数量（H5 会按顺序探测）。 */
    public static final int SLOTS = 9;

    private WorldImportPrep() {
    }

    /** 一个待写入 Download 的包。 */
    public static final class Part {
        /** 目标子目录后缀：{@code "root"} 表示世界根；{@code "db"} 表示 db 子目录。 */
        public final String suffix;
        /** 包文件名里用的后缀（与 suffix 相同）。 */
        public final byte[] data;

        Part(String suffix, byte[] data) {
            this.suffix = suffix;
            this.data = data;
        }
    }

    /** 处理结果。 */
    public static final class Result {
        public String levelName = "导入的世界";
        public String worldPrefix = "";              // 世界里那层外壳目录
        public final List<Part> parts = new ArrayList<Part>();
        public byte[] recordZip;
        public final LevelDat.Info before = new LevelDat.Info();
        public int patchedBytes = -1;                // -1 = 没做降级
        public int files;
        public long bytes;
        public String warning;                       // 非致命提示

        public LevelDat.Info after;
    }

    // ------------------------------------------------------------------ 主流程

    /**
     * @param src       源 .mcworld / 世界 zip
     * @param slotId    槽位 ID（同时是世界目录名与记录文件名），例如 {@code mcw1}
     * @param downgrade 是否把版本字段降到客户端支持的档位
     */
    public static Result prepare(File src, String slotId, boolean downgrade) throws IOException {
        Result r = new Result();

        ZipFile z = new ZipFile(src);
        try {
            // 1) 找世界根：最浅的那个 level.dat 所在目录
            String prefix = null;
            List<String> names = new ArrayList<String>();
            Map<String, ZipEntry> byName = new LinkedHashMap<String, ZipEntry>();
            for (ZipEntry e : Collections.list(z.entries())) {
                if (e.isDirectory()) continue;
                String n = norm(e.getName());
                if (n.isEmpty()) continue;
                names.add(n);
                byName.put(n, e);
                if (baseName(n).equalsIgnoreCase("level.dat")) {
                    String dir = parentOf(n);
                    if (prefix == null || dir.length() < prefix.length()) prefix = dir;
                }
            }
            if (prefix == null) {
                throw new IllegalArgumentException(
                        "这个文件里没有 level.dat，不是基岩版世界存档（.mcworld / 世界 zip）");
            }
            r.worldPrefix = prefix;

            // 2) 读 level.dat，顺便体检版本
            //    注意用 getInputStream 而不是 ZipFile.read(ZipEntry) ——
            //    后者只有 OpenJDK 有，Android 的 libcore 里没有。
            ZipEntry levelDat = byName.get(prefix + "level.dat");
            if (levelDat == null) {
                throw new IllegalArgumentException("世界包里找不到 level.dat");
            }
            byte[] rootLevelDat = ApkPatcher.readAll(z.getInputStream(levelDat));
            LevelDat.Info info = LevelDat.read(rootLevelDat);
            copyInto(r.before, info);
            if (!info.nbtOk) {
                r.warning = "level.dat 解析不了（" + info.error + "），跳过版本体检";
            } else if (info.compareVersion(CLIENT_VERSION) > 0
                    || (info.storageVersion != null && info.storageVersion > CLIENT_STORAGE)) {
                if (downgrade) {
                    byte[] patched = new byte[rootLevelDat.length];
                    System.arraycopy(rootLevelDat, 0, patched, 0, rootLevelDat.length);
                    r.patchedBytes = LevelDat.patch(patched, info, CLIENT_VERSION,
                            CLIENT_STORAGE, CLIENT_NETWORK);
                    rootLevelDat = patched;
                    r.after = LevelDat.read(patched);
                } else {
                    r.warning = "这个世界比客户端新（" + info.versionString()
                            + " / StorageVersion " + info.storageVersion
                            + "），直接导入游戏会拒绝加载，建议勾选「自动降级」";
                }
            }

            // 3) 世界名：优先 levelname.txt
            String name = null;
            ZipEntry ln = byName.get(prefix + "levelname.txt");
            if (ln != null) {
                byte[] nb = ApkPatcher.readAll(z.getInputStream(ln));
                String s = new String(nb, java.nio.charset.StandardCharsets.UTF_8).trim();
                if (!s.isEmpty()) name = s;
            }
            if (name == null && info.levelName != null && !info.levelName.trim().isEmpty()) {
                name = info.levelName.trim();
            }
            if (name == null) name = stripExt(src.getName());
            r.levelName = name;

            // 4) 按顶层目录分组
            Map<String, Map<String, byte[]>> groups = new LinkedHashMap<String, Map<String, byte[]>>();
            groups.put("root", new LinkedHashMap<String, byte[]>());
            for (String n : names) {
                if (!n.startsWith(prefix)) continue;          // 世界根之外的东西丢掉
                String rel = n.substring(prefix.length());
                if (rel.isEmpty()) continue;
                if (rel.contains("../")) throw new IllegalArgumentException("世界包里有非法路径: " + rel);
                byte[] data = ApkPatcher.readAll(z.getInputStream(byName.get(n)));
                if (rel.equals("level.dat") || rel.equals("level.dat_old")) {
                    data = rootLevelDat;                       // 用（可能已降级的）版本
                }
                int slash = rel.indexOf('/');
                if (slash < 0) {
                    groups.get("root").put(rel, data);
                } else {
                    String top = rel.substring(0, slash);
                    String inner = rel.substring(slash + 1);
                    if (inner.isEmpty()) continue;
                    Map<String, byte[]> g = groups.get(top);
                    if (g == null) {
                        g = new LinkedHashMap<String, byte[]>();
                        groups.put(top, g);
                    }
                    g.put(inner, data);
                }
            }
            // db 必须排在其他分组之前（先建目录），其实顺序无所谓；这里固定一下顺序更可读
            List<String> order = new ArrayList<String>();
            order.add("root");
            if (groups.containsKey("db")) order.add("db");
            for (String k : groups.keySet()) if (!order.contains(k)) order.add(k);

            for (String top : order) {
                Map<String, byte[]> g = groups.get(top);
                if (g == null || g.isEmpty()) continue;
                r.parts.add(new Part(top, zipOf(g)));
                r.files += g.size();
                for (byte[] b : g.values()) r.bytes += b.length;
            }

            // 5) 世界记录
            r.recordZip = zipOf(Collections.singletonMap(slotId + ".json", recordJson(slotId, name)));
            return r;
        } finally {
            try {
                z.close();
            } catch (IOException ignored) {
            }
        }
    }

    /** 世界记录 JSON —— 字段与客户端自己写的一致（不写 game_type，模块会自己从 level.dat 补）。 */
    public static byte[] recordJson(String slotId, String name) {
        long now = System.currentTimeMillis() / 1000L;
        String s = "{\"second_type\": -1, \"is_local\": true, \"is_copy\": false, "
                + "\"name\": \"" + LevelDat.jsonEscape(name) + "\", "
                + "\"level_id\": \"" + LevelDat.jsonEscape(slotId) + "\", "
                + "\"resource_packs\": {}, "
                + "\"user_ids\": {\"\": " + now + "}, "
                + "\"version\": 0, \"item_id\": \"-100\", "
                + "\"path\": \"" + LevelDat.jsonEscape(slotId) + "\", "
                + "\"addons\": {}, \"icon\": \"\"}";
        return s.getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    /** 打包成 zip（DEFLATED 级别 1：世界包可能很大，压太狠不划算）。 */
    static byte[] zipOf(Map<String, byte[]> files) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream(1 << 16);
        ZipOutputStream zo = new ZipOutputStream(bos);
        zo.setLevel(files.size() <= 4 ? 9 : 1);
        try {
            for (Map.Entry<String, byte[]> e : files.entrySet()) {
                String n = norm(e.getKey());
                if (n.isEmpty() || n.endsWith("/")) continue;
                zo.putNextEntry(new ZipEntry(n));
                zo.write(e.getValue());
                zo.closeEntry();
            }
        } finally {
            zo.close();
        }
        return bos.toByteArray();
    }

    // ------------------------------------------------------------------ 辅助

    static String norm(String n) {
        return n.replace('\\', '/');
    }

    static String baseName(String n) {
        int i = n.lastIndexOf('/');
        return i < 0 ? n : n.substring(i + 1);
    }

    static String parentOf(String n) {
        int i = n.lastIndexOf('/');
        return i < 0 ? "" : n.substring(0, i + 1);
    }

    static String stripExt(String n) {
        int i = n.lastIndexOf('.');
        return i <= 0 ? n : n.substring(0, i);
    }

    private static void copyInto(LevelDat.Info dst, LevelDat.Info src) {
        dst.lastOpenedWithVersion = src.lastOpenedWithVersion;
        dst.storageVersion = src.storageVersion;
        dst.networkVersion = src.networkVersion;
        dst.levelName = src.levelName;
        dst.nbtOk = src.nbtOk;
        dst.error = src.error;
        dst.plainNbt = src.plainNbt;
        dst.compressed = src.compressed;
    }

    /** 供界面显示：一行版本描述。 */
    public static String describe(LevelDat.Info i) {
        if (i == null) return "(未知)";
        if (!i.nbtOk) return "解析失败：" + i.error;
        return "版本 " + i.versionString()
                + " / StorageVersion " + i.storageVersion
                + " / NetworkVersion " + i.networkVersion;
    }

    /** 客户端能力值描述。 */
    public static String clientDesc() {
        return "1.1.3.50 / StorageVersion " + CLIENT_STORAGE + " / NetworkVersion " + CLIENT_NETWORK;
    }

    /** 读一个 zip 里的某个条目（调试用）。 */
    static byte[] readEntry(File zip, String name) throws IOException {
        ZipFile z = new ZipFile(zip);
        try {
            ZipEntry e = z.getEntry(name);
            if (e == null) return null;
            InputStream in = z.getInputStream(e);
            try {
                return ApkPatcher.readAll(in);
            } finally {
                in.close();
            }
        } finally {
            z.close();
        }
    }
}
