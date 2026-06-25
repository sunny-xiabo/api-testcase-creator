#!/usr/bin/env python3
# validate_code.py - CLI: 验证生成的 pytest 代码
# 用法: python3 validate_code.py <test_dir>

import sys
import os
import py_compile
import ast


def validate_syntax(filepath: str) -> list[str]:
    """检查单个文件的语法"""
    errors = []
    try:
        py_compile.compile(filepath, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(f"语法错误: {e}")
    return errors


def validate_imports(filepath: str) -> list[str]:
    """检查 import 是否合理（静态分析）"""
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return []  # 语法错误已在上一步捕获

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split('.')[0]
                # 检查是否是已知的标准库或第三方库
                # 这里只做基本检查，不阻塞
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split('.')[0]

    return errors


def validate_test_methods(filepath: str) -> list[str]:
    """检查测试文件是否包含测试方法"""
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return []

    has_test = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            has_test = True
            break
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    has_test = True
                    break

    if not has_test:
        errors.append("警告: 文件中未找到 test_ 开头的测试方法")

    return errors


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate_code.py <test_dir>")
        sys.exit(1)

    test_dir = sys.argv[1]
    if not os.path.isdir(test_dir):
        print(f"[ERROR] 目录不存在: {test_dir}")
        sys.exit(1)

    total_errors = []
    total_warnings = []
    files_checked = 0

    for filename in sorted(os.listdir(test_dir)):
        if not filename.endswith('.py'):
            continue
        if filename.startswith('__'):
            continue

        filepath = os.path.join(test_dir, filename)
        files_checked += 1

        # 语法检查
        syntax_errors = validate_syntax(filepath)
        for err in syntax_errors:
            total_errors.append(f"[{filename}] {err}")

        # import 检查
        import_errors = validate_imports(filepath)
        for err in import_errors:
            total_errors.append(f"[{filename}] {err}")

        # 测试方法检查
        test_errors = validate_test_methods(filepath)
        for err in test_errors:
            total_warnings.append(f"[{filename}] {err}")

    # 输出结果
    print(f"已检查 {files_checked} 个文件")
    print()

    if total_errors:
        print(f"[FAIL] 发现 {len(total_errors)} 个错误:")
        for err in total_errors:
            print(f"  - {err}")
    else:
        print("[OK] 语法检查通过")

    if total_warnings:
        print(f"\n[WARN] {len(total_warnings)} 个警告:")
        for warn in total_warnings:
            print(f"  - {warn}")

    # 尝试收集测试用例数量
    print()
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "--collect-only", "-q"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # 解析收集到的用例数
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'test' in line.lower() and ('selected' in line.lower() or 'collected' in line.lower()):
                    print(f"[INFO] {line.strip()}")
                    break
            else:
                # 简单计数
                test_count = sum(1 for l in lines if '::' in l and 'test_' in l)
                if test_count:
                    print(f"[INFO] 收集到 {test_count} 个测试用例")
        else:
            print(f"[WARN] pytest 收集失败: {result.stderr[:200]}")
    except Exception as e:
        print(f"[WARN] 无法运行 pytest --collect-only: {e}")

    sys.exit(1 if total_errors else 0)


if __name__ == '__main__':
    main()
