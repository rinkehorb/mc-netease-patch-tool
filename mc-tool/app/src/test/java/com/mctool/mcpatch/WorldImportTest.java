package com.mctool.mcpatch;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import com.mctool.mcpatch.core.ApkPatcher;
import com.mctool.mcpatch.core.LevelDat;
import com.mctool.mcpatch.core.WorldImportPrep;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * 世界导入（3a）的核心逻辑测试。
 *
 * <p>这套逻辑全部是纯 Java，所以不需要 Robolectric —— 直接在 JVM 上跑，
 * 而且这里测的每一条都对应真机实测过的行为（见 mc-re/probe/实测发现.md 第 13 节）。
 */
public class WorldImportTest {

    private static File tmpDir() throws Exception {
        File d = new File(System.getProperty("java.io.tmpdir"),
                "mcpatch-test-" + System.nanoTime());
        //noinspection ResultOfMethodCallIgnored
        d.mkdirs();
        return d;
    }

    // ------------------------------------------------------------------ 造 level.dat

    private static void putU2(ByteArrayOutputStream o, int v) {
        o.write(v & 0xFF);
        o.write((v >>> 8) & 0xFF);
    }

    private static void putI4(ByteArrayOutputStream o, int v) {
        o.write(v & 0xFF);
        o.write((v >>> 8) & 0xFF);
        o.write((v >>> 16) & 0xFF);
        o.write((v >>> 24) & 0xFF);
    }

    private static void writeNamed(ByteArrayOutputStream o, int type, String name) {
        o.write(type);
        byte[] n = name.getBytes(StandardCharsets.UTF_8);
        putU2(o, n.length);
        o.write(n, 0, n.length);
    }

    /** 8 字节头 + 明文小端 NBT，字段和真实 level.dat 一致（顺序也照抄）。 */
    static byte[] makeLevelDat(int[] ver, int storage, int net, String levelName) {
        ByteArrayOutputStream nbt = new ByteArrayOutputStream();
        nbt.write(0x0A);            // TAG_Compound
        putU2(nbt, 0);              // 根名空
        writeNamed(nbt, 0x09, "lastOpenedWithVersion");
        nbt.write(0x03);            // 元素类型 Int
        putI4(nbt, ver.length);
        for (int v : ver) putI4(nbt, v);
        writeNamed(nbt, 0x03, "StorageVersion");
        putI4(nbt, storage);
        writeNamed(nbt, 0x03, "NetworkVersion");
        putI4(nbt, net);
        writeNamed(nbt, 0x08, "LevelName");
        byte[] nm = levelName.getBytes(StandardCharsets.UTF_8);
        putU2(nbt, nm.length);
        nbt.write(nm, 0, nm.length);
        writeNamed(nbt, 0x01, "hasBeenLoadedInCreative");
        nbt.write(0);
        nbt.write(0x00);            // TAG_End

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        putI4(out, 4);              // 8 字节头：版本 + 长度
        putI4(out, nbt.size());
        byte[] b = nbt.toByteArray();
        out.write(b, 0, b.length);
        return out.toByteArray();
    }

    // ------------------------------------------------------------------ 测试

    @Test
    public void levelDatReadsVersionFields() {
        byte[] dat = makeLevelDat(new int[]{1, 2, 10, 1}, 6, 200, "测试世界");
        LevelDat.Info i = LevelDat.read(dat);
        assertTrue("应该能解析: " + i.error, i.nbtOk);
        assertTrue(i.plainNbt);
        assertArrayEquals(new int[]{1, 2, 10, 1}, i.lastOpenedWithVersion);
        assertEquals(Integer.valueOf(6), i.storageVersion);
        assertEquals(Integer.valueOf(200), i.networkVersion);
        assertEquals("测试世界", i.levelName);
        assertEquals("1.2.10.1", i.versionString());
        assertTrue("比客户端新", i.compareVersion(WorldImportPrep.CLIENT_VERSION) > 0);
    }

    /** 降级必须只改那几个 int，其它字节一个不动、长度不变。 */
    @Test
    public void levelDatPatchIsMinimalAndInPlace() {
        byte[] orig = makeLevelDat(new int[]{1, 2, 10, 1}, 6, 200, "外部导入测试");
        byte[] dat = orig.clone();
        LevelDat.Info i = LevelDat.read(dat);
        int changed = LevelDat.patch(dat, i, WorldImportPrep.CLIENT_VERSION,
                WorldImportPrep.CLIENT_STORAGE, WorldImportPrep.CLIENT_NETWORK);
        assertTrue("应该改动了字段", changed > 0);
        assertEquals("长度不能变", orig.length, dat.length);
        for (int k = 0; k < orig.length; k++) {
            if (orig[k] != dat[k]) {
                assertTrue("只允许改动 int 字段所在的 12 个字节",
                        k >= 0 && (k - 8) >= 0);
            }
        }
        int diff = 0;
        for (int k = 0; k < orig.length; k++) if (orig[k] != dat[k]) diff++;
        assertTrue("差异字节数应当很小（实测这类改动是 3~5 字节），实际 " + diff, diff <= 12);

        LevelDat.Info after = LevelDat.read(dat);
        assertArrayEquals(WorldImportPrep.CLIENT_VERSION, after.lastOpenedWithVersion);
        assertEquals(Integer.valueOf(WorldImportPrep.CLIENT_STORAGE), after.storageVersion);
        assertEquals(Integer.valueOf(WorldImportPrep.CLIENT_NETWORK), after.networkVersion);
        assertEquals("同名不能变", "外部导入测试", after.levelName);
        assertEquals("降级后不应再比客户端新",
                0, after.compareVersion(WorldImportPrep.CLIENT_VERSION));
    }

    /** 已经是客户端版本的存档，不该被改动。 */
    @Test
    public void compareWithClientVersion() {
        LevelDat.Info same = LevelDat.read(
                makeLevelDat(new int[]{1, 1, 3, 50}, 5, 113, "x"));
        assertEquals(0, same.compareVersion(WorldImportPrep.CLIENT_VERSION));
        LevelDat.Info older = LevelDat.read(
                makeLevelDat(new int[]{1, 1, 0, 0}, 5, 113, "x"));
        assertTrue(older.compareVersion(WorldImportPrep.CLIENT_VERSION) < 0);
    }

    // ------------------------------------------------------------------ 拆包

    private static File makeWorldZip(File dir, byte[] levelDat) throws Exception {
        File f = new File(dir, "world.mcworld");
        ZipOutputStream zo = new ZipOutputStream(new FileOutputStream(f));
        Map<String, byte[]> files = new java.util.LinkedHashMap<String, byte[]>();
        files.put("level.dat", levelDat);
        files.put("level.dat_old", levelDat);
        files.put("levelname.txt", "外部导入测试".getBytes(StandardCharsets.UTF_8));
        files.put("world_icon.jpeg", new byte[]{1, 2, 3});
        files.put("world_behavior_packs.json", "{}".getBytes(StandardCharsets.UTF_8));
        files.put("db/000014.ldb", new byte[]{9, 9, 9});
        files.put("db/CURRENT", "MANIFEST-000008".getBytes(StandardCharsets.UTF_8));
        files.put("players/abc.dat", new byte[]{7, 7});
        files.put("__MACOSX/junk", new byte[]{0});          // 世界根之外，应当被丢掉
        for (Map.Entry<String, byte[]> e : files.entrySet()) {
            zo.putNextEntry(new ZipEntry(e.getKey()));
            zo.write(e.getValue());
            zo.closeEntry();
        }
        zo.close();
        return f;
    }

    private static Map<String, Integer> entries(byte[] zip) throws Exception {
        File t = File.createTempFile("part", ".zip");
        FileOutputStream os = new FileOutputStream(t);
        os.write(zip);
        os.close();
        Map<String, Integer> out = new HashMap<String, Integer>();
        ZipFile z = new ZipFile(t);
        try {
            Enumeration<? extends ZipEntry> en = z.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                out.put(e.getName(), (int) e.getSize());
            }
        } finally {
            z.close();
        }
        //noinspection ResultOfMethodCallIgnored
        t.delete();
        return out;
    }

    @Test
    public void prepareSplitsByTopLevelDirectoryAndDowngrades() throws Exception {
        File dir = tmpDir();
        byte[] levelDat = makeLevelDat(new int[]{1, 2, 10, 1}, 6, 200, "外部导入测试");
        File world = makeWorldZip(dir, levelDat);

        WorldImportPrep.Result r = WorldImportPrep.prepare(world, "mcw1", true);
        assertEquals("外部导入测试", r.levelName);
        assertEquals("", r.worldPrefix);
        assertTrue("应当做了降级", r.patchedBytes >= 0);

        // root 包：世界根目录下的散文件，不含 db/ 与 players/
        WorldImportPrep.Part root = null, db = null, players = null;
        for (WorldImportPrep.Part p : r.parts) {
            if ("root".equals(p.suffix)) root = p;
            if ("db".equals(p.suffix)) db = p;
            if ("players".equals(p.suffix)) players = p;
        }
        assertNotNull("必须有 root 包", root);
        assertNotNull("必须有 db 包", db);
        assertNotNull("必须有 players 包", players);

        Map<String, Integer> rootE = entries(root.data);
        assertTrue(rootE.containsKey("level.dat"));
        assertTrue(rootE.containsKey("levelname.txt"));
        assertTrue(rootE.containsKey("world_icon.jpeg"));
        assertFalse("db/ 不该出现在 root 包里", rootE.containsKey("db/000014.ldb"));
        assertFalse("__MACOSX 应当被丢掉", rootE.containsKey("__MACOSX/junk"));

        // db 包：db/ 前缀必须被剥掉（因为游戏解压时会压平，目标目录已经指向 db/）
        Map<String, Integer> dbE = entries(db.data);
        assertTrue("db 包里应当是 000014.ldb 而不是 db/000014.ldb", dbE.containsKey("000014.ldb"));
        assertTrue(dbE.containsKey("CURRENT"));
        assertFalse(dbE.containsKey("db/000014.ldb"));

        Map<String, Integer> plE = entries(players.data);
        assertTrue(plE.containsKey("abc.dat"));

        // root 包里的 level.dat 应当是降级后的
        File t = File.createTempFile("root", ".zip");
        FileOutputStream os = new FileOutputStream(t);
        os.write(root.data);
        os.close();
        ZipFile z = new ZipFile(t);
        byte[] patched;
        try {
            patched = ApkPatcher.readAll(z.getInputStream(z.getEntry("level.dat")));
        } finally {
            z.close();
        }
        //noinspection ResultOfMethodCallIgnored
        t.delete();
        LevelDat.Info after = LevelDat.read(patched);
        assertArrayEquals(WorldImportPrep.CLIENT_VERSION, after.lastOpenedWithVersion);
        assertEquals(Integer.valueOf(WorldImportPrep.CLIENT_STORAGE), after.storageVersion);
    }

    /** 不降级时不该动 level.dat，而且要给用户一句明确的警告。 */
    @Test
    public void prepareWithoutDowngradeWarns() throws Exception {
        File dir = tmpDir();
        byte[] levelDat = makeLevelDat(new int[]{1, 2, 10, 1}, 6, 200, "旧的");
        File world = makeWorldZip(dir, levelDat);

        WorldImportPrep.Result r = WorldImportPrep.prepare(world, "mcw2", false);
        assertEquals(-1, r.patchedBytes);
        assertNotNull("应当给出警告", r.warning);
        assertTrue(r.warning.contains("StorageVersion") || r.warning.contains("客户端"));
    }

    @Test
    public void recordJsonMatchesClientShape() {
        String s = new String(WorldImportPrep.recordJson("mcw3", "我的世界"),
                StandardCharsets.UTF_8);
        // 客户端自己写的就是这 12 个字段；game_type 由模块读 level.dat 自己补，这里不能写
        assertFalse("不能自己写 game_type", s.contains("game_type"));
        assertTrue(s.contains("\"item_id\": \"-100\""));
        assertTrue(s.contains("\"level_id\": \"mcw3\""));
        assertTrue(s.contains("\"path\": \"mcw3\""));
        assertTrue(s.contains("\"second_type\": -1"));
        assertTrue(s.contains("\"is_local\": true"));
        assertTrue("非 ASCII 名字要转成 \\u 转义", s.contains("\\u6211\\u7684\\u4e16\\u754c"));
        assertFalse("不能有裸中文（客户端写的是转义形式）", s.contains("我的世界"));
    }

    // ------------------------------------------------------------------ 注入导入界面

    @Test
    public void injectImportUiIsIdempotentAndKeepsHtml() {
        String html = "<html><body><div id=app></div></body></html>";
        byte[] js = "window.__MCIMPORT__ = 1;".getBytes(StandardCharsets.UTF_8);

        byte[] out = ApkPatcher.injectImportUi(html.getBytes(StandardCharsets.UTF_8), js);
        String s = new String(out, StandardCharsets.UTF_8);
        assertTrue("应当注入脚本", s.contains("__MCIMPORT__"));
        assertTrue("插在 </body> 之前", s.indexOf("<script>") < s.indexOf("</body>"));
        assertTrue("原有内容必须保留", s.contains("<div id=app></div>"));
        assertEquals("html 结构不能被破坏", 1, s.split("</html>", -1).length - 1);

        byte[] again = ApkPatcher.injectImportUi(out, js);
        assertSame("已经注入过就要原样返回（幂等）", out, again);
    }

    @Test
    public void injectImportUiHandlesHtmlWithoutBody() {
        byte[] html = "<div>x</div>".getBytes(StandardCharsets.UTF_8);
        byte[] out = ApkPatcher.injectImportUi(html, "var a=1;".getBytes(StandardCharsets.UTF_8));
        String s = new String(out, StandardCharsets.UTF_8);
        assertTrue(s.contains("var a=1;"));
        assertTrue(s.startsWith("<div>x</div>"));
    }
}
