#!/usr/bin/env python3
"""
GitHub推送脚本 - 处理锁文件问题
"""
import subprocess
import os
import sys
import time
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def remove_lock_file(project_dir):
    """尝试删除Git锁文件"""
    lock_file = os.path.join(project_dir, ".git", "index.lock")
    if os.path.exists(lock_file):
        try:
            # 尝试多种方式删除
            os.chmod(lock_file, 0o777)
            os.remove(lock_file)
            print("已删除Git锁文件")
            return True
        except Exception as e:
            print(f"无法删除锁文件: {e}")
            return False
    return True

def run_command(cmd, cwd=None, timeout=120):
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
    
    print("=== 开始推送到GitHub ===")
    
    # 删除锁文件
    if not remove_lock_file(project_dir):
        print("警告: 无法删除锁文件，尝试继续...")
    
    # 配置Git
    print("\n1. 配置Git...")
    run_command('git config user.email "dev@quant_display.com"', cwd=project_dir)
    run_command('git config user.name "Quant Developer"', cwd=project_dir)
    print("Git配置完成")
    
    # 检查远程仓库
    print("\n2. 检查远程仓库...")
    code, out, err = run_command("git remote -v", cwd=project_dir)
    if "because666/quant_display" not in out:
        print("添加远程仓库...")
        run_command("git remote remove origin", cwd=project_dir)
        run_command(
            "git remote add origin https://github.com/because666/quant_display.git",
            cwd=project_dir
        )
    print("远程仓库配置完成")
    
    # 添加文件
    print("\n3. 添加文件到暂存区...")
    # 先删除锁文件
    remove_lock_file(project_dir)
    code, out, err = run_command("git add .", cwd=project_dir, timeout=180)
    if code != 0:
        print(f"添加文件失败: {err}")
        return 1
    print("文件添加成功")
    
    # 检查状态
    code, out, err = run_command("git status --short", cwd=project_dir)
    file_count = len([l for l in out.split('\n') if l.strip()])
    print(f"待提交文件数: {file_count}")
    
    if file_count == 0:
        print("没有需要提交的文件")
        return 0
    
    # 提交
    print("\n4. 提交更改...")
    remove_lock_file(project_dir)
    code, out, err = run_command(
        'git commit -m "feat(init): 量化投资选股策略项目初始化"',
        cwd=project_dir,
        timeout=120
    )
    if code != 0:
        print(f"提交失败: {err}")
        print(f"输出: {out}")
        return 1
    print("提交成功")
    
    # 推送到main分支
    print("\n5. 推送到GitHub...")
    remove_lock_file(project_dir)
    code, out, err = run_command(
        "git push -u origin master:main --force",
        cwd=project_dir,
        timeout=300
    )
    if code != 0:
        print(f"推送失败: {err}")
        print(f"输出: {out}")
        return 1
    
    print("\n=== 推送成功！ ===")
    print(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
