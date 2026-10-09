package com.mctool.mcpatch.core;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Locale;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * 基岩版世界包（{@code .mcworld} / 世界 zip）的结构体检与展平。
 *
 * <h3>为什么需要它</h3>
 * 游戏收到文件后，是把它<b>原样解压</b>到自己新建的世界目录里的：
 * <pre>
 *   minecraftWorlds/&lt;游戏生成的ID&gt;/&lt;zip 里的内容&gt;
 * </pre>
 * 所以 <b>{@code level.dat} 必须位于 zip 的根目录</b>，否则结果会变成
 * {@code minecraftWorlds/<ID>/WorldName/level.dat} —— 多一层，游戏就认不出来，
 * 表现是"导入进度条走完了，但世界里什么都没有"。
 *
 * <p>实测踩过：一个多套了一层文件夹的世界 zip，导入后目录成了
 * {@code minecraftWorlds/qPIFAOQgAkkA=/+OYCABpnCQA=/level.dat}，游戏完全读不到。
 *
 * <h3>做法</h3>
 * 找到最浅的那个 {@code level.dat}，把它的父目录当作"世界根"，
 * 重打一个把该前缀剥掉的 zip；顺带丢掉世界根之外的东西
 * （{@code __MACOSX/}、说明文件之类）。
 */
public final class WorldPackNormalizer {

    public static final String LEVEL_DAT = "level.dat";
    public static final String MANIFEST = "manifest.json";

    private WorldPackNormalizer() {
    }

    /** 结构体检结果。 */
    public static final class Info {
        /** 找到 level.dat（是标准基岩版世界）。 */
        public boolean hasLevelDat;
        /** 找到 manifest.json（是资源/行为包）。 */
        public boolean hasManifest;
        /**
         * 世界根目录前缀，形如 {@code ""} / {@code "MyWorld/"} / {@code "A/B/"}。
         * 没找到 level.dat 时为空串。
         */
        public String worldPrefix = "";
        /** 根层（前缀之外）的其它文件数量，用于提示"会丢掉什么"。 */
        public int outsideEntries;
        public int entries;
        public String error;

        /** 需要展平吗（level.dat 不在根目录）。 */
        public boolean needsFlatten() {
            return hasLevelDat && worldPrefix != null && !worldPrefix.isEmpty();
        }
    }

    private static String norm(String n) {
        return n.replace('\\', '/');
    }

    private static String basename(String n) {
        int i = n.lastIndexOf('/');
        return i < 0 ? n : n.substring(i + 1);
    }

    private static String parentOf(String n) {
        int i = n.lastIndexOf('/');
        return i < 0 ? "" : n.substring(0, i + 1);
    }

    /** 扫一遍 zip，判断它是什么、level.dat 埋在第几层。 */
    public static Info inspect(File zip) {
        Info info = new Info();
        // 用局部变量找「最浅的 level.dat 所在目录」。
        // 注意不能直接拿 info.worldPrefix 来比较 —— 它的初值是空串，
        // 会让 "dir.length() < worldPrefix.length()" 永远不成立。
        String best = null;
        ZipFile z = null;
        try {
            z = new ZipFile(zip);
            java.util.Enumeration<? extends ZipEntry> en = z.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                if (e.isDirectory()) continue;
                String n = norm(e.getName());
                if (n.isEmpty()) continue;
                info.entries++;
                String base = basename(n).toLowerCase(Locale.ROOT);
                if (base.equals(LEVEL_DAT)) {
                    info.hasLevelDat = true;
                    String dir = parentOf(n);
                    if (best == null || dir.length() < best.length()) best = dir;
                } else if (base.equals(MANIFEST)) {
                    info.hasManifest = true;
                }
            }
        } catch (Throwable t) {
            info.error = String.valueOf(t.getMessage());
        } finally {
            if (z != null) {
                try {
                    z.close();
                } catch (IOException ignored) {
                }
            }
        }
        info.worldPrefix = best == null ? "" : best;
        return info;
    }

    /**
     * 决定交给游戏时用什么文件名。
     *
     * <p>游戏是<b>按扩展名</b>判类型的（native 里认 {@code mcworld / mcpack /
     * mctemplate / mcaddon}），所以这里按内容把扩展名摆正：
     * <ul>
     *   <li>里面是标准基岩版世界 → {@code .mcworld}</li>
     *   <li>里面有 manifest.json → {@code .mcpack}</li>
     *   <li>都看不出来时保留原扩展名；原扩展名也不认识就按世界兜底</li>
     * </ul>
     */
    public static String decideName(Info info, String originalName) {
        String name = originalName == null || originalName.isEmpty() ? "import" : originalName;
        String lower = name.toLowerCase(Locale.ROOT);
        String base = name;
        for (String ext : new String[]{".mcworld", ".mctemplate", ".mcaddon", ".mcpack", ".zip"}) {
            if (lower.endsWith(ext)) {
                base = name.substring(0, name.length() - ext.length());
                break;
            }
        }
        if (info != null && info.hasLevelDat) return base + ".mcworld";
        if (info != null && info.hasManifest) return base + ".mcpack";
        for (String ext : new String[]{".mcworld", ".mctemplate", ".mcaddon", ".mcpack"}) {
            if (lower.endsWith(ext)) return name;      // 已经认识，别动
        }
        return base + ".mcworld";                      // 兜底：这个功能是「导入存档」
    }

    /**
     * 把 {@code prefix} 剥掉重打一份 zip，让 {@code level.dat} 落在根目录。
     *
     * @param prefix 世界根前缀（{@link Info#worldPrefix}），为空时原样复制
     * @return 实际写入的条目数
     */
    public static int flatten(File src, File dst, String prefix) throws IOException {
        String pre = prefix == null ? "" : prefix;
        ZipInputStream in = new ZipInputStream(
                new BufferedInputStream(new FileInputStream(src), 1 << 16));
        ZipOutputStream out = new ZipOutputStream(
                new BufferedOutputStream(new FileOutputStream(dst), 1 << 16));
        int written = 0;
        try {
            ZipEntry e;
            while ((e = in.getNextEntry()) != null) {
                if (e.isDirectory()) continue;
                String n = norm(e.getName());
                if (n.isEmpty()) continue;
                if (!pre.isEmpty()) {
                    if (!n.startsWith(pre)) continue;          // 世界根之外的丢掉
                    n = n.substring(pre.length());
                    if (n.isEmpty()) continue;
                }
                if (n.contains("..")) {
                    throw new IOException("世界包里有非法路径: " + n);
                }
                out.putNextEntry(new ZipEntry(n));
                byte[] buf = new byte[1 << 16];
                int k;
                while ((k = in.read(buf)) > 0) out.write(buf, 0, k);
                out.closeEntry();
                written++;
            }
        } finally {
            try {
                out.close();
            } catch (IOException ignored) {
            }
            try {
                in.close();
            } catch (IOException ignored) {
            }
        }
        return written;
    }
}
