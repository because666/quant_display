#!/usr/bin/env python3
"""
GitHub推送脚本
用于将代码推送到GitHub仓库
"""
import subprocess
import os
import sys
import time

def run_command(cmd, cwd=None, timeout=60):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def main():
    project_dir = r"d:\量化\V2.0"
    
    # 检查并删除锁文件
    lock_file = os.path.join(project_dir, ".git", "index.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("已删除Git锁文件")
        except Exception as e:
            print(f"无法删除锁文件: {e}")
    
    # 配置Git
    print("配置Git...")
    run_command('git config user.email "dev@quant_display.com"', cwd=project_dir)
    run_command('git config user.name "Quant Developer"', cwd=project_dir)
    
    # 添加远程仓库
    print("配置远程仓库...")
    run_command("git remote remove origin", cwd=project_dir)
    code, out, err = run_command(
        "git remote add origin https://github.com/because666/quant_display.git",
        cwd=project_dir
    )
    if code != 0 and "already exists" not in err:
        print(f"添加远程仓库失败: {err}")
    
    # 添加文件
    print("添加文件到暂存区...")
    code, out, err = run_command("git add .", cwd=project_dir, timeout=180)
    if code != 0:
        print(f"添加文件失败: {err}")
        return 1
    print("文件添加成功")
    
    # 提交
    print("提交更改...")
    code, out, err = run_command(
        'git commit -m "feat(init): initial commit"',
        cwd=project_dir,
        timeout=120
    )
    if code != 0:
        print(f"提交失败或没有新更改: {err}")
        print(f"输出: {out}")
    else:
        print("提交成功")
        print(out)
    
    # 强制推送到main分支
    print("强制推送到GitHub...")
    code, out, err = run_command(
        "git push -u origin master:main --force",
        cwd=project_dir,
        timeout=180
    )
    if code != 0:
        print(f"推送失败: {err}")
        print(f"输出: {out}")
        return 1
    print("推送成功")
    print(out)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
