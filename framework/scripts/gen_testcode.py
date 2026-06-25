#!/usr/bin/env python3
# gen_testcode.py - CLI: 从用例 JSON 生成 pytest 代码
# 用法: python3 gen_testcode.py <input_json> <output_dir> [--project NAME] [--base-url URL]

import sys
import json
import os

# 兼容源码目录运行和部署到 .api-testcase-assets 后运行
SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
for path in (os.path.dirname(ASSETS_DIR), ASSETS_DIR, os.path.join(ASSETS_DIR, 'framework')):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from framework.generators.code_gen import CodeGenerator
except ModuleNotFoundError:
    from generators.code_gen import CodeGenerator


def main():
    if len(sys.argv) < 3:
        print("用法: python3 gen_testcode.py <input_json> <output_dir> [--project NAME] [--base-url URL]")
        sys.exit(1)

    input_json = sys.argv[1]
    output_dir = sys.argv[2]

    # 解析可选参数
    project_name = "API"
    base_url = ""
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            project_name = sys.argv[i + 1]
        if arg == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]

    # 读取用例
    with open(input_json, 'r', encoding='utf-8') as f:
        testcases = json.load(f)

    # 生成代码
    generator = CodeGenerator(output_dir)
    result = generator.generate(testcases, project_name=project_name, base_url=base_url)
    generator.write_files(result)

    # 输出摘要
    print(f"[OK] 已生成 pytest 代码到 {output_dir}/")
    print(f"  测试文件: {len(result['test_files'])} 个")
    for filename in result['test_files']:
        print(f"    - {filename}")
    print(f"  conftest.py: 已生成")
    print(f"  api_client.py: 已生成")
    print(f"  config.yaml: 已生成（请填写实际配置）")
    print(f"  requirements.txt: 已生成")


if __name__ == '__main__':
    main()
