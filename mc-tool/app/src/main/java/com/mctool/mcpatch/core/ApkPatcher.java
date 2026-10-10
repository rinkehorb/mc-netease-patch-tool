package com.mctool.mcpatch.core;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * 网易《我的世界》APK 一键修改器 —— 核心逻辑（纯 Java，可在桌面 JVM 上跑同一份代码做验证）。
 *
 * <h3>改哪些文件（全部来自 v19 实测可行的位置）</h3>
 * <ul>
 *   <li><b>玩家名称</b>：{@code assets/resource_packs/vanilla/texts/zh_CN.lang} 与 {@code en_US.lang}
 *       里的 {@code skin.name.alex / skin.name.steve / skin.name.dummy}。
 *       这个网易版本就是拿「皮肤显示名」当本地玩家名用的，v19 改的就是它。</li>
 *   <li><b>皮肤</b>：{@code assets/resource_packs/skins/skinpacks/Base/} 下的
 *       {@code alex.png / alex_dev.png / steve.png / steve_dev.png}（原包四个都是 64x64）。
 *       只改 {@code alex*} 就能生效（v19 就是只改了这两个），这里把 {@code steve*} 一起改掉，
 *       免得将来因为默认槽位变化而失效。</li>
 *   <li><b>细/粗手臂</b>：{@code .../Base/skindefs.json} 里各皮肤的
 *       {@code geometry.humanoid.customSlim}（细/Alex）与 {@code geometry.humanoid.custom}（粗/Steve）。</li>
 *   <li><b>资源包</b>：把包的整个目录树覆盖进 {@code assets/resource_packs/vanilla/}。
 *       为什么是覆盖 vanilla：APK 里<b>没有</b>任何资源包注册表（没有 valid_known_packs.json /
 *       resource_packs.json），全局资源包是运行时记在数据目录里的，改包无法登记新包；
 *       而 vanilla 永远处于激活状态，覆盖它等价于「这个包一直挂在最上层」，
 *       这也正是基岩版本身的覆盖语义。<br>
 *       例外：包自己的 {@code manifest.json} / {@code pack_icon.png} 不覆盖（那是包元数据，
 *       盖掉 vanilla 的会让游戏认不出这个内置包）；{@code texts/*.lang} 采用<b>追加合并</b>，
 *       避免包只带半份语言文件时把游戏 UI 文案弄坏。</li>
 * </ul>
 *
 * <h3>刻意不做的事</h3>
 * <ul>
 *   <li>不动 {@code classes.dex}（v19 的 smali 补丁原样保留）</li>
 *   <li>不重编译 {@code resources.arsc} / {@code AndroidManifest.xml}（apktool 重打包会改坏资源 ID，
 *       这是 v19 说明里明确踩过的坑），二者逐字节原样搬运</li>
 *   <li>不动 {@code lib/**}（含 30 MB 的 libminecraftpe.so）</li>
 * </ul>
 */
public final class ApkPatcher {

    // ------------------------------------------------------------------ 路径常量

    public static final String VANILLA_PREFIX = "assets/resource_packs/vanilla/";
    public static final String BASE_PREFIX = "assets/resource_packs/skins/skinpacks/Base/";

    public static final String P_SKINDEFS = BASE_PREFIX + "skindefs.json";

    public static final String[] P_SKIN_PNGS = {
            BASE_PREFIX + "alex.png",
            BASE_PREFIX + "alex_dev.png",
            BASE_PREFIX + "steve.png",
            BASE_PREFIX + "steve_dev.png",
    };

    public static final String P_LANG_ZH = VANILLA_PREFIX + "texts/zh_CN.lang";
    public static final String P_LANG_EN = VANILLA_PREFIX + "texts/en_US.lang";
    public static final String[] P_LANGS = {P_LANG_ZH, P_LANG_EN};

    /** 游戏 H5 启动器的首页 —— 世界列表就在这个网页里。 */
    public static final String P_WEB_INDEX = "assets/web/index.html";
    /** 导入界面的幂等标记（注入过就不再注入）。 */
    public static final String IMPORT_MARK = "__MCIMPORT__";

    /** 换签名时必然失效的旧签名文件，先剔掉，免得和 apksig 新写的打架。 */
    private static final String[] OLD_SIG_SUFFIX = {".SF", ".RSA", ".DSA", ".EC"};

    private ApkPatcher() {
    }

    // ------------------------------------------------------------------ 主流程

    public static Result patch(PatchSpec spec, PatchLog log) throws Exception {
        spec.validate();
        long t0 = System.currentTimeMillis();

        File unsigned = new File(spec.dstApk.getParentFile(),
                spec.dstApk.getName() + ".unsigned.tmp");

        Result result = new Result();

        log.stage("检查源 APK…");
        ZipFile zin = new ZipFile(spec.srcApk);
        try {
            if (zin.getEntry(P_SKINDEFS) == null) {
                throw new IllegalArgumentException(
                        "这个 APK 里找不到 " + P_SKINDEFS + "\n"
                                + "看起来不是网易《我的世界》的包（或者已经被别的工具拆坏过）。");
            }

            Map<String, byte[]> repl = new LinkedHashMap<String, byte[]>();      // 优先级最高
            Map<String, byte[]> packNew = new LinkedHashMap<String, byte[]>();   // 资源包覆盖展开期

            // ---------- 1. 资源包 ----------
            byte[] langZh = readOrNull(zin, P_LANG_ZH);
            byte[] langEn = readOrNull(zin, P_LANG_EN);

            if (spec.packEnabled) {
                int count = 0;
                final int total = spec.resourcePacks.size();
                for (int i = 0; i < total; i++) {
                    File pf = spec.resourcePacks.get(i);
                    log.stage(total == 1 ? "解析资源包…" : ("解析资源包 " + (i + 1) + "/" + total + "…"));
                    Map<String, byte[]> newRaw = new LinkedHashMap<String, byte[]>();
                    Map<String, byte[]> newLang = new LinkedHashMap<String, byte[]>();
                    count += ZipFileUtil.collectResourcePack(pf, newRaw, newLang, log);
                    log.detail(pf.getName() + " → " + newRaw.size() + " 个文件"
                            + (newLang.isEmpty() ? "" : " + " + newLang.size() + " 份语言"));

                    // texts/*.lang 按包顺序依次「追加合并」，
                    // 基岩版 lang 是后出现的键覆盖先出现的，所以后面的包翻译优先。
                    if (newLang.containsKey(P_LANG_ZH) && langZh != null) {
                        langZh = LangPatcher.appendLines(langZh, newLang.remove(P_LANG_ZH));
                    }
                    if (newLang.containsKey(P_LANG_EN) && langEn != null) {
                        langEn = LangPatcher.appendLines(langEn, newLang.remove(P_LANG_EN));
                    }
                    // 包里有、vanilla 里没有的 lang 当普通新文件
                    packNew.putAll(newLang);
                    // 后面的包覆盖前面同名文件
                    packNew.putAll(newRaw);
                }
                log.detail("叠加后合计 " + count + " 个文件");
                result.resourcePackFiles = packNew.size();
            }

            // ---------- 2. 改名（优先级高于资源包带来的 lang） ----------
            if (spec.renameEnabled) {
                String name = spec.playerName.trim();
                log.stage("写入玩家名称：" + name);
                if (langZh != null) langZh = LangPatcher.renamePlayer(langZh, name);
                if (langEn != null) langEn = LangPatcher.renamePlayer(langEn, name);
                if (langZh == null && langEn == null) {
                    throw new IllegalStateException("源 APK 里没有找到任何 texts/*.lang，无法改名");
                }
            }
            if (langZh != null) repl.put(P_LANG_ZH, langZh);
            if (langEn != null) repl.put(P_LANG_EN, langEn);

            // ---------- 3. 皮肤 + 手臂 ----------
            if (spec.skinEnabled) {
                log.stage("写入皮肤（" + (spec.slimArms ? "细手臂 / Alex" : "粗手臂 / Steve") + "）…");
                for (String p : P_SKIN_PNGS) {
                    if (zin.getEntry(p) != null) repl.put(p, spec.skinPng);
                }
                byte[] defs = readOrNull(zin, P_SKINDEFS);
                if (defs != null) repl.put(P_SKINDEFS, SkindefsPatcher.applyArms(defs, spec.slimArms));
                result.skinFiles = P_SKIN_PNGS.length;
            }

            // ---------- 4. 世界导入界面（注入 H5 首页） ----------
            if (spec.importScript != null && spec.importScript.length > 0) {
                byte[] html = readOrNull(zin, P_WEB_INDEX);
                if (html == null) {
                    log.detail("源包里没有 " + P_WEB_INDEX + "，跳过导入界面注入");
                } else {
                    byte[] injected = injectImportUi(html, spec.importScript);
                    if (injected == html) {
                        log.detail("H5 首页里已经有导入界面了，跳过");
                    } else {
                        log.stage("注入世界导入界面（" + P_WEB_INDEX + "）…");
                        repl.put(P_WEB_INDEX, injected);
                        result.importUiInjected = true;
                    }
                }
            }

            // ---------- 5. 重写 zip ----------
            log.stage("重打包 APK…");
            if (unsigned.exists() && !unsigned.delete()) {
                throw new IOException("无法删除旧的临时文件: " + unsigned);
            }
            RawZipWriter w = new RawZipWriter(unsigned);
            try {
                List<? extends ZipEntry> entries = Collections.list(zin.entries());
                int total = entries.size();
                int done = 0;
                long nextTick = 0;
                for (ZipEntry e : entries) {
                    String name = e.getName();
                    if (e.isDirectory()) continue;
                    if (isOldSignature(name)) continue;

                    byte[] r = repl.remove(name);
                    if (r != null) {
                        w.addDeflated(name, r);
                        result.replaced++;
                    } else {
                        byte[] pr = packNew.remove(name);
                        if (pr != null) {
                            w.addDeflated(name, pr);
                            result.replaced++;
                        } else if (e.getMethod() == ZipEntry.STORED) {
                            w.addStored(name, e.getCrc(), e.getSize(), zin.getInputStream(e));
                            result.copiedStored++;
                        } else {
                            w.addDeflated(name, zin.getInputStream(e));
                            result.copiedDeflated++;
                        }
                    }
                    done++;
                    if (System.currentTimeMillis() >= nextTick) {
                        nextTick = System.currentTimeMillis() + 250;
                        log.progress(total == 0 ? 1.0 : (double) done / total * 0.85);
                    }
                }

                // 源包里没有的（新语言文件、资源包新增文件）
                for (Map.Entry<String, byte[]> en : repl.entrySet()) {
                    w.addDeflated(en.getKey(), en.getValue());
                    result.added++;
                }
                for (Map.Entry<String, byte[]> en : packNew.entrySet()) {
                    w.addDeflated(en.getKey(), en.getValue());
                    result.added++;
                }
                w.finish();
                result.zipEntries = w.entryCount();
            } catch (Throwable t) {
                try {
                    w.close();
                } catch (Throwable ignored) {
                }
                throw t;
            }
        } finally {
            try {
                zin.close();
            } catch (IOException ignored) {
            }
        }

        // ---------- 5. 签名 ----------
        try {
            log.stage("签名（v1 + v2 + v3）…");
            log.progress(0.9);
            if (spec.dstApk.exists() && !spec.dstApk.delete()) {
                throw new IOException("无法覆盖已存在的输出文件: " + spec.dstApk);
            }
            ApkSignerHelper.sign(spec, unsigned, spec.dstApk);
            result.signed = true;
        } finally {
            if (unsigned.exists()) {
                //noinspection ResultOfMethodCallIgnored
                unsigned.delete();
            }
        }

        log.progress(1.0);
        result.millis = System.currentTimeMillis() - t0;
        result.outSize = spec.dstApk.length();
        result.srcSize = spec.srcApk.length();
        log.stage("完成");
        return result;
    }

    // ------------------------------------------------------------------ 辅助

    /**
     * 把导入界面的 JS 注入 H5 首页。
     *
     * <p>插在最后一个 {@code </body>}（或 {@code </html>}）之前 ——
     * 实测这个位置可行：游戏启动时会把 {@code assets/web/} 整个解压到数据目录的
     * {@code web/} 下再从那里加载，所以改 APK 里的这份就够。
     *
     * <p><b>会先摘掉旧的再插新的</b>（不是"看到标记就跳过"）。
     * 这一点很重要：源 APK 可能是<b>别人以前改过的包</b>，里面已经带着旧版导入脚本，
     * 如果这里跳过，产出包就会继续带旧脚本 —— 而新工具写的是 {@code .png}、
     * 旧脚本找的是 {@code .zip}，结果就是游戏里一直报"没有找到待导入的包"。
     * （真机上就这么踩过一次，排查了半天。）
     *
     * @return 新的 HTML；和原来完全一样（说明本来就是这个版本）时返回<b>同一个数组引用</b>
     */
    public static byte[] injectImportUi(byte[] html, byte[] js) {
        String original = new String(html, java.nio.charset.StandardCharsets.UTF_8);
        String s = stripImportUi(original);
        int idx = s.lastIndexOf("</body>");
        if (idx < 0) idx = s.lastIndexOf("</html>");
        if (idx < 0) idx = s.length();
        String block = "\n<script>\n" + new String(js, java.nio.charset.StandardCharsets.UTF_8)
                + "\n</script>\n";
        String out = s.substring(0, idx) + block + s.substring(idx);
        if (out.equals(original)) return html;
        return out.getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    /**
     * 把已经注入过的导入界面脚本摘掉（连同它前后的换行）。
     * 没注入过就原样返回。用标记定位，不要求 HTML 结构规范。
     */
    static String stripImportUi(String s) {
        int mark = s.indexOf(IMPORT_MARK);
        int guard = 0;
        while (mark >= 0 && guard++ < 10) {
            int open = s.lastIndexOf("<script", mark);
            int close = s.indexOf("</script>", mark);
            if (open < 0 || close < 0) break;
            close += "</script>".length();
            int a = open, b = close;
            // 前后各自的换行都要吃掉，否则"摘掉再插回去"会多出/少掉一个换行，
            // 同一个版本重复注入就不再是幂等的（单元测试抓过这个）。
            while (a > 0 && (s.charAt(a - 1) == '\n' || s.charAt(a - 1) == '\r')) a--;
            while (b < s.length() && (s.charAt(b) == '\n' || s.charAt(b) == '\r')) b++;
            s = s.substring(0, a) + s.substring(b);
            mark = s.indexOf(IMPORT_MARK);
        }
        return s;
    }

    private static boolean isOldSignature(String name) {
        if (!name.startsWith("META-INF/")) return false;
        String upper = name.toUpperCase(Locale.ROOT);
        if (upper.equals("META-INF/MANIFEST.MF")) return true;
        for (String s : OLD_SIG_SUFFIX) {
            if (upper.endsWith(s)) return true;
        }
        return false;
    }

    static byte[] readOrNull(ZipFile z, String name) throws IOException {
        ZipEntry e = z.getEntry(name);
        if (e == null) return null;
        InputStream in = z.getInputStream(e);
        try {
            return readAll(in);
        } finally {
            in.close();
        }
    }

    public static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream(1 << 16);
        byte[] buf = new byte[1 << 16];
        int n;
        while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
        return bos.toByteArray();
    }

    public static byte[] readFile(File f) throws IOException {
        FileInputStream in = new FileInputStream(f);
        try {
            return readAll(in);
        } finally {
            in.close();
        }
    }

    /** PNG 尺寸校验（只读 IHDR，不需要图片库，桌面/安卓都能跑）。 */
    public static int[] pngSize(byte[] png) {
        if (png == null || png.length < 24) return null;
        if ((png[0] & 0xFF) != 0x89 || png[1] != 'P' || png[2] != 'N' || png[3] != 'G') return null;
        int w = ((png[16] & 0xFF) << 24) | ((png[17] & 0xFF) << 16) | ((png[18] & 0xFF) << 8) | (png[19] & 0xFF);
        int h = ((png[20] & 0xFF) << 24) | ((png[21] & 0xFF) << 16) | ((png[22] & 0xFF) << 8) | (png[23] & 0xFF);
        return new int[]{w, h};
    }

    public static String describePng(byte[] png) {
        int[] s = pngSize(png);
        if (s == null) return "不是有效的 PNG";
        return s[0] + "x" + s[1];
    }

    // ------------------------------------------------------------------ 结果

    public static final class Result {
        public int replaced;
        public int added;
        public int copiedStored;
        public int copiedDeflated;
        public int zipEntries;
        public int skinFiles;
        public int resourcePackFiles;
        public boolean importUiInjected;
        public boolean signed;
        public long srcSize;
        public long outSize;
        public long millis;

        @Override
        public String toString() {
            return "替换 " + replaced + " 项 / 新增 " + added + " 项 / 原样搬运 "
                    + (copiedStored + copiedDeflated) + " 项，共 " + zipEntries + " 个条目"
                    + (signed ? "，已签名" : "，未签名");
        }
    }

    /** 小工具：把资源包 zip 展开成「目标路径 → 字节」。 */
    static final class ZipFileUtil {
        static int collectResourcePack(File pack, Map<String, byte[]> outNew,
                                       Map<String, byte[]> outLang, PatchLog log) throws IOException {
            ZipFile pz = new ZipFile(pack);
            try {
                List<? extends ZipEntry> list = Collections.list(pz.entries());
                // 兼容「外面套了一层文件夹」的资源包
                String manifest = null;
                for (ZipEntry e : list) {
                    String n = norm(e.getName());
                    if (n.toLowerCase(Locale.ROOT).endsWith("manifest.json")) {
                        manifest = n;
                        break;
                    }
                }
                if (manifest == null) {
                    throw new IllegalArgumentException(
                            "资源包里没有 manifest.json，不是有效的基岩版资源包（.zip / .mcpack）");
                }
                int slash = manifest.lastIndexOf('/');
                String prefix = slash < 0 ? "" : manifest.substring(0, slash + 1);
                if (!prefix.isEmpty()) {
                    log.detail("资源包外层目录: " + prefix);
                }

                int count = 0;
                for (ZipEntry e : list) {
                    if (e.isDirectory()) continue;
                    String n = norm(e.getName());
                    if (!prefix.isEmpty()) {
                        if (!n.startsWith(prefix)) continue;
                        n = n.substring(prefix.length());
                    }
                    if (n.isEmpty()) continue;
                    String lower = n.toLowerCase(Locale.ROOT);
                    if (lower.equals("manifest.json") || lower.equals("pack_icon.png")
                            || lower.startsWith("meta-inf/")) {
                        continue;   // 包元数据，不能盖掉 vanilla 的
                    }
                    if (n.contains("../")) {
                        throw new IllegalArgumentException("资源包里有非法路径: " + n);
                    }
                    byte[] data = readAll(pz.getInputStream(e));
                    String target = VANILLA_PREFIX + n;
                    if (lower.startsWith("texts/") && lower.endsWith(".lang")) {
                        outLang.put(target, data);
                    } else {
                        outNew.put(target, data);
                    }
                    count++;
                }
                if (count == 0) {
                    throw new IllegalArgumentException("资源包里没有任何可用文件");
                }
                return count;
            } finally {
                pz.close();
            }
        }

        static String norm(String n) {
            return n.replace('\\', '/');
        }
    }

    /** 供外部自检用：列出所有会被本次补丁影响的路径。 */
    public static List<String> affectedPaths(PatchSpec spec) {
        List<String> l = new ArrayList<String>();
        if (spec.renameEnabled) l.addAll(Arrays.asList(P_LANGS));
        if (spec.skinEnabled) {
            l.addAll(Arrays.asList(P_SKIN_PNGS));
            l.add(P_SKINDEFS);
        }
        if (spec.packEnabled) l.add(VANILLA_PREFIX + "**（由 " + spec.resourcePacks.size() + " 个资源包覆盖）");
        if (spec.importScript != null && spec.importScript.length > 0) l.add(P_WEB_INDEX + "（注入导入界面）");
        return l;
    }
}
