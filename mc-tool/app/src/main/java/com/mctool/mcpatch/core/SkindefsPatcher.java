package com.mctool.mcpatch.core;

import java.nio.charset.StandardCharsets;

/**
 * 改写皮肤包里的 {@code skindefs.json}，切换手臂粗细。
 *
 * <p>原始内容（v19 包实测）：
 * <pre>
 * {
 *   "geometry": "skinpacks/skins.json",            &lt;-- 顶层，指向几何文件，不能动
 *   "skins": [
 *     { "name": "Alex",  "id": "skinpacks/Base/alex",  "geometry": "geometry.humanoid.customSlim", "texture": "skinpacks/Base/alex",  "type": "Free" },
 *     { "name": "Steve", "id": "skinpacks/Base/steve", "geometry": "geometry.humanoid.custom",     "texture": "skinpacks/Base/steve", "type": "Free" },
 *     { "name": "Dummy", "id": "skinpacks/Base/dummy", "geometry": "geometry.humanoid.custom",     "texture": "skinpacks/Base/dummy", "type": "Custom" }
 *   ]
 * }
 * </pre>
 *
 * <p>{@code geometry.humanoid.customSlim} = 细手臂(Alex 体型)，
 * {@code geometry.humanoid.custom} = 粗手臂(Steve 体型)，
 * 二者都在同目录的 {@code base.json} 里定义（{@code base.json} 顶层键就是
 * {@code geometry.humanoid} / {@code geometry.humanoid.custom} / {@code geometry.humanoid.customSlim}）。
 *
 * <p>这里把 Alex / Steve 两个 Free 皮肤都改成目标体型：因为我们同时把
 * {@code steve.png} 也换成用户的图，两条记录指向同一张皮肤，
 * 只有几何体一致才不会出现「换个槽位手臂就变粗」的随机感。
 * Dummy 是 {@code type: Custom}（玩家自己导入皮肤的占位槽），保持原样。
 */
public final class SkindefsPatcher {

    public static final String SLIM = "geometry.humanoid.customSlim";
    public static final String CLASSIC = "geometry.humanoid.custom";

    private SkindefsPatcher() {
    }

    /** @param slim true=细手臂(Alex) false=粗手臂(Steve) */
    public static byte[] applyArms(byte[] skindefsJson, boolean slim) {
        String s = new String(skindefsJson, StandardCharsets.UTF_8);
        String target = slim ? SLIM : CLASSIC;

        // SLIM 是 CLASSIC 的前缀，先把它换成占位符，免得替换串味
        final String HOLD = "\u0001SLIM_HOLD\u0001";
        s = s.replace(SLIM, HOLD);
        s = s.replace(CLASSIC, target);
        s = s.replace(HOLD, target);

        if (s.indexOf("geometry.humanoid.custom") < 0) {
            throw new IllegalStateException("skindefs.json 里没有找到 geometry.humanoid.custom*，"
                    + "这个包的皮肤结构可能和预期不同，为安全起见不再继续");
        }
        return s.getBytes(StandardCharsets.UTF_8);
    }

    /** 供 UI 显示用：把 skindefs.json 解析成「皮肤名 -> 体型」的摘要。 */
    public static String describe(byte[] skindefsJson) {
        String s = new String(skindefsJson, StandardCharsets.UTF_8);
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (true) {
            int k = s.indexOf("\"name\"", i);
            if (k < 0) break;
            int v1 = s.indexOf('"', s.indexOf(':', k) + 1);
            int v2 = v1 < 0 ? -1 : s.indexOf('"', v1 + 1);
            if (v2 < 0) break;
            String name = s.substring(v1 + 1, v2);
            int g = s.indexOf("\"geometry\"", v2);
            String geo = "?";
            if (g >= 0) {
                int g1 = s.indexOf('"', s.indexOf(':', g) + 1);
                int g2 = g1 < 0 ? -1 : s.indexOf('"', g1 + 1);
                if (g2 > 0) geo = s.substring(g1 + 1, g2);
            }
            if (sb.length() > 0) sb.append('\n');
            sb.append("  ").append(name).append(" -> ").append(geo);
            i = v2 + 1;
        }
        return sb.toString();
    }
}
