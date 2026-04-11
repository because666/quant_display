#!/usr/bin/env python3
"""检查Git仓库中最大的文件"""
import subprocess
import os

def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        return result.stdout
    except Exception as e:
        return str(e)

project_dir = r"d:\量化\V2.0"

# 获取所有文件及其大小
output = run_command("git ls-files", cwd=project_dir)
files = output.strip().split('\n')

file_sizes = []
for f in files:
    if f:
        size_output = run_command(f'git cat-file -s :"{f}"', cwd=project_dir)
        try:
            size = int(size_output.strip())
            file_sizes.append((size, f))
        except:
            pass

# 排序并显示最大的20个文件
file_sizes.sort(reverse=True)
print("最大的20个文件:")
for size, f in file_sizes[:20]:
    print(f"{size/1024/1024:.2f} MB - {f}")

# 统计总大小
total_size = sum(s for s, _ in file_sizes)
print(f"\n总大小: {total_size/1024/1024:.2f} MB")
