#!/usr/bin/env python3
"""
阿不 finbot 每日收盘更新脚本
"""
import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python3")

def run_script(name, module_path):
    """运行一个python模块"""
    py = VENV_PYTHON if os.path.exists(VENV_PYTHON) else "python3"
    abs_path = os.path.join(BASE_DIR, module_path)
    result = subprocess.run([py, abs_path, "--report"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ {name} 失败:", result.stderr[:200])
        return False
    print(f"✅ {name}: {result.stdout.strip()}")
    return True

def main():
    print(f"🔄 阿不 收盘更新 | {__import__('datetime').datetime.now()}")
    print("=" * 40)
    
    # 1. 生成报告
    run_script("analyzer", "core/analyzer.py")
    run_script("screener", "core/screener.py")
    
    # 2. 更新看板
    d = os.path.join(BASE_DIR, "scripts", "build_dashboard.py")
    result = subprocess.run([VENV_PYTHON, d], capture_output=True, text=True)
    print(result.stdout.strip())
    
    print("=" * 40)
    print("✅ 收盘更新完成")

if __name__ == "__main__":
    main()
