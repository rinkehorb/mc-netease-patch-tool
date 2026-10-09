package com.mctool.mcpatch;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * 极简 ContentProvider：把自己产出的文件以 {@code content://} 暴露给别的 App。
 *
 * <p>两个用途：
 * <ul>
 *   <li>{@code output/} 下刚生成好的 APK —— 交给系统安装器（Android 7 起
 *       Intent 里带 {@code file://} 会抛 FileUriExposedException，必须是 content URI）；</li>
 *   <li>{@code import/} 下的 {@code .mcworld} 等存档文件 —— 交给《我的世界》自己的
 *       {@code ACTION_VIEW} 导入通道（游戏是另一个包名，读不到本应用的
 *       {@code Android/data} 目录，只能走 content URI + 临时授权）。</li>
 * </ul>
 *
 * <p>安全：只允许访问上面两个白名单目录下的<b>单层文件名</b>，
 * 拒绝任何带 {@code /} 或 {@code ..} 的路径；provider 本身
 * {@code exported=false}，只对显式授权的接收方开放。
 */
public class ShareFileProvider extends ContentProvider {

    public static final String AUTHORITY_SUFFIX = ".files";

    public static final String KIND_OUTPUT = "output";
    public static final String KIND_IMPORT = "import";

    private static final Set<String> ALLOWED_KINDS =
            new HashSet<String>(Arrays.asList(KIND_OUTPUT, KIND_IMPORT));

    /** 取（必要时创建）某个共享子目录。 */
    public static File dir(Context ctx, String kind) {
        File d = ctx.getExternalFilesDir(kind);
        if (d == null) d = new File(ctx.getFilesDir(), kind);
        if (!d.exists()) {
            //noinspection ResultOfMethodCallIgnored
            d.mkdirs();
        }
        return d;
    }

    /** 生成指向该文件的 content URI（形如 {@code content://<pkg>.files/<kind>/<name>}）。 */
    public static Uri uriFor(Context ctx, File f) {
        File parent = f.getParentFile();
        String kind = parent == null ? KIND_OUTPUT : parent.getName();
        return new Uri.Builder()
                .scheme("content")
                .authority(ctx.getPackageName() + AUTHORITY_SUFFIX)
                .appendPath(kind)
                .appendPath(f.getName())
                .build();
    }

    /** 按扩展名给出 MIME。基岩版认 {@code application/octet-stream}。 */
    public static String mimeFor(String name) {
        String n = name == null ? "" : name.toLowerCase(Locale.ROOT);
        if (n.endsWith(".apk")) return "application/vnd.android.package-archive";
        return "application/octet-stream";
    }

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        Context ctx = getContext();
        if (ctx == null) throw new FileNotFoundException("no context");

        java.util.List<String> seg = uri.getPathSegments();
        if (seg == null || seg.size() != 2) {
            throw new FileNotFoundException("非法路径: " + uri);
        }
        String kind = seg.get(0);
        String name = seg.get(1);
        if (!ALLOWED_KINDS.contains(kind)) {
            throw new FileNotFoundException("不允许的目录: " + kind);
        }
        if (name.isEmpty() || name.indexOf('/') >= 0 || name.indexOf('\\') >= 0
                || name.contains("..")) {
            throw new FileNotFoundException("非法文件名: " + name);
        }
        File f = new File(dir(ctx, kind), name);
        if (!f.isFile()) throw new FileNotFoundException(f.getAbsolutePath());
        return ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override
    public String getType(Uri uri) {
        java.util.List<String> seg = uri.getPathSegments();
        return mimeFor(seg == null || seg.size() < 2 ? null : seg.get(1));
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection,
                        String[] selectionArgs, String sortOrder) {
        return null;
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }
}
