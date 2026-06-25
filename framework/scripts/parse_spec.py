#!/usr/bin/env python3
# parse_spec.py - CLI: 解析接口文档，输出 Endpoint 列表 JSON
# 支持: OpenAPI 3.0 / Swagger 2.0 / Postman Collection v2.1
# 用法: python3 parse_spec.py <input_file> [output_file]

import sys
import json
import os
from pathlib import Path

# 兼容源码目录运行和部署到 .api-testcase-assets 后运行
SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
for path in (os.path.dirname(ASSETS_DIR), ASSETS_DIR, os.path.join(ASSETS_DIR, 'framework')):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from framework.parsers.openapi_parser import OpenAPIParser
    from framework.parsers.postman_parser import PostmanParser
    from framework.parsers.endpoint_model import Endpoint
except ModuleNotFoundError:
    from parsers.openapi_parser import OpenAPIParser
    from parsers.postman_parser import PostmanParser
    from parsers.endpoint_model import Endpoint


def detect_format(file_path: str) -> str:
    """自动检测文件格式"""
    path = Path(file_path)
    content = path.read_text(encoding='utf-8')

    # 尝试解析 JSON
    try:
        data = json.loads(content)
        # Postman Collection 检测
        if 'info' in data and 'item' in data:
            schema = data.get('info', {}).get('schema', '')
            if 'postman' in schema.lower() or 'collection' in schema.lower():
                return 'postman'
            # 即使 schema 不明确，有 item 结构也认为是 Postman
            return 'postman'
        # OpenAPI/Swagger 检测
        if 'openapi' in data or 'swagger' in data or 'paths' in data:
            return 'openapi'
    except json.JSONDecodeError:
        # 可能是 YAML
        try:
            import yaml
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                if 'openapi' in data or 'swagger' in data or 'paths' in data:
                    return 'openapi'
                if 'info' in data and 'item' in data:
                    return 'postman'
        except Exception:
            pass

    # 根据后缀猜测
    if path.suffix in ('.yaml', '.yml'):
        return 'openapi'
    if 'postman' in path.name.lower() or 'collection' in path.name.lower():
        return 'postman'

    return 'openapi'  # 默认


def endpoint_to_dict(ep: Endpoint) -> dict:
    """Endpoint 转为可序列化的 dict"""
    return {
        "method": ep.method,
        "path": ep.path,
        "summary": ep.summary,
        "description": ep.description,
        "tags": ep.tags,
        "parameters": [
            {
                "name": p.name,
                "location": p.location,
                "type": p.type,
                "required": p.required,
                "description": p.description,
                "enum": p.enum,
                "minimum": p.minimum,
                "maximum": p.maximum,
                "min_length": p.min_length,
                "max_length": p.max_length,
                "pattern": p.pattern,
                "default": p.default,
                "example": p.example,
            }
            for p in ep.parameters
        ],
        "request_body": [
            {
                "name": f.name,
                "type": f.type,
                "required": f.required,
                "description": f.description,
                "enum": f.enum,
                "minimum": f.minimum,
                "maximum": f.maximum,
                "min_length": f.min_length,
                "max_length": f.max_length,
                "pattern": f.pattern,
                "default": f.default,
                "example": f.example,
            }
            for f in ep.request_body
        ],
        "responses": [
            {
                "status_code": r.status_code,
                "description": r.description,
                "schema": r.schema,
                "example": r.example,
            }
            for r in ep.responses
        ],
        "security": ep.security,
        "has_auth": ep.has_auth,
        "deprecated": ep.deprecated,
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 parse_spec.py <input_file> [output_file]")
        print("")
        print("支持格式:")
        print("  - OpenAPI 3.0 (.json / .yaml)")
        print("  - Swagger 2.0 (.json / .yaml)")
        print("  - Postman Collection v2.1 (.json)")
        print("")
        print("格式自动检测，也可用 --format 手动指定。")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = None
    force_format = None

    # 解析参数
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == '--format' and i + 1 < len(sys.argv):
            force_format = sys.argv[i + 1]
        elif not arg.startswith('-') and output_file is None:
            output_file = arg

    # 检测格式
    fmt = force_format or detect_format(input_file)
    print(f"[INFO] 检测格式: {fmt}")

    # 选择解析器
    if fmt == 'postman':
        parser = PostmanParser()
    else:
        parser = OpenAPIParser()

    # 解析
    try:
        endpoints = parser.parse(input_file)
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 转为 dict
    result = [endpoint_to_dict(ep) for ep in endpoints]

    # 输出
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"[OK] 已解析 {len(endpoints)} 个接口，输出到 {output_file}")
    else:
        print(output)


if __name__ == '__main__':
    main()
