#!/usr/bin/env python3
"""监控处理进度"""
import time
import os
import subprocess

result_file = "/Users/weilingkeji/360安全云盘同步版/000-海外/01-jisi/002-HangzhouLeiming/hangzhou-leiming-AI-drama/data/hangzhou-leiming/analysis/多子多福，开局就送绝美老婆/result.json"
backup_file = result_file + ".backup"

# 获取备份文件的大小
if os.path.exists(backup_file):
    backup_size = os.path.getsize(backup_file)
    backup_mtime = os.path.getmtime(backup_file)
    print(f"备份文件大小: {backup_size} bytes")
    print(f"备份文件时间: {time.ctime(backup_mtime)}")
else:
    backup_size = 0
    print("没有找到备份文件")

# 监控result文件的变化
last_size = 0
last_mtime = 0

print("\n监控处理进度...")
print("按 Ctrl+C 停止\n")

try:
    while True:
        if os.path.exists(result_file):
            current_size = os.path.getsize(result_file)
            current_mtime = os.path.getmtime(result_file)

            if current_size != last_size or current_mtime != last_mtime:
                print(f"[{time.strftime('%H:%M:%S')}] 文件已更新:")
                print(f"  大小: {current_size} bytes")
                print(f"  修改时间: {time.ctime(current_mtime)}")

                # 如果文件大小变化，可能正在写入
                if current_size > backup_size:
                    print(f"  ✓ 文件大小增加 {current_size - backup_size} bytes")

                last_size = current_size
                last_mtime = current_mtime

        time.sleep(5)  # 每5秒检查一次

except KeyboardInterrupt:
    print("\n\n监控已停止")

# 最终比较
if os.path.exists(result_file):
    final_size = os.path.getsize(result_file)
    print(f"\n最终文件大小: {final_size} bytes")

    if backup_size > 0:
        diff = final_size - backup_size
        print(f"与备份相比: {diff:+d} bytes")

        if diff > 0:
            print("✓ 文件已更新（新版本）")
        elif diff < 0:
            print("⚠ 文件被还原了？")
        else:
            print("= 文件没有变化")
