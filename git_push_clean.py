#!/usr/bin/env python3
"""
GitHub推送脚本 - 清理大文件后推送
"""
import subprocess
import os
import sys
import shutil

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
    backup_dir = r"d:\量化\V2.0_backup"
    
    print("=== 清理Git历史并重新推送 ===")
    
    # 备份重要文件
    print("备份.gitignore...")
    gitignore_src = os.path.join(project_dir, ".gitignore")
    gitignore_backup = os.path.join(project_dir, ".gitignore.backup")
    if os.path.exists(gitignore_src):
        shutil.copy2(gitignore_src, gitignore_backup)
    
    # 完全删除.git目录重新开始
    print("删除旧的Git仓库...")
    git_dir = os.path.join(project_dir, ".git")
    if os.path.exists(git_dir):
        # 使用系统命令删除
        run_command(f'rmdir /s /q "{git_dir}"', cwd=project_dir)
    
    # 初始化新的Git仓库
    print("初始化新的Git仓库...")
    code, out, err = run_command("git init", cwd=project_dir)
    if code != 0:
        print(f"初始化失败: {err}")
        return 1
    print("初始化成功")
    
    # 恢复.gitignore
    if os.path.exists(gitignore_backup):
        shutil.copy2(gitignore_backup, gitignore_src)
        os.remove(gitignore_backup)
        print("恢复.gitignore")
    
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
    if code != 0:
        print(f"添加远程仓库失败: {err}")
    else:
        print("远程仓库配置成功")
    
    # 添加文件（根据.gitignore过滤）
    print("添加文件到暂存区（根据.gitignore过滤大文件）...")
    code, out, err = run_command("git add .", cwd=project_dir, timeout=180)
    if code != 0:
        print(f"添加文件失败: {err}")
        return 1
    print("文件添加成功")
    
    # 检查状态
    code, out, err = run_command("git status --short | wc -l", cwd=project_dir)
    print(f"待提交文件数: {out.strip()}")
    
    # 提交
    print("提交更改...")
    code, out, err = run_command(
        'git commit -m "feat(init): 量化投资选股策略项目初始化"',
        cwd=project_dir,
        timeout=120
    )
    if code != 0:
        print(f"提交失败: {err}")
        return 1
    print("提交成功")
    
    # 推送到main分支
    print("推送到GitHub...")
    code, out, err = run_command(
        "git push -u origin master:main --force",
        cwd=project_dir,
        timeout=300
    )
    if code != 0:
        print(f"推送失败: {err}")
        print(f"输出: {out}")
        return 1
    print("推送成功！")
    print(out)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
