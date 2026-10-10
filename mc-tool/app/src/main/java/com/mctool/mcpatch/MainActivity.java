package com.mctool.mcpatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextWatcher;
import android.text.method.ScrollingMovementMethod;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.RadioButton;
import android.widget.TextView;
import android.widget.Toast;

import com.mctool.mcpatch.core.ApkPatcher;
import com.mctool.mcpatch.core.ApkSignerHelper;
import com.mctool.mcpatch.core.PatchLog;
import com.mctool.mcpatch.core.PatchSpec;
import com.mctool.mcpatch.core.WorldImportPrep;
import com.mctool.mcpatch.core.WorldPackNormalizer;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.zip.ZipFile;

/**
 * 单界面工具：选源 APK → 勾要改的东西 → 一键生成 → 直接安装。
 *
 * <p>几个关键点：
 * <ul>
 *   <li>选完源 APK 会后台做一次<b>体检</b>（拷贝 + 读包信息 + 读签名 + 查关键文件），
 *       并把「签名是否与内置密钥一致」「是不是网易版」当场显示出来。</li>
 *   <li>「能否覆盖安装」是<b>动态算出来的</b>：读源包真实签名与内置密钥指纹比对。</li>
 *   <li>所有选择都会记住（SharedPreferences），下次打开直接点生成。</li>
 *   <li>外观默认<b>跟随系统</b>，标题栏右上角的太阳/月亮按钮可以手动切浅色/深色/跟随。</li>
 *   <li>资源包支持<b>多选叠加</b>，按加入顺序覆盖。</li>
 * </ul>
 */
public class MainActivity extends Activity {

    private static final int REQ_APK = 1001;
    private static final int REQ_SKIN = 1002;
    private static final int REQ_PACK = 1003;
    private static final int REQ_IMPORT = 1004;
    private static final int REQ_STORAGE_PERM = 2001;
    private static final int REQ_INSTALL_PERM = 2002;
    private static final int MENU_THEME = 1;

    /**
     * 《我的世界》的包名候选（按优先级）。
     * 存档导入要把文件交给游戏自己处理，所以得先找到它是谁。
     */
    private static final String[] MC_PACKAGES = {
            "com.netease.mc.qihoo",     // 网易版（奇酷渠道，就是这个包）
            "com.netease.mc.aligames",  // 网易版（其他渠道）
            "com.netease.mc",           // 网易版（通用）
            "com.mojang.minecraftpe",   // 国际版
    };

    /** 基岩版认识的存档/包扩展名由 core 里的 {@code WorldPackNormalizer} 统一处理。 */


    // 签名材料：PKCS#8 私钥 + X.509 证书。
    // 刻意不用 KeyStore —— Android 没有 JKS 实现（真机上会抛 JKS not found）。
    private static final String ASSET_KEY = "mc-patch-key.pk8";
    private static final String ASSET_CERT = "mc-patch-cert.pem";

    private static final String PREF = "mcpatch";
    private static final String SK_CACHE = "last-skin.png";

    private static final String THEME_AUTO = "auto";
    private static final String THEME_LIGHT = "light";
    private static final String THEME_DARK = "dark";

    // ---------------- 选择状态
    private Uri apkUri;
    private String apkName = "";
    private long apkSize = -1;
    private byte[] skinPng;
    private String skinLabel = "";
    private final List<Uri> packUris = new ArrayList<Uri>();
    private final List<String> packNames = new ArrayList<String>();

    // ---------------- 导入存档（3a）
    private Uri importUri;
    private String importName = "";
    private CheckBox cbDowngrade;

    private File copiedInput;
    private Uri lastCopiedFrom;
    private long lastCopiedSize = -1;
    private volatile int prepareSeq;

    // ---------------- 签名材料
    private byte[] signerKey, signerCert;
    private String bundledSha;

    private String themeMode = THEME_AUTO;
    private File outputApk;

    private final Handler ui = new Handler(Looper.getMainLooper());
    private volatile boolean cancelled;
    private volatile boolean running;

    // ---------------- 控件
    private TextView tvApk, tvSourceInfo, tvSkin, tvPack, tvStatus, tvLog, tvSign, tvImport;
    private CheckBox cbRename, cbSkin, cbPack, cbAutoExport;
    private EditText etName;
    private ImageView ivSkin;
    private RadioButton rbSlim, rbClassic;
    private Button btnGenerate, btnInstall;
    private ProgressBar progress;

    private SharedPreferences prefs;
    private final StringBuilder logBuf = new StringBuilder();
    /** 是否正在跑任务。用来决定日志区要不要自动展开（启动时不展开）。 */
    private volatile boolean taskRunning = false;

    // ================================================================== 生命周期

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // prefs 要在 super.onCreate 之前读，才能先把主题定下来再建界面
        prefs = getSharedPreferences(PREF, Context.MODE_PRIVATE);
        themeMode = prefs.getString("theme", THEME_AUTO);
        applyTheme();
        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        try {
            android.app.ActionBar ab = getActionBar();
            if (ab != null) ab.setSubtitle(getString(R.string.author_subtitle));
        } catch (Throwable ignored) {
            // 没有 ActionBar 的主题也无所谓，页面底部还有一行署名
        }

        tvApk = findViewById(R.id.tvApk);
        tvSourceInfo = findViewById(R.id.tvSourceInfo);
        tvSkin = findViewById(R.id.tvSkin);
        tvPack = findViewById(R.id.tvPack);
        tvStatus = findViewById(R.id.tvStatus);
        tvLog = findViewById(R.id.tvLog);
        tvSign = findViewById(R.id.tvSign);
        tvImport = findViewById(R.id.tvImport);
        cbDowngrade = findViewById(R.id.cbDowngrade);
        cbRename = findViewById(R.id.cbRename);
        cbSkin = findViewById(R.id.cbSkin);
        cbPack = findViewById(R.id.cbPack);
        cbAutoExport = findViewById(R.id.cbAutoExport);
        etName = findViewById(R.id.etName);
        ivSkin = findViewById(R.id.ivSkin);
        rbSlim = findViewById(R.id.rbSlim);
        rbClassic = findViewById(R.id.rbClassic);
        btnGenerate = findViewById(R.id.btnGenerate);
        btnInstall = findViewById(R.id.btnInstall);
        progress = findViewById(R.id.progress);
        tvLog.setMovementMethod(new ScrollingMovementMethod());

        // 先恢复上次的选择，再接监听器（免得恢复过程本身触发保存）
        restoreState();
        wireListeners();
        applyEnabledStates();

        checkSigner();
        if (apkUri != null) {
            startPrepare();
        }
    }

    /** 浅色/深色/跟随系统。auto 时不 setTheme，由 values/values-night 决定。 */
    private void applyTheme() {
        if (THEME_LIGHT.equals(themeMode)) {
            setTheme(R.style.Theme_MCPatch_Light);
        } else if (THEME_DARK.equals(themeMode)) {
            setTheme(R.style.Theme_MCPatch_Dark);
        }
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        // 清单里声明了 uiMode，所以系统切深色时 Activity 不会自动重建；
        // 这里主动重建一次去套用新主题。正在生成时不动，免得打断。
        if (!running && THEME_AUTO.equals(themeMode)) {
            recreate();
        }
    }

    // ------------------------------------------------------------------ 标题栏右上角的外观切换

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        MenuItem it = menu.add(0, MENU_THEME, 0, R.string.theme_auto);
        it.setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS);
        it.setIcon(themeIconRes());
        return true;
    }

    @Override
    public boolean onPrepareOptionsMenu(Menu menu) {
        MenuItem it = menu.findItem(MENU_THEME);
        if (it != null) it.setIcon(themeIconRes());
        return super.onPrepareOptionsMenu(menu);
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        if (item.getItemId() == MENU_THEME) {
            cycleTheme();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private int themeIconRes() {
        if (THEME_LIGHT.equals(themeMode)) return R.drawable.ic_theme_sun;
        if (THEME_DARK.equals(themeMode)) return R.drawable.ic_theme_moon;
        return R.drawable.ic_theme_auto;
    }

    private String themeLabel() {
        if (THEME_LIGHT.equals(themeMode)) return getString(R.string.theme_light);
        if (THEME_DARK.equals(themeMode)) return getString(R.string.theme_dark);
        return getString(R.string.theme_auto);
    }

    private void cycleTheme() {
        themeMode = THEME_AUTO.equals(themeMode) ? THEME_LIGHT
                : THEME_LIGHT.equals(themeMode) ? THEME_DARK : THEME_AUTO;
        prefs.edit().putString("theme", themeMode).apply();
        if (running) {
            toast(getString(R.string.theme_now, themeLabel()) + "（生成中，下次打开生效）");
            return;
        }
        toast(getString(R.string.theme_now, themeLabel()));
        recreate();
    }

    private void wireListeners() {
        findViewById(R.id.btnPickApk).setOnClickListener(v -> pick(REQ_APK, "*/*", false));
        findViewById(R.id.btnPickSkin).setOnClickListener(v -> pick(REQ_SKIN, "image/*", false));
        findViewById(R.id.btnPickPack).setOnClickListener(v -> pick(REQ_PACK, "*/*", true));

        findViewById(R.id.btnClearName).setOnClickListener(v -> etName.setText(""));
        findViewById(R.id.btnClearPack).setOnClickListener(v -> {
            packUris.clear();
            packNames.clear();
            renderPackList();
            saveState();
        });

        cbRename.setOnCheckedChangeListener((b, c) -> {
            applyEnabledStates();
            saveState();
        });
        cbSkin.setOnCheckedChangeListener((b, c) -> {
            applyEnabledStates();
            saveState();
        });
        cbPack.setOnCheckedChangeListener((b, c) -> saveState());
        cbAutoExport.setOnCheckedChangeListener((b, c) -> saveState());
        etName.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int a, int b, int c) {
            }

            @Override
            public void onTextChanged(CharSequence s, int a, int b, int c) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                saveState();
            }
        });
        ((android.widget.RadioGroup) findViewById(R.id.rgArms))
                .setOnCheckedChangeListener((group, checkedId) -> saveState());

        btnGenerate.setOnClickListener(v -> startGenerate());
        btnInstall.setOnClickListener(v -> doInstall());
        findViewById(R.id.btnCopyLog).setOnClickListener(v -> doCopyLog());

        // 导入存档（独立功能，不依赖源 APK）
        findViewById(R.id.btnPickImport).setOnClickListener(v -> pick(REQ_IMPORT, "*/*", false));
        findViewById(R.id.btnDoImport).setOnClickListener(v -> startImport());

        // 换手臂粗细（免 root）：把改好的 options.txt 写成 Download 里的 .png，
        // 游戏启动时由注入的 H5 脚本 decompress_map 写进游戏私有目录。
        findViewById(R.id.btnArm3).setOnClickListener(v -> startArmSwitch(true));
        findViewById(R.id.btnArm4).setOnClickListener(v -> startArmSwitch(false));

        // 折叠区：5 导入 / 6 换手臂 / 日志。默认都收起 —— 这个页面说明文字多，
        // 全展开要滚很久（用户反馈过"太长了"）。
        accordion(R.id.hdrImport, R.id.boxImport, false);
        accordion(R.id.hdrArm, R.id.boxArm, false);
        accordion(R.id.hdrLog, R.id.boxLog, false);
    }

    /**
     * 把「标题 + 内容块」做成可折叠：点标题切换显示，标题前用 ▾/▸ 表示状态。
     *
     * <p>纯 XML 没有折叠控件，这里用「标题点击 → 切换内容块 visibility」实现，
     * 不引入任何库。标题原文里不带箭头，所以箭头是加在前面的。
     */
    private void accordion(int headerId, int boxId, boolean openByDefault) {
        final TextView h = findViewById(headerId);
        final View box = findViewById(boxId);
        final String base = h.getText().toString().replaceFirst("^[▾▸]\\s*", "");
        final boolean[] open = {openByDefault};
        box.setVisibility(openByDefault ? View.VISIBLE : View.GONE);
        h.setText((openByDefault ? "▾ " : "▸ ") + base);
        h.setOnClickListener(v -> {
            open[0] = !open[0];
            box.setVisibility(open[0] ? View.VISIBLE : View.GONE);
            h.setText((open[0] ? "▾ " : "▸ ") + base);
        });
    }

    /** 有日志输出时把日志区自动展开，否则用户以为什么都没发生。 */
    private void openLogBox() {
        View box = findViewById(R.id.boxLog);
        if (box.getVisibility() != View.VISIBLE) {
            box.setVisibility(View.VISIBLE);
            TextView h = findViewById(R.id.hdrLog);
            h.setText("▾ " + h.getText().toString().replaceFirst("^[▾▸]\\s*", ""));
        }
    }

    /**
     * 「换手臂粗细（不用 root）」。
     *
     * <p>手臂体型存在游戏私有目录的 {@code options.txt} 里（{@code game_skintypefull}），
     * 普通应用碰不到；但游戏里的 H5 有 {@code decompress_map}，能以<b>游戏身份</b>写进去。
     * 这里只负责把「改好的 options.txt」打成包、放到游戏读得到的地方；
     * 真正落盘由游戏启动时注入的 {@code mc-import.js} 完成。
     *
     * @param slim true = 3px 细手臂（Alex），false = 4px 粗手臂（Steve）
     */
    private void startArmSwitch(boolean slim) {
        final String base = ArmSwitch.baseName(slim);
        new Thread(() -> {
            try {
                stage("准备手臂切换包…");
                log("=== 换手臂粗细：" + ArmSwitch.label(slim) + " ===");
                byte[] zip = ArmSwitch.buildZip(this, slim);
                // 保证同一时刻只有一个手臂包：先把另一个删掉。
                // 否则两个文件同时存在时，游戏先找到哪个就用哪个，后点的那个等于白点。
                ShareWriter.delete(this, ArmSwitch.baseName(!slim));
                log("  模板 " + ArmSwitch.assetName(slim) + " → " + ArmSwitch.armLine(this, slim));
                File f = ShareWriter.write(this, base, zip);
                log("  已写入 " + f.getName() + "  (" + fmt(zip.length) + ")");
                log("  位置：" + ShareWriter.dirDesc());
                log("  游戏侧会写进：" + ArmSwitch.DEST_DIR);
                log("");
                log("接下来：");
                log("  ① 打开游戏（左下角会提示已写入手臂配置）");
                log("  ② 完全关掉游戏（切后台 / 划掉都行）");
                log("  ③ 重新打开 —— 手臂就是 " + (slim ? "3px 细（Alex）" : "4px 粗（Steve）"));
                log("⚠️ 会重置游戏设置；改完直接关掉游戏，别在运行时覆盖安装");
                final File out = f;
                ui.post(() -> tvStatus.setText("手臂包已就绪：" + out.getName()
                        + "\n打开游戏 → 完全关掉 → 重开"));
            } catch (Throwable e) {
                final String m = e.getMessage() == null ? e.toString() : e.getMessage();
                log("失败：" + m);
                ui.post(() -> tvStatus.setText("准备失败：" + m));
            }
        }, "mc-arm").start();
    }

    private void applyEnabledStates() {
        // 只把「输入框/预览」跟着勾选走；选文件的按钮始终可用，
        // 免得用户想先挑好素材再勾选时被挡住
        etName.setEnabled(cbRename.isChecked());
        findViewById(R.id.btnClearName).setEnabled(cbRename.isChecked());
        ivSkin.setEnabled(cbSkin.isChecked());
    }

    // ================================================================== 状态记忆

    private void saveState() {
        if (prefs == null) return;
        prefs.edit()
                .putBoolean("cb_rename", cbRename.isChecked())
                .putBoolean("cb_skin", cbSkin.isChecked())
                .putBoolean("cb_pack", cbPack.isChecked())
                .putBoolean("auto_export", cbAutoExport.isChecked())
                .putBoolean("downgrade", cbDowngrade.isChecked())
                .putBoolean("slim", rbSlim.isChecked())
                .putString("name", etName.getText().toString())
                .putString("apk_uri", apkUri == null ? null : apkUri.toString())
                .putString("apk_name", apkName)
                .putLong("apk_size", apkSize)
                .putString("skin_label", skinLabel)
                .putString("pack_uris", joinLines(uriStrings(packUris)))
                .putString("pack_names", joinLines(packNames))
                .apply();
    }

    private void restoreState() {
        cbRename.setChecked(prefs.getBoolean("cb_rename", false));
        cbSkin.setChecked(prefs.getBoolean("cb_skin", false));
        cbPack.setChecked(prefs.getBoolean("cb_pack", false));
        cbAutoExport.setChecked(prefs.getBoolean("auto_export", false));
        cbDowngrade.setChecked(prefs.getBoolean("downgrade", true));
        if (prefs.getBoolean("slim", true)) rbSlim.setChecked(true);
        else rbClassic.setChecked(true);
        etName.setText(prefs.getString("name", ""));

        String u = prefs.getString("apk_uri", null);
        if (u != null) {
            apkUri = Uri.parse(u);
            apkName = prefs.getString("apk_name", "");
            apkSize = prefs.getLong("apk_size", -1);
            tvApk.setText(apkName + "\n" + fmt(apkSize));
            showSourceInfo(getString(R.string.source_preparing), getColor(R.color.src_warn));
        }

        packUris.clear();
        packNames.clear();
        List<String> us = splitLines(prefs.getString("pack_uris", ""));
        List<String> ns = splitLines(prefs.getString("pack_names", ""));
        for (int i = 0; i < us.size(); i++) {
            packUris.add(Uri.parse(us.get(i)));
            packNames.add(i < ns.size() ? ns.get(i) : us.get(i));
        }
        renderPackList();

        // 皮肤直接读缓存的 PNG，比重新解析相册 URI 可靠
        File cache = new File(getFilesDir(), SK_CACHE);
        if (cache.isFile() && cache.length() > 0) {
            try {
                skinPng = ApkPatcher.readFile(cache);
                skinLabel = prefs.getString("skin_label", "上次用的皮肤");
                int[] sz = ApkPatcher.pngSize(skinPng);
                tvSkin.setText(skinLabel + "  →  " + (sz == null ? "?" : sz[0] + "x" + sz[1]));
                ivSkin.setImageBitmap(BitmapFactory.decodeByteArray(skinPng, 0, skinPng.length));
            } catch (Throwable e) {
                skinPng = null;
            }
        }
    }

    private static List<String> uriStrings(List<Uri> l) {
        List<String> out = new ArrayList<String>(l.size());
        for (Uri u : l) out.add(u.toString());
        return out;
    }

    private static String joinLines(List<String> l) {
        StringBuilder sb = new StringBuilder();
        for (String s : l) {
            if (s == null) continue;
            if (sb.length() > 0) sb.append('\n');
            sb.append(s.replace('\n', ' ').replace('\r', ' '));
        }
        return sb.toString();
    }

    private static List<String> splitLines(String s) {
        List<String> out = new ArrayList<String>();
        if (s == null || s.isEmpty()) return out;
        for (String p : s.split("\n")) {
            if (!p.isEmpty()) out.add(p);
        }
        return out;
    }

    private void renderPackList() {
        if (packNames.isEmpty()) {
            tvPack.setText(R.string.no_pack);
            return;
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < packNames.size(); i++) {
            sb.append(i + 1).append(". ").append(packNames.get(i));
            if (i != packNames.size() - 1) sb.append('\n');
        }
        tvPack.setText(sb.toString());
    }

    // ================================================================== 选择文件

    private void pick(int req, String mime, boolean multi) {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        i.addCategory(Intent.CATEGORY_OPENABLE);
        i.setType(mime);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        if (multi) i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        try {
            startActivityForResult(i, req);
        } catch (Exception e) {
            toast("打不开文件选择器：" + e.getMessage());
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null) return;

        if (requestCode == REQ_PACK) {
            List<Uri> picked = new ArrayList<Uri>();
            ClipData cd = data.getClipData();
            if (cd != null) {
                for (int i = 0; i < cd.getItemCount(); i++) {
                    if (cd.getItemAt(i) != null && cd.getItemAt(i).getUri() != null) {
                        picked.add(cd.getItemAt(i).getUri());
                    }
                }
            } else if (data.getData() != null) {
                picked.add(data.getData());
            }
            if (picked.isEmpty()) return;
            for (Uri u : picked) {
                try {
                    getContentResolver().takePersistableUriPermission(
                            u, Intent.FLAG_GRANT_READ_URI_PERMISSION);
                } catch (Exception ignored) {
                }
                packUris.add(u);
                packNames.add(displayName(u));
            }
            renderPackList();
            saveState();
            log("加入 " + picked.size() + " 个资源包，现有 " + packUris.size() + " 个（按顺序叠加）");
            if (packUris.size() > 1) {
                toast("已叠加 " + packUris.size() + " 个资源包：后面的覆盖前面的同名文件");
            }
            return;
        }

        if (data.getData() == null) return;
        Uri uri = data.getData();
        try {
            getContentResolver().takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (Exception ignored) {
            // 有些 provider 不支持持久化授权；那下次启动就要重新选，不影响本次使用
        }

        if (requestCode == REQ_IMPORT) {
            if (data.getData() == null) return;
            importUri = data.getData();
            importName = displayName(importUri);
            tvImport.setText(importName + "\n" + fmt(sizeOf(importUri)));
            findViewById(R.id.btnDoImport).setEnabled(true);
            log("待导入存档：" + importName + " (" + fmt(sizeOf(importUri)) + ")");
            return;
        }

        if (requestCode == REQ_APK) {
            apkUri = uri;
            apkName = displayName(uri);
            apkSize = sizeOf(uri);
            copiedInput = null;       // 换了包，缓存作废
            lastCopiedFrom = null;
            tvApk.setText(apkName + "\n" + fmt(apkSize));
            log("源 APK：" + apkName + " (" + fmt(apkSize) + ")");
            if (apkSize > 0 && apkSize < 40L * 1024 * 1024) {
                toast("这个文件只有 " + fmt(apkSize) + "，看起来不像《我的世界》的包");
            }
            saveState();
            startPrepare();
        } else if (requestCode == REQ_SKIN) {
            try {
                skinPng = decodeSkin(uri);
                skinLabel = displayName(uri);
                int[] sz = ApkPatcher.pngSize(skinPng);
                tvSkin.setText(skinLabel + "  →  " + sz[0] + "x" + sz[1] + " PNG " + fmt(skinPng.length));
                ivSkin.setImageBitmap(BitmapFactory.decodeByteArray(skinPng, 0, skinPng.length));
                // 缓存一份，下次打开直接恢复（相册 URI 有时效问题）
                File cache = new File(getFilesDir(), SK_CACHE);
                OutputStream os = new FileOutputStream(cache);
                try {
                    os.write(skinPng);
                } finally {
                    os.close();
                }
                log("皮肤：" + skinLabel + " " + sz[0] + "x" + sz[1]);
                saveState();
            } catch (Exception e) {
                skinPng = null;
                new AlertDialog.Builder(this)
                        .setTitle("这张图不能用")
                        .setMessage(String.valueOf(e.getMessage()))
                        .setPositiveButton("知道了", null)
                        .show();
            }
        }
    }

    private String displayName(Uri uri) {
        Cursor c = null;
        try {
            c = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME},
                    null, null, null);
            if (c != null && c.moveToFirst()) {
                String s = c.getString(0);
                if (s != null && !s.isEmpty()) return s;
            }
        } catch (Exception ignored) {
        } finally {
            if (c != null) c.close();
        }
        String p = uri.getLastPathSegment();
        return p == null ? "unknown" : p;
    }

    private long sizeOf(Uri uri) {
        Cursor c = null;
        try {
            c = getContentResolver().query(uri, new String[]{OpenableColumns.SIZE},
                    null, null, null);
            if (c != null && c.moveToFirst() && !c.isNull(0)) return c.getLong(0);
        } catch (Exception ignored) {
        } finally {
            if (c != null) c.close();
        }
        return -1;
    }

    // ================================================================== 源包体检

    /** 体检结果。 */
    private static final class SourceInfo {
        String pkg, versionName;
        long size;
        boolean hasSkindefs;
        int langCount;
        String zipError;
        ApkSignerHelper.ApkSignerInfo signer;
    }

    private void startPrepare() {
        final int seq = ++prepareSeq;
        showSourceInfo(getString(R.string.source_preparing), getColor(R.color.src_warn));
        new Thread(() -> prepareSource(seq), "mc-prepare").start();
    }

    /**
     * 把源包拷到本地工作目录（生成时也要用，不算白干），然后读包信息、签名与关键文件。
     * 结果按 seq 判断是否已过期——用户可能又选了别的包。
     */
    private void prepareSource(int seq) {
        try {
            File base = getExternalFilesDir(null);
            if (base == null) base = getFilesDir();
            File workDir = new File(base, "work");
            //noinspection ResultOfMethodCallIgnored
            workDir.mkdirs();
            File dst = new File(workDir, "input.apk");

            if (!inputCacheValid(dst)) {
                stage("准备源 APK：拷贝到本地…");
                copyUri(apkUri, dst, apkSize, 0.0, 1.0, 0.0);
                if (apkSize <= 0) apkSize = dst.length();
                copiedInput = dst;
                lastCopiedFrom = apkUri;
                lastCopiedSize = apkSize;
            } else {
                copiedInput = dst;
            }
            if (seq != prepareSeq) return;

            SourceInfo info = inspect(dst);
            if (seq != prepareSeq) return;
            if (apkSize <= 0) apkSize = info.size;
            ui.post(() -> {
                renderSourceInfo(info);
                tvApk.setText(apkName + "\n" + fmt(apkSize));
                saveState();
            });
        } catch (Throwable e) {
            final String msg = String.valueOf(e.getMessage());
            if (seq != prepareSeq) return;
            ui.post(() -> showSourceInfo(getString(R.string.src_prepare_failed, msg),
                    getColor(R.color.src_bad)));
            log("源 APK 体检失败：" + msg);
        } finally {
            if (seq == prepareSeq) ui.post(() -> tvStatus.setText(""));
        }
    }

    private boolean inputCacheValid(File dst) {
        return dst.isFile() && dst.length() > 0
                && lastCopiedFrom != null && lastCopiedFrom.equals(apkUri)
                && lastCopiedSize == apkSize;
    }

    private SourceInfo inspect(File apk) {
        SourceInfo si = new SourceInfo();
        si.size = apk.length();

        // 1) 包名 / 版本 —— 只是给用户看的辅助信息，读不到就不显示
        try {
            PackageInfo pi = getPackageManager()
                    .getPackageArchiveInfo(apk.getAbsolutePath(), 0);
            if (pi != null) {
                si.pkg = pi.packageName;
                si.versionName = pi.versionName;
            }
        } catch (Throwable ignored) {
        }

        // 2) 签名 —— 关键信息，用 apksig 自己解析。
        //    不用 PackageManager.getPackageArchiveInfo：它受 Android 11+ 的包可见性影响，
        //    可能直接返回 null，那就白做了。
        si.signer = ApkSignerHelper.inspectSigner(apk);

        // 3) 结构体检：本工具要改的那几个文件到底在不在
        ZipFile z = null;
        try {
            z = new ZipFile(apk);
            si.hasSkindefs = z.getEntry(ApkPatcher.P_SKINDEFS) != null;
            int n = 0;
            for (String p : ApkPatcher.P_LANGS) {
                if (z.getEntry(p) != null) n++;
            }
            si.langCount = n;
        } catch (Throwable e) {
            si.zipError = String.valueOf(e.getMessage());
        } finally {
            if (z != null) {
                try {
                    z.close();
                } catch (IOException ignored) {
                }
            }
        }
        return si;
    }

    private void renderSourceInfo(SourceInfo si) {
        StringBuilder sb = new StringBuilder();
        int level = 0;   // 0=ok 1=warn 2=bad

        if (si.pkg != null) {
            sb.append(getString(R.string.src_line_head,
                    si.pkg, si.versionName == null ? "?" : si.versionName));
        } else {
            sb.append(getString(R.string.src_line_size, fmt(si.size)));
            level = 1;
        }
        sb.append('\n').append(getString(R.string.src_line_size, fmt(si.size)));

        // 签名：和内置密钥指纹动态比对
        sb.append('\n');
        String signerSha = si.signer == null ? null : si.signer.certSha256;
        if (signerSha == null) {
            sb.append(getString(R.string.src_sig_unknown));
            if (level < 1) level = 1;
        } else if (bundledSha != null && bundledSha.equalsIgnoreCase(signerSha)) {
            sb.append(getString(R.string.src_sig_same));
        } else {
            sb.append(getString(R.string.src_sig_diff));
            level = 1;
        }
        if (signerSha != null && si.signer != null && !si.signer.verified) {
            sb.append('\n').append(getString(R.string.src_sig_invalid));
            level = 1;
        }

        // 结构
        sb.append('\n');
        if (si.zipError != null) {
            sb.append(getString(R.string.src_struct_bad, si.zipError));
            level = 2;
        } else if (si.hasSkindefs && si.langCount > 0) {
            sb.append(getString(R.string.src_struct_ok, si.langCount));
        } else if (!si.hasSkindefs && si.langCount == 0) {
            sb.append(getString(R.string.src_struct_bad,
                    getString(R.string.src_missing_skindefs) + "；" + getString(R.string.src_missing_lang)));
            level = 2;
        } else {
            String miss = si.hasSkindefs
                    ? getString(R.string.src_missing_lang)
                    : getString(R.string.src_missing_skindefs);
            sb.append(getString(R.string.src_struct_part, miss));
            if (level < 1) level = 1;
        }

        int color = getColor(level == 0 ? R.color.src_ok
                : level == 1 ? R.color.src_warn : R.color.src_bad);
        showSourceInfo(sb.toString(), color);
        log("源 APK 体检：\n  包名 " + si.pkg + "\n  版本 " + si.versionName
                + "\n  签名 " + (signerSha == null ? "未知" : signerSha.substring(0, 16) + "…"
                + (si.signer.verified ? "(校验通过)" : "(校验未通过)"))
                + " skindefs=" + si.hasSkindefs + " lang=" + si.langCount);
        if (si.signer != null && si.signer.error != null) {
            log("签名解析提示：" + si.signer.error);
        }
    }

    private void showSourceInfo(String text, int color) {
        tvSourceInfo.setText(text);
        tvSourceInfo.setTextColor(color);
        tvSourceInfo.setVisibility(View.VISIBLE);
    }

    // ================================================================== 皮肤解码

    /**
     * 相册里挑到的图统一转成 PNG 字节。
     * 两个关键点：强制 ARGB_8888（默认可能解成 RGB_565，皮肤的透明像素会被吃掉）；
     * 尺寸必须是 64x64 或 128x128（基岩版只认这两种）。
     */
    private byte[] decodeSkin(Uri uri) throws IOException {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        InputStream in1 = getContentResolver().openInputStream(uri);
        if (in1 == null) throw new IOException("读不到这张图片");
        try {
            BitmapFactory.decodeStream(in1, null, bounds);
        } finally {
            in1.close();
        }
        int w = bounds.outWidth, h = bounds.outHeight;
        if (w <= 0 || h <= 0) throw new IOException("这张图片无法解析，换一张试试");
        if (!((w == 64 && h == 64) || (w == 128 && h == 128))) {
            throw new IOException("皮肤必须是 64x64 或 128x128，这张是 " + w + "x" + h
                    + "。\n可以先用图片编辑器裁成这两种尺寸再导入。");
        }

        BitmapFactory.Options opts = new BitmapFactory.Options();
        opts.inPreferredConfig = Bitmap.Config.ARGB_8888;
        opts.inScaled = false;
        InputStream in2 = getContentResolver().openInputStream(uri);
        if (in2 == null) throw new IOException("读不到这张图片");
        Bitmap bm;
        try {
            bm = BitmapFactory.decodeStream(in2, null, opts);
        } finally {
            in2.close();
        }
        if (bm == null) throw new IOException("这张图片解码失败");
        if (bm.getWidth() != w || bm.getHeight() != h) {
            Bitmap scaled = Bitmap.createScaledBitmap(bm, w, h, false);
            bm.recycle();
            bm = scaled;
        }
        ByteArrayOutputStream bos = new ByteArrayOutputStream(64 * 1024);
        bm.compress(Bitmap.CompressFormat.PNG, 100, bos);
        bm.recycle();
        return bos.toByteArray();
    }

    // ================================================================== 生成

    private void startGenerate() {
        if (running) {
            cancelled = true;
            tvStatus.setText("正在取消…");
            return;
        }
        if (apkUri == null) {
            toast(getString(R.string.need_apk_first));
            return;
        }
        if (!cbRename.isChecked() && !cbSkin.isChecked() && !cbPack.isChecked()) {
            toast(getString(R.string.need_change));
            return;
        }
        if (cbSkin.isChecked() && skinPng == null) {
            toast("勾了换皮肤，但还没选图片");
            return;
        }
        if (cbPack.isChecked() && packUris.isEmpty()) {
            toast("勾了换资源包，但还没选文件");
            return;
        }
        if (cbRename.isChecked() && etName.getText().toString().trim().isEmpty()) {
            toast("勾了改名，但名字是空的");
            return;
        }

        cancelled = false;
        running = true;
        getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        btnGenerate.setText(R.string.cancel);
        btnInstall.setEnabled(false);
        logBuf.setLength(0);
        tvLog.setText("");
        progress.setProgress(0);

        // 在 UI 线程把界面状态快照下来，后台线程只碰这些 final 值
        final boolean doRename = cbRename.isChecked();
        final String name = etName.getText().toString().trim();
        final boolean doSkin = cbSkin.isChecked();
        final byte[] skin = skinPng;
        final boolean slim = rbSlim.isChecked();
        final boolean doPack = cbPack.isChecked();
        final boolean autoExport = cbAutoExport.isChecked();
        final List<Uri> packs = new ArrayList<Uri>(packUris);

        new Thread(() -> work(doRename, name, doSkin, skin, slim, doPack, autoExport, packs),
                "mc-patch").start();
    }

    private void work(boolean doRename, String name, boolean doSkin, byte[] skin,
                      boolean slim, boolean doPack, boolean autoExport, List<Uri> packs) {
        long t0 = System.currentTimeMillis();
        boolean wasCancelled = false;
        try {
            PatchSpec spec = new PatchSpec();
            spec.renameEnabled = doRename;
            spec.playerName = name;
            spec.skinEnabled = doSkin;
            spec.skinPng = skin;
            spec.slimArms = slim;
            spec.packEnabled = doPack;
            // 导入界面总是注入：它只是给游戏 H5 加一个「导入世界」按钮，
            // 否则用户拿到的改包里没有这个入口，导入功能就用不了。
            spec.importScript = loadImportScript();

            // 换皮肤/改手臂这条最容易白忙一场，先把话说清楚（见 README 2.2.1）。
            if (doSkin) {
                log("换皮肤：覆盖安装即可，贴图会变 ✔");
                log("手臂粗细：覆盖安装不会变，用第 6 节换（不用卸载）");
                log("⚠️ 真要卸载游戏：卸载会清空 Android/data，请先备份存档");
            }

            // ---- 0. 先校验签名材料 ----
            // 放在最前面：签名材料有问题就别浪费几十秒去拷一个 165 MB 的包。
            stage("校验签名材料…");
            loadSignerMaterial();
            spec.signerPrivateKeyPkcs8 = signerKey;
            spec.signerCertificate = signerCert;
            log("签名证书指纹 " + ApkSignerHelper.selfTest(spec));
            if (ApkSignerHelper.matchesV19(spec)) {
                log("  → 和你之前那份改包同签名，可以直接覆盖安装");
            } else if (ApkSignerHelper.matchesExampleKey(spec)) {
                log("⚠️ 正在使用【内置示例密钥】—— 它是公开的，谁都能签出能覆盖安装到你手机上的包。");
                log("   想换成自己的：在电脑上跑 tools/genkey.ps1（或用 tools/genkey.sh），");
                log("   再把重新构建出来的工具装上。注意：一旦用某个密钥装过改包，");
                log("   以后就得一直用同一个，否则只能卸载重装（会丢存档）。");
            }

            // ---- 1. 源 APK（体检时通常已经拷好了）----
            File base = getExternalFilesDir(null);
            if (base == null) base = getFilesDir();
            final long need = (apkSize > 0 ? apkSize : 180L * 1024 * 1024) * 2 + 80L * 1024 * 1024;
            if (base.getUsableSpace() > 0 && base.getUsableSpace() < need) {
                throw new IOException("存储空间不足，还需要大约 " + fmt(need - base.getUsableSpace()));
            }
            File workDir = new File(base, "work");
            //noinspection ResultOfMethodCallIgnored
            workDir.mkdirs();
            File dst = new File(workDir, "input.apk");
            if (inputCacheValid(dst)) {
                copiedInput = dst;
                log("复用已准备的源 APK");
            } else {
                stage("拷贝源 APK 到本地工作目录…");
                copyUri(apkUri, dst, apkSize, 0.0, 0.18, 0.0);
                if (apkSize <= 0) apkSize = dst.length();
                copiedInput = dst;
                lastCopiedFrom = apkUri;
                lastCopiedSize = apkSize;
            }
            spec.srcApk = copiedInput;

            // ---- 2. 资源包（可多个，按顺序叠加）----
            if (spec.packEnabled) {
                for (int i = 0; i < packs.size(); i++) {
                    File pf = new File(workDir, "pack" + (i + 1) + ".zip");
                    copyUri(packs.get(i), pf, sizeOf(packs.get(i)), 0.18, 0.22, 0.0);
                    spec.resourcePacks.add(pf);
                }
            }

            // ---- 3. 输出路径 ----
            String stamp = new SimpleDateFormat("yyyyMMdd-HHmm", Locale.US).format(new Date());
            String srcBase = apkName.toLowerCase(Locale.ROOT).endsWith(".apk")
                    ? apkName.substring(0, apkName.length() - 4) : apkName;
            if (srcBase.length() > 48) srcBase = srcBase.substring(0, 48);
            String outName = sanitize(srcBase) + "-mod-" + stamp + ".apk";
            spec.dstApk = new File(ShareFileProvider.dir(this, ShareFileProvider.KIND_OUTPUT), outName);

            // ---- 4. 干活 ----
            ApkPatcher.Result r = ApkPatcher.patch(spec, new PatchLog() {
                @Override
                public void stage(String text) {
                    if (cancelled) throw new RuntimeException("已取消");
                    MainActivity.this.stage(text);
                }

                @Override
                public void detail(String text) {
                    MainActivity.this.log("  " + text);
                }

                @Override
                public void progress(double f) {
                    int v = (int) ((0.22 + f * 0.78) * 1000);
                    ui.post(() -> progress.setProgress(Math.max(0, Math.min(1000, v))));
                }
            });

            outputApk = spec.dstApk;
            final String msg = getString(R.string.done, outputApk.getName());
            final String skinWarn = doSkin ? "\n" + getString(R.string.skin_reinstall_warn_short) : "";
            ui.post(() -> {
                tvStatus.setText(msg + "\n" + r.toString() + "\n"
                        + fmt(r.outSize) + "，耗时 " + (r.millis / 1000.0) + " 秒" + skinWarn);
                btnInstall.setEnabled(true);
                progressDone();
            });
            log("完成：" + outputApk.getAbsolutePath());
            log(r.toString());
            log("源包大小 " + fmt(r.srcSize) + " → 产出大小 " + fmt(r.outSize));
            if (doSkin) log(getString(R.string.skin_reinstall_warn_short));

            if (autoExport) {
                ui.post(this::doExport);
            }
        } catch (Throwable e) {
            final String m = e.getMessage() == null ? e.toString() : e.getMessage();
            wasCancelled = cancelled || "已取消".equals(m);
            log(wasCancelled ? "已取消" : ("失败: " + m));
            if (!wasCancelled) {
                ui.post(() -> {
                    tvStatus.setText("失败");
                    new AlertDialog.Builder(MainActivity.this)
                            .setTitle("生成失败")
                            .setMessage(m)
                            .setPositiveButton("知道了", null)
                            .show();
                });
            } else {
                ui.post(() -> tvStatus.setText("已取消"));
            }
        } finally {
            running = false;
            final long dt = System.currentTimeMillis() - t0;
            final boolean cx = wasCancelled;
            ui.post(() -> {
                btnGenerate.setText(R.string.generate);
                getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                if (cx) tvStatus.setText("已取消");
            });
            log("结束，用时 " + dt + " 毫秒");
        }
    }

    private static String sanitize(String s) {        StringBuilder sb = new StringBuilder(s.length());
        for (char c : s.toCharArray()) {
            sb.append(Character.isLetterOrDigit(c) || c == '.' || c == '-' || c == '_' ? c : '_');
        }
        return sb.toString();
    }

    /**
     * 进度到 1000 = 这件事做完了：顺手把进度条藏起来。
     *
     * <p>进度条平时是隐藏的（空闲时那条 0% 的灰杠看起来像分隔线，用户提过），
     * 由 {@link #stage(String)} 在任务开始时显示。
     * <b>必须是方法调用</b>：它会被写进 `ui.post(() -> progressDone())` 这种一行 lambda 里，
     * 往那里塞两条语句会编译不过（踩过）。
     */
    private void progressDone() {
        progress.setProgress(1000);
        findViewById(R.id.progress).setVisibility(View.GONE);
    }

    private void stage(String text) {
        taskRunning = true;        // 先置位，这样 log 里的"自动展开日志"才生效
        log("[" + text + "]");
        ui.post(() -> {
            tvStatus.setText(text);
            // 任务开始就把进度条亮出来；完成时由 progressDone() 收起
            findViewById(R.id.progress).setVisibility(View.VISIBLE);
        });
    }

    private void log(String s) {
        logBuf.append(s).append('\n');
        final String all = logBuf.toString();
        ui.post(() -> {
            tvLog.setText(all);
            // 只有真正干活时才自动展开日志区。启动时那几行「就绪…」不展开，
            // 否则一进页面日志就占掉半屏（用户反馈过页面太长）。
            if (taskRunning) openLogBox();
        });
    }

    private void copyUri(Uri from, File to, long knownSize, double pFrom, double pTo, double within)
            throws IOException {
        InputStream in = getContentResolver().openInputStream(from);
        if (in == null) throw new IOException("打不开选中的文件（可能上次选的已经失效，请重新选一次）");
        BufferedInputStream bin = new BufferedInputStream(in, 1 << 20);
        OutputStream out = new BufferedOutputStream(new FileOutputStream(to), 1 << 20);
        try {
            byte[] buf = new byte[1 << 20];
            long total = 0;
            long nextTick = 0;
            int n;
            while ((n = bin.read(buf)) > 0) {
                if (cancelled) throw new RuntimeException("已取消");
                out.write(buf, 0, n);
                total += n;
                if (System.currentTimeMillis() >= nextTick) {
                    nextTick = System.currentTimeMillis() + 200;
                    if (knownSize > 0) {
                        double f = pFrom + (pTo - pFrom) * ((double) total / knownSize) + within;
                        final int v = (int) (Math.min(1.0, Math.max(0.0, f)) * 1000);
                        ui.post(() -> progress.setProgress(v));
                    }
                }
            }
        } finally {
            try {
                out.close();
            } catch (IOException ignored) {
            }
            try {
                bin.close();
            } catch (IOException ignored) {
            }
        }
    }

    // ================================================================== 签名材料

    private void loadSignerMaterial() throws IOException {
        if (signerKey != null && signerCert != null) return;
        signerKey = readAsset(ASSET_KEY);
        signerCert = readAsset(ASSET_CERT);
    }

    private byte[] readAsset(String name) throws IOException {
        InputStream in = getAssets().open(name);
        try {
            return ApkPatcher.readAll(in);
        } finally {
            try {
                in.close();
            } catch (IOException ignored) {
            }
        }
    }

    private void checkSigner() {
        try {
            loadSignerMaterial();
            PatchSpec s = new PatchSpec();
            s.signerPrivateKeyPkcs8 = signerKey;
            s.signerCertificate = signerCert;
            bundledSha = ApkSignerHelper.selfTest(s);
            log("内置签名证书 SHA-256：" + bundledSha);
            if (ApkSignerHelper.V19_CERT_SHA256.equalsIgnoreCase(bundledSha)) {
                tvSign.setText(getString(R.string.sign_ok));
            } else if (ApkSignerHelper.EXAMPLE_CERT_SHA256.equalsIgnoreCase(bundledSha)) {
                // 公开仓库里带的是示例密钥：能跑，但谁都能签出能覆盖安装的包
                tvSign.setText(getString(R.string.sign_example));
                log("⚠️ 这是仓库里公开的【示例密钥】—— 谁都能签出能覆盖安装到你手机上的包。");
                log("   想换成自己的：电脑上跑 tools/genkey.ps1（Linux/macOS 用 tools/genkey.sh），");
                log("   再重新构建工具。详见 app/src/main/assets/README.md。");
            } else {
                tvSign.setText(getString(R.string.sign_bad));
                log("内置密钥与 minecraft 改包签名不同 → 安装前需卸载原版");
            }
        } catch (Throwable e) {
            String msg = String.valueOf(e.getMessage());
            boolean missing = (e instanceof java.io.FileNotFoundException)
                    || msg.contains("mc-patch-key") || msg.contains("mc-patch-cert");
            if (missing) {
                // 公开仓库刻意不带私钥，所以这是"还没生成密钥"的正常状态，
                // 必须给出可操作的提示，而不是一句看不懂的读取失败。
                tvSign.setText(getString(R.string.sign_missing));
                log("没有找到签名密钥（assets/mc-patch-key.pk8 与 mc-patch-cert.pem）。");
                log("  生成方法：电脑上跑 tools/genkey.ps1（Linux/macOS 用 tools/genkey.sh），再重新构建工具。");
                log("  详见 app/src/main/assets/README.md。");
            } else {
                tvSign.setText(getString(R.string.sign_broken, msg));
                log("读取内置签名材料失败：" + e);
            }
        }
    }

    // ================================================================== 导入存档（不用 root）

    /**
     * 读取工具 APK 里的「导入界面」脚本（{@code assets/mc-import.js}）。
     *
     * <p>每次打补丁都会把它注入到游戏 H5 首页的末尾，于是游戏里会多一个
     * 「导入世界」按钮。为什么要这样做：网易版的世界列表是个网页，它读的是
     * 网易自己的「世界记录」而不是扫目录；而 H5 能调的
     * {@code h5adaptor.decompress_map} 目标目录是任意的，
     * 所以把「世界记录 JSON」也打成一个 zip 就能直接写进记录目录 ——
     * <b>全程不需要 root</b>。详见 README 第 9 节。
     */
    private byte[] loadImportScript() {
        InputStream in = null;
        try {
            in = getAssets().open("mc-import.js");
            return ApkPatcher.readAll(in);
        } catch (Throwable e) {
            log("读取导入界面脚本失败（不影响其它改动）：" + e.getMessage());
            return null;
        } finally {
            if (in != null) {
                try {
                    in.close();
                } catch (IOException ignored) {
                }
            }
        }
    }

    private void startImport() {
        if (importUri == null) {
            toast(getString(R.string.import_need_file));
            return;
        }
        final Uri src = importUri;
        final String name = importName;
        final boolean downgrade = cbDowngrade.isChecked();
        findViewById(R.id.btnDoImport).setEnabled(false);
        progress.setProgress(0);
        new Thread(() -> prepareImport(src, name, downgrade), "mc-import").start();
    }

    /**
     * 把外部世界处理成「游戏里一键导入」用的几个包，写进**游戏能读到的共享目录**。
     *
     * <p>位置是 {@code /sdcard/Android/media/com.mctool.mcpatch/}，由 {@link ShareWriter}
     * 负责。为什么不是 {@code Download/}：App 写进 {@code Download/} 的文件权限是
     * {@code -rwxrwx--- owner:media_rw}，别的 App 按路径打开会 <b>EACCES</b> ——
     * 真机上就是卡在这里（{@code [Errno 13] Permission denied}）。
     * 详见 {@link ShareWriter} 的注释。
     */
    private void prepareImport(Uri src, String name, boolean downgrade) {
        try {
            File base = getExternalFilesDir(null);
            if (base == null) base = getFilesDir();
            File workDir = new File(base, "work");
            //noinspection ResultOfMethodCallIgnored
            workDir.mkdirs();
            File local = new File(workDir, "import-world.zip");

            stage(getString(R.string.import_copying));
            copyUri(src, local, sizeOf(src), 0.0, 0.35, 0.0);

            final int slot = nextSlot();
            final String slotId = "mcw" + slot;
            stage(getString(R.string.import_preparing, slotId));

            WorldImportPrep.Result r = WorldImportPrep.prepare(local, slotId, downgrade);

            log("世界名：" + r.levelName
                    + (r.worldPrefix.isEmpty() ? "" : "（包里有外壳目录 " + r.worldPrefix + "）"));
            log("存档体检：" + WorldImportPrep.describe(r.before));
            log("客户端能力：" + WorldImportPrep.clientDesc());
            if (r.patchedBytes >= 0) {
                log("已自动降级 → " + WorldImportPrep.describe(r.after)
                        + "（改动了 " + r.patchedBytes + " 个整数字段）");
            } else if (r.warning != null) {
                log("提示：" + r.warning);
            }
            log("拆分结果：" + r.parts.size() + " 个包 / " + r.files + " 个文件 / " + fmt(r.bytes));

            // 先清掉 Download 里【所有】mcweb_* 残留（不只当前槽位）。
            // 游戏侧 H5 从槽位 1 依次扫：前面只要留着一个"半截"槽位
            // （比如只有 _db 没有 _root），它就会卡在那一格，后面的完整包永远轮不到 ——
            // 真机现象就是"怎么点都导入不了"（实测被残缺的槽位 4 挡住过完整的槽位 5）。
            int cleaned = ShareWriter.purgeAll(this);
            if (cleaned > 0) log("  清理旧包残留 " + cleaned + " 个");

            final int total = r.parts.size() + 1;
            int idx = 0;
            for (WorldImportPrep.Part p : r.parts) {
                idx++;
                stage(getString(R.string.import_writing, idx, total));
                String fn = "mcweb_" + slot + "_" + p.suffix;
                ShareWriter.write(this, fn, p.data);
                log("  写入 " + fn + ShareWriter.EXT + "  (" + fmt(p.data.length) + ")");
                // 本方法跑在后台线程（new Thread(() -> prepareImport(...))），
                // 碰任何 View 都必须回主线程，否则抛 CalledFromWrongThreadException
                // —— 真机上表现成「导入准备失败」而包其实已经写好了（第一次必失败）。
                final int pv = (int) ((0.35 + 0.6 * idx / (double) total) * 1000);
                ui.post(() -> progress.setProgress(pv));
            }
            stage(getString(R.string.import_writing, total, total));
            ShareWriter.write(this, "mcweb_" + slot + "_record", r.recordZip);
            log("  写入 mcweb_" + slot + "_record" + ShareWriter.EXT + "  (世界记录)");
            log("  位置：" + ShareWriter.dirDesc());
            ui.post(this::progressDone);

            final String msg = getString(R.string.import_ready, slotId, r.levelName);
            ui.post(() -> {
                tvStatus.setText(msg);
                toast(getString(R.string.import_ready_short));
            });
        } catch (Throwable e) {
            final String m = String.valueOf(e.getMessage());
            log(getString(R.string.import_failed, m));
            ui.post(() -> toast(getString(R.string.import_failed, m)));
        } finally {
            ui.post(() -> {
                findViewById(R.id.btnDoImport).setEnabled(true);
                progress.setProgress(0);
            });
        }
    }

    /**
     * 挑一个槽位（1..{@link WorldImportPrep#SLOTS}）。
     *
     * <p>顺序很重要：
     * <ol>
     *   <li><b>先找"还没被游戏取走"的槽位</b>（{@code mcweb_<n>_root} 还在）。
     *       有就直接<b>复用并覆盖</b>它 —— 否则用户每点一次「② 准备导入」就多占一个槽位，
     *       之后每点一次「导入世界」就会把那些残留的包依次导进来，凭空多出一堆世界
     *       （真机上手点三次踩过）。</li>
     *   <li>都空着，才按轮转计数器拿一个新槽位。游戏解压成功后会<b>消耗掉源包</b>，
     *       所以"槽位空着"天然等价于"这个槽位没被用过"，不需要额外记状态。</li>
     * </ol>
     */
    private int nextSlot() {
        for (int s = 1; s <= WorldImportPrep.SLOTS; s++) {
            if (ShareWriter.existsAny(this, "mcweb_" + s + "_root")) {
                log("复用槽位 " + s + "（上次准备的包还没被游戏取走，直接覆盖）");
                return s;
            }
        }
        int cur = prefs.getInt("import_slot", 1);
        if (cur < 1 || cur > WorldImportPrep.SLOTS) cur = 1;
        prefs.edit().putInt("import_slot",
                cur >= WorldImportPrep.SLOTS ? 1 : cur + 1).apply();
        return cur;
    }

    // ================================================================== 安装/导出/日志

    /**
     * 「立即安装」入口：先弹一句提醒再装。
     *
     * <p>覆盖安装本身不丢存档，但如果签名不同、系统要求先卸载，卸载会清空
     * {@code Android/data}（存档全在里面）。实测丢过一次，所以这里必须提醒。
     */
    private void doInstall() {
        if (outputApk == null || !outputApk.isFile()) return;
        new android.app.AlertDialog.Builder(this)
                .setTitle(R.string.install_confirm_title)
                .setMessage(R.string.install_confirm_msg)
                .setPositiveButton("继续安装", (d, w) -> reallyInstall())
                .setNegativeButton("取消", null)
                .show();
    }

    private void reallyInstall() {
        if (outputApk == null || !outputApk.isFile()) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            PackageManager pm = getPackageManager();
            if (!pm.canRequestPackageInstalls()) {
                toast(getString(R.string.install_unknown_sources));
                try {
                    startActivityForResult(new Intent(
                                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                                    Uri.parse("package:" + getPackageName())),
                            REQ_INSTALL_PERM);
                } catch (Exception e) {
                    toast("请到系统设置里允许「安装未知应用」");
                }
                return;
            }
        }
        try {
            Uri uri = ShareFileProvider.uriFor(this, outputApk);
            Intent i = new Intent(Intent.ACTION_VIEW);
            i.setDataAndType(uri, "application/vnd.android.package-archive");
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Exception e) {
            toast("调起安装器失败：" + e.getMessage());
            log("调起安装器失败，可到 Download 目录手动点安装");
        }
    }

    private void doCopyLog() {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm == null) {
                toast("剪贴板不可用");
                return;
            }
            StringBuilder sb = new StringBuilder();
            sb.append("MCPatchTool 日志\n");
            sb.append("设备: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL)
                    .append(" / Android ").append(Build.VERSION.RELEASE)
                    .append(" (API ").append(Build.VERSION.SDK_INT).append(")\n");
            sb.append("外观: ").append(themeLabel()).append('\n');
            sb.append("内置签名: ").append(bundledSha == null ? "未读取" : bundledSha).append('\n');
            sb.append("源 APK: ").append(apkName).append(" (").append(fmt(apkSize)).append(")\n");
            sb.append("资源包: ").append(packNames.isEmpty() ? "无" : joinLines(packNames)).append('\n');
            sb.append("---- 日志 ----\n").append(logBuf);
            cm.setPrimaryClip(ClipData.newPlainText("MCPatchTool", sb.toString()));
            toast(getString(R.string.log_copied));
        } catch (Throwable e) {
            toast("复制失败：" + e.getMessage());
        }
    }

    private void doExport() {
        if (outputApk == null || !outputApk.isFile()) return;
        final File src = outputApk;
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
                && checkSelfPermission(android.Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.WRITE_EXTERNAL_STORAGE},
                    REQ_STORAGE_PERM);
            return;
        }
        new Thread(() -> {
            try {
                // 名字要能一眼和 Download 里那些给游戏读的 .png 区分开
                String name = "MCPatchTool-输出的改包-"
                        + new java.text.SimpleDateFormat("yyyyMMdd-HHmm", java.util.Locale.US)
                        .format(new java.util.Date())
                        + ".apk";
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues cv = new ContentValues();
                    cv.put(MediaStore.Downloads.DISPLAY_NAME, name);
                    cv.put(MediaStore.Downloads.MIME_TYPE, "application/vnd.android.package-archive");
                    cv.put(MediaStore.Downloads.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                    Uri item = getContentResolver().insert(
                            MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                    if (item == null) throw new IOException("无法在 Download 目录创建文件");
                    OutputStream os = getContentResolver().openOutputStream(item);
                    if (os == null) throw new IOException("无法写入 Download 目录");
                    try {
                        copyFile(src, os);
                    } finally {
                        os.close();
                    }
                } else {
                    File dir = Environment.getExternalStoragePublicDirectory(
                            Environment.DIRECTORY_DOWNLOADS);
                    //noinspection ResultOfMethodCallIgnored
                    dir.mkdirs();
                    File dst = new File(dir, name);
                    OutputStream os = new FileOutputStream(dst);
                    try {
                        copyFile(src, os);
                    } finally {
                        os.close();
                    }
                    android.media.MediaScannerConnection.scanFile(this,
                            new String[]{dst.getAbsolutePath()},
                            new String[]{"application/vnd.android.package-archive"}, null);
                }
                ui.post(() -> {
                    toast(getString(R.string.auto_exported, name));
                    log("已导出到 Download/" + name);
                });
            } catch (Throwable e) {
                ui.post(() -> toast("导出失败：" + e.getMessage()));
            }
        }, "mc-export").start();
    }

    private static void copyFile(File src, OutputStream os) throws IOException {
        InputStream in = new java.io.FileInputStream(src);
        BufferedInputStream bin = new BufferedInputStream(in, 1 << 20);
        try {
            byte[] buf = new byte[1 << 20];
            int n;
            while ((n = bin.read(buf)) > 0) os.write(buf, 0, n);
        } finally {
            bin.close();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQ_STORAGE_PERM && results.length > 0
                && results[0] == PackageManager.PERMISSION_GRANTED) {
            doExport();
        } else if (requestCode == REQ_STORAGE_PERM) {
            toast("没有存储权限，无法自动另存到 Download 目录");
        }
    }

    // ================================================================== 杂项

    private void toast(String s) {
        Toast.makeText(this, s, Toast.LENGTH_LONG).show();
    }

    private static String fmt(long bytes) {
        if (bytes < 0) return "未知大小";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format(Locale.US, "%.1f KB", bytes / 1024.0);
        if (bytes < 1024L * 1024 * 1024) return String.format(Locale.US, "%.1f MB", bytes / 1048576.0);
        return String.format(Locale.US, "%.2f GB", bytes / 1073741824.0);
    }
}
