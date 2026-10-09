package com.mctool.mcpatch.core;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/**
 * 基岩版 {@code .lang} 的改写。
 *
 * <p>实测源文件特征（v19 包里的 zh_CN.lang / en_US.lang）：
 * <ul>
 *   <li>UTF-8 <b>带 BOM</b>（EF BB BF）</li>
 *   <li>行尾是 {@code \n}（LF），文件末尾<b>没有</b>换行</li>
 *   <li>大量行形如 {@code key=value\t#注释}，4805/5183 行都带 {@code \t#}</li>
 * </ul>
 *
 * <p>{@code skin.name.alex} 这一行在 v19 里被改成了不带 {@code \t#} 尾巴的
 * {@code skin.name.alex=Miku}，并且实测生效，所以这里也统一去掉尾巴。
 */
public final class LangPatcher {

    private static final byte[] BOM = {(byte) 0xEF, (byte) 0xBB, (byte) 0xBF};

    /** 会被改写的键。三个都写，避免游戏到底读哪个槽位的问题。 */
    public static final String[] NAME_KEYS = {
            "skin.name.alex", "skin.name.steve", "skin.name.dummy"
    };

    private LangPatcher() {
    }

    /**
     * 把 {@code skin.name.*} 的值换成玩家名。
     *
     * @param lang 原始 lang 字节（可带 BOM）
     * @return 新的 lang 字节（保留 BOM、保留所有其它行与注释）
     */
    public static byte[] renamePlayer(byte[] lang, String name) {
        boolean bom = hasBom(lang);
        String text = decode(lang);
        StringBuilder sb = new StringBuilder(text.length() + 64);

        boolean touched = false;
        int i = 0;
        while (true) {
            int nl = text.indexOf('\n', i);
            String line = nl < 0 ? text.substring(i) : text.substring(i, nl);
            if (isNameKey(line)) {
                int eq = line.indexOf('=');
                if (eq > 0) {
                    line = line.substring(0, eq) + "=" + name;
                    touched = true;
                }
            }
            sb.append(line);
            if (nl < 0) break;
            sb.append('\n');
            i = nl + 1;
        }

        if (!touched) {
            // 这份 lang 里没有 skin.name.*（换了版本/换了语言），兜底追加
            if (sb.length() > 0 && sb.charAt(sb.length() - 1) != '\n') sb.append('\n');
            for (int k = 0; k < NAME_KEYS.length; k++) {
                sb.append(NAME_KEYS[k]).append('=').append(name);
                if (k != NAME_KEYS.length - 1) sb.append('\n');
            }
        }
        return encode(sb.toString(), bom);
    }

    /**
     * 把资源包自带的 lang <b>追加</b>到现有 lang 后面。
     *
     * <p>基岩版的 lang 是按行读进 map，后出现的键覆盖先出现的，
     * 所以「原文件 + 资源包」的顺序天然让资源包的翻译优先生效，
     * 同时不会像直接覆盖那样把游戏 UI 文案整片弄丢。
     */
    public static byte[] appendLines(byte[] base, byte[] extraLang) {
        boolean bom = hasBom(base);
        String baseText = decode(base);
        String extraText = decode(extraLang);

        StringBuilder sb = new StringBuilder(baseText.length() + extraText.length() + 8);
        sb.append(baseText);
        if (sb.length() > 0 && sb.charAt(sb.length() - 1) != '\n') sb.append('\n');
        // 去掉 extra 自己的 BOM 残留与首尾空白行
        int start = 0;
        while (start < extraText.length()
                && (extraText.charAt(start) == '\n' || extraText.charAt(start) == '\r'
                || extraText.charAt(start) == '\uFEFF')) {
            start++;
        }
        sb.append(extraText, start, extraText.length());
        return encode(sb.toString(), bom);
    }

    // ------------------------------------------------------------------ 内部

    private static boolean isNameKey(String line) {
        for (String k : NAME_KEYS) {
            if (line.startsWith(k)) {
                int after = k.length();
                if (after < line.length() && line.charAt(after) == '=') return true;
            }
        }
        return false;
    }

    private static boolean hasBom(byte[] b) {
        return b != null && b.length >= 3
                && (b[0] & 0xFF) == 0xEF && (b[1] & 0xFF) == 0xBB && (b[2] & 0xFF) == 0xBF;
    }

    private static String decode(byte[] b) {
        int off = hasBom(b) ? 3 : 0;
        String s = new String(b, off, b.length - off, StandardCharsets.UTF_8);
        if (!s.isEmpty() && s.charAt(0) == '\uFEFF') s = s.substring(1);
        return s;
    }

    private static byte[] encode(String s, boolean bom) {
        ByteArrayOutputStream bos = new ByteArrayOutputStream(s.length() * 2 + 3);
        if (bom) {
            bos.write(BOM, 0, BOM.length);
        }
        byte[] raw = s.getBytes(StandardCharsets.UTF_8);
        bos.write(raw, 0, raw.length);
        return bos.toByteArray();
    }
}
