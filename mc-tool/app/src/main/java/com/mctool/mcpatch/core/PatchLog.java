package com.mctool.mcpatch.core;

/** 进度/日志回调。stage 是给用户看的粗粒度阶段，fraction 取值 0..1（负数表示不确定）。 */
public interface PatchLog {

    void stage(String text);

    default void detail(String text) {
    }

    default void progress(double fraction) {
    }

    PatchLog SILENT = new PatchLog() {
        @Override
        public void stage(String text) {
        }
    };
}
