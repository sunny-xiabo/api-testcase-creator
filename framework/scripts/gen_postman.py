#!/usr/bin/env python3
# gen_postman.py - CLI: 从用例 JSON 生成 Postman Collection
# 用法: python3 gen_postman.py <input_json> <output_json> [--name NAME] [--base-url URL]

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
    from framework.generators.postman_gen import PostmanGenerator
except ModuleNotFoundError:
    from generators.postman_gen import PostmanGenerator


def main():
    if len(sys.argv) < 3:
        print("用法: python3 gen_postman.py <input_json> <output_json> [--name NAME] [--base-url URL]")
        sys.exit(1)

    input_json = sys.argv[1]
    output_json = sys.argv[2]

    # 解析可选参数
    collection_name = "API 测试"
    base_url = ""
    for i, arg in enumerate(sys.argv):
        if arg == "--name" and i + 1 < len(sys.argv):
            collection_name = sys.argv[i + 1]
        if arg == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]

    # 读取用例
    with open(input_json, 'r', encoding='utf-8') as f:
        testcases = json.load(f)

    # 生成 Postman Collection
    generator = PostmanGenerator()
    collection = generator.generate(testcases, collection_name=collection_name, base_url=base_url)
    generator.write(collection, output_json)

    # 输出摘要
    total_items = sum(len(folder.get("item", [])) for folder in collection.get("item", []))
    print(f"[OK] 已生成 Postman Collection 到 {output_json}")
    print(f"  Collection 名称: {collection_name}")
    print(f"  请求总数: {total_items}")
    print(f"  文件夹数: {len(collection.get('item', []))}")
    print(f"\n导入方式:")
    print(f"  1. 打开 Postman")
    print(f"  2. 点击 Import -> File")
    print(f"  3. 选择 {output_json}")


if __name__ == '__main__':
    main()
