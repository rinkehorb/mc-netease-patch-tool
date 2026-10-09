package com.mctool.mcpatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import android.content.Context;
import android.net.Uri;

import com.mctool.mcpatch.core.WorldPackNormalizer;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 「导入存档」相关逻辑的测试。
 *
 * <p>这个功能没法在这里跑真机（要装了游戏才能验证 Intent 是否被接住），
 * 但其中两块<b>纯逻辑</b>是可以完整验证的，而且正好是最容易出错的两块：
 * <ul>
 *   <li>{@link ShareFileProvider} —— 交给游戏的那个 {@code content://} URI 能不能被解析、
 *       路径越权会不会被挡住（安全相关）；</li>
 *   <li>扩展名嗅探 —— {@code .zip} 到底该当成世界还是资源包。</li>
 * </ul>
 */
@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34)
public class SaveImportTest {

    private static Context ctx() {
        return RuntimeEnvironment.getApplication();
    }

    private static File writeFile(File dir, String name, byte[] data) throws Exception {
        File f = new File(dir, name);
        FileOutputStream os = new FileOutputStream(f);
        try {
            os.write(data);
        } finally {
            os.close();
        }
        return f;
    }

    /** 交给游戏的 content URI 必须能被 ContentResolver 正常打开，并且 MIME 正确。 */
    @Test
    public void providerServesImportFile() throws Exception {
        Context c = ctx();
        File dir = ShareFileProvider.dir(c, ShareFileProvider.KIND_IMPORT);
        byte[] payload = "this-is-a-fake-mcworld".getBytes("UTF-8");
        File f = writeFile(dir, "MyWorld.mcworld", payload);

        Uri uri = ShareFileProvider.uriFor(c, f);
        assertEquals("authority 应为 <包名>.files",
                c.getPackageName() + ShareFileProvider.AUTHORITY_SUFFIX, uri.getAuthority());
        assertEquals("最后一段应是原文件名（游戏要靠扩展名判类型）",
                "MyWorld.mcworld", uri.getLastPathSegment());
        assertEquals("路径应为 <kind>/<name>", 2, uri.getPathSegments().size());
        assertEquals(ShareFileProvider.KIND_IMPORT, uri.getPathSegments().get(0));

        assertEquals("application/octet-stream",
                c.getContentResolver().getType(uri));

        InputStream in = c.getContentResolver().openInputStream(uri);
        assertNotNull("应该能打开", in);
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] buf = new byte[256];
        int n;
        try {
            while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
        } finally {
            in.close();
        }
        assertEquals("内容应逐字节一致", new String(payload, "UTF-8"),
                new String(bos.toByteArray(), "UTF-8"));
    }

    /** 生成的 APK 也要能被同一个 provider 服务（安装流程依赖它）。 */
    @Test
    public void providerServesOutputApkWithApkMime() throws Exception {
        Context c = ctx();
        File dir = ShareFileProvider.dir(c, ShareFileProvider.KIND_OUTPUT);
        File f = writeFile(dir, "out-mod.apk", new byte[]{1, 2, 3});
        Uri uri = ShareFileProvider.uriFor(c, f);
        assertEquals("application/vnd.android.package-archive",
                c.getContentResolver().getType(uri));
        assertNotNull(c.getContentResolver().openInputStream(uri));
    }

    /** 越权与非法路径必须被挡住。 */
    @Test
    public void providerRejectsTraversalAndUnknownKind() {
        Context c = ctx();
        String auth = c.getPackageName() + ShareFileProvider.AUTHORITY_SUFFIX;

        // 1) 目录白名单之外
        try {
            c.getContentResolver().openInputStream(
                    Uri.parse("content://" + auth + "/evil/whatever.txt"));
            fail("不在白名单里的目录应当被拒绝");
        } catch (Exception expected) {
            assertTrue(expected.getMessage() + "", true);
        }

        // 2) 用 %2F 编码进来的路径穿越
        try {
            c.getContentResolver().openInputStream(
                    Uri.parse("content://" + auth + "/import/..%2F..%2Fsecret.txt"));
            fail("路径穿越应当被拒绝");
        } catch (Exception expected) {
            assertTrue(expected.getMessage() + "", true);
        }

        // 3) 段数不对
        try {
            c.getContentResolver().openInputStream(
                    Uri.parse("content://" + auth + "/import"));
            fail("段数不对应当被拒绝");
        } catch (Exception expected) {
            assertTrue(expected.getMessage() + "", true);
        }
    }

    /** 扩展名嗅探：.zip 里是 level.dat 就当世界，是 manifest.json 就当资源包。 */
    @Test
    public void sniffZipAsWorldOrPack() throws Exception {
        File tmp = new File(ctx().getCacheDir(), "snifftest2");
        //noinspection ResultOfMethodCallIgnored
        tmp.mkdirs();

        File worldZip = writeFile(tmp, "MyWorld.zip", zipOf("MyWorld/level.dat"));
        assertEquals("含 level.dat 的 .zip 应被当成世界",
                "MyWorld.mcworld",
                WorldPackNormalizer.decideName(WorldPackNormalizer.inspect(worldZip), "MyWorld.zip"));

        File packZip = writeFile(tmp, "CoolPack.zip", zipOf("manifest.json"));
        assertEquals("含 manifest.json 的 .zip 应被当成资源包",
                "CoolPack.mcpack",
                WorldPackNormalizer.decideName(WorldPackNormalizer.inspect(packZip), "CoolPack.zip"));

        File already = writeFile(tmp, "Done.mcworld", zipOf("level.dat"));
        assertEquals("已经是对得上的扩展名就不动",
                "Done.mcworld",
                WorldPackNormalizer.decideName(WorldPackNormalizer.inspect(already), "Done.mcworld"));

        File unknown = writeFile(tmp, "Weird.zip", zipOf("something/else.txt"));
        assertEquals("看不懂的内容兜底按世界处理",
                "Weird.mcworld",
                WorldPackNormalizer.decideName(WorldPackNormalizer.inspect(unknown), "Weird.zip"));

        File notZip = writeFile(tmp, "Broken.zip", "not a zip".getBytes("UTF-8"));
        assertEquals("根本不是压缩包也应兜底而不是崩",
                "Broken.mcworld",
                WorldPackNormalizer.decideName(WorldPackNormalizer.inspect(notZip), "Broken.zip"));
    }

    // ==================================================================
    // 下面这几条对应真机上踩到的坑：
    // 世界 zip 里 level.dat 埋在了子目录里，游戏把它原样解到
    // minecraftWorlds/<新ID>/ 下，结果变成 <新ID>/<子目录>/level.dat，读不到。
    // ==================================================================

    /** level.dat 已经在根目录：不需要展平。 */
    @Test
    public void worldAtRootNeedsNoFlatten() throws Exception {
        File tmp = new File(ctx().getCacheDir(), "flat1");
        //noinspection ResultOfMethodCallIgnored
        tmp.mkdirs();
        File zip = writeFile(tmp, "w.mcworld", zipOfEntries(
                "level.dat", "levelname.txt", "db/CURRENT", "world_icon.jpeg"));

        WorldPackNormalizer.Info info = WorldPackNormalizer.inspect(zip);
        assertTrue("应识别为世界", info.hasLevelDat);
        assertEquals("世界根就是 zip 根目录", "", info.worldPrefix);
        assertTrue("不需要展平", !info.needsFlatten());
    }

    /** 多套一层（实测踩到的情形）：应识别出前缀并展平。 */
    @Test
    public void nestedWorldGetsFlattened() throws Exception {
        File tmp = new File(ctx().getCacheDir(), "flat2");
        //noinspection ResultOfMethodCallIgnored
        tmp.mkdirs();
        File zip = writeFile(tmp, "nested.zip", zipOfEntries(
                "+OYCABpnCQA=/level.dat",
                "+OYCABpnCQA=/levelname.txt",
                "+OYCABpnCQA=/db/CURRENT",
                "__MACOSX/._level.dat",           // 垃圾，展平时应当丢掉
                "readme.txt"));                   // 世界根之外，也丢掉

        WorldPackNormalizer.Info info = WorldPackNormalizer.inspect(zip);
        assertTrue(info.hasLevelDat);
        assertEquals("世界根前缀应是那层文件夹", "+OYCABpnCQA=/", info.worldPrefix);
        assertTrue("应需要展平", info.needsFlatten());

        File out = new File(tmp, "flat.mcworld");
        int n = WorldPackNormalizer.flatten(zip, out, info.worldPrefix);
        assertEquals("只应写入世界根内的 3 个文件", 3, n);

        WorldPackNormalizer.Info after = WorldPackNormalizer.inspect(out);
        assertEquals("展平后 level.dat 应落在根目录", "", after.worldPrefix);
        assertTrue("展平后不需要再展平", !after.needsFlatten());
        assertEquals("展平后条目数应正确", 3, after.entries);

        // 逐项核对剥前缀是否正确
        java.util.List<String> names = entryNames(out);
        assertTrue("应含 level.dat", names.contains("level.dat"));
        assertTrue("应含 db/CURRENT", names.contains("db/CURRENT"));
        assertTrue("应含 levelname.txt", names.contains("levelname.txt"));
        assertTrue("不应残留原前缀", !names.toString().contains("+OYCABpnCQA="));
        assertTrue("不应残留 __MACOSX", !names.toString().contains("__MACOSX"));
        assertTrue("不应残留 readme", !names.contains("readme.txt"));
    }

    /** 套两层：也应能定位到最浅的 level.dat 并展平。 */
    @Test
    public void doubleNestedWorldGetsFlattened() throws Exception {
        File tmp = new File(ctx().getCacheDir(), "flat3");
        //noinspection ResultOfMethodCallIgnored
        tmp.mkdirs();
        File zip = writeFile(tmp, "double.zip", zipOfEntries(
                "WorldName/level.dat", "WorldName/db/CURRENT", "WorldName/levelname.txt"));

        WorldPackNormalizer.Info info = WorldPackNormalizer.inspect(zip);
        assertEquals("WorldName/", info.worldPrefix);

        File out = new File(tmp, "flat.mcworld");
        WorldPackNormalizer.flatten(zip, out, info.worldPrefix);
        assertEquals("展平后 level.dat 在根目录", "",
                WorldPackNormalizer.inspect(out).worldPrefix);
    }

    private static java.util.List<String> entryNames(File zip) throws Exception {
        java.util.List<String> out = new java.util.ArrayList<String>();
        java.util.zip.ZipFile z = new java.util.zip.ZipFile(zip);
        try {
            java.util.Enumeration<? extends java.util.zip.ZipEntry> en = z.entries();
            while (en.hasMoreElements()) out.add(en.nextElement().getName());
        } finally {
            z.close();
        }
        return out;
    }

    private static byte[] zipOfEntries(String... names) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        ZipOutputStream z = new ZipOutputStream(bos);
        try {
            for (String n : names) {
                z.putNextEntry(new ZipEntry(n));
                z.write(("payload-" + n).getBytes("UTF-8"));
                z.closeEntry();
            }
        } finally {
            z.close();
        }
        return bos.toByteArray();
    }

    private static byte[] zipOf(String entryName) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        ZipOutputStream z = new ZipOutputStream(bos);
        try {
            z.putNextEntry(new ZipEntry(entryName));
            z.write(new byte[]{1, 2, 3});
            z.closeEntry();
        } finally {
            z.close();
        }
        return bos.toByteArray();
    }
}
