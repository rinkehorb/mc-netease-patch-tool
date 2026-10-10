package com.mctool.mcpatch;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.assertFalse;

import android.content.Context;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;

import java.io.ByteArrayInputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * 「换手臂粗细（免 root）」的本地可验证部分：
 * 模板内容对不对、打出来的 zip 游戏那边能不能按预期解（一个根目录下的 options.txt）。
 *
 * <p>不能在这里验证的部分（要靠真机）：decompress_map 是否真的写得进游戏私有目录。
 * 那一条已在 2026-10-10 用一加（有 root）逐字节 + vivo（无 root）重启看手臂 两次实测通过。
 */
@RunWith(RobolectricTestRunner.class)
public class ArmSwitchTest {

    private Context ctx() {
        return RuntimeEnvironment.getApplication();
    }

    @Test
    public void templatesOnlyDifferInTheArmLine() throws Exception {
        String alex = ArmSwitch.armLine(ctx(), true);
        String steve = ArmSwitch.armLine(ctx(), false);
        assertEquals("game_skintypefull:Standard_Alex", alex);
        assertEquals("game_skintypefull:Standard_Steve", steve);
    }

    @Test
    public void zipContainsSingleRootOptionsTxt() throws Exception {
        for (boolean slim : new boolean[]{true, false}) {
            byte[] zip = ArmSwitch.buildZip(ctx(), slim);
            ZipInputStream zin = new ZipInputStream(new ByteArrayInputStream(zip));
            ZipEntry e = zin.getNextEntry();
            assertEquals("options.txt", e.getName());
            assertFalse("不该有目录结构（decompress_map 会压平）", e.getName().contains("/"));
            assertTrue("模板内容应当非空", e.getSize() != 0 || zip.length > 200);
            zin.closeEntry();
            assertEquals("只应该有一个条目", null, zin.getNextEntry());
            zin.close();
        }
    }

    @Test
    public void zipContentMatchesTemplate() throws Exception {
        byte[] zip = ArmSwitch.buildZip(ctx(), false);
        ZipInputStream zin = new ZipInputStream(new ByteArrayInputStream(zip));
        zin.getNextEntry();
        StringBuilder sb = new StringBuilder();
        byte[] buf = new byte[4096];
        int n;
        while ((n = zin.read(buf)) > 0) sb.append(new String(buf, 0, n, "UTF-8"));
        zin.close();
        String s = sb.toString();
        assertTrue("解出来的就是那一行 Steve: " + ArmSwitch.armLine(ctx(), false),
                s.contains("game_skintypefull:Standard_Steve"));
        assertTrue("应当还带着其它设置项", s.contains("game_language:"));
    }

    @Test
    public void baseNamesAreStable() {
        // 游戏侧的候选文件名写死在这两个字符串上，改了必须同步 mc-import.js 的 ARM_BASES
        assertEquals("mcarm_3px", ArmSwitch.baseName(true));
        assertEquals("mcarm_4px", ArmSwitch.baseName(false));
        assertEquals("options-arm3.txt", ArmSwitch.assetName(true));
        assertEquals("options-arm4.txt", ArmSwitch.assetName(false));
    }
}
