"""检查 MainActivity.smali 的 onCreate 方法"""
import os, re

main_activity = r'C:\Users\Administrator\Documents\deepseek-harness\default-workspace\mc-re\smali_v17\com\mojang\minecraftpe\MainActivity.smali'

with open(main_activity, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找 onCreate 方法
in_oncreate = False
for i, line in enumerate(lines):
    if '.method public onCreate(Landroid/os/Bundle;)V' in line:
        in_oncreate = True
        print(f'=== onCreate 方法 (行 {i+1}) ===')
        # 打印前 30 行
        for j in range(i, min(i+40, len(lines))):
            print(f'{j+1}: {lines[j]}', end='')
        print()
        break
