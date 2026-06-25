#!/usr/bin/env python3
# repair_json.py - 从 LLM 输出中提取、修复并校验 JSON
# 用法: python3 repair_json.py <input_file> <output_json> [--schema schema.json]

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def extract_json_text(content: str) -> str:
    """优先提取 fenced JSON 代码块，其次提取首尾 JSON 容器。"""
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()

    stripped = content.strip()
    starts = [idx for idx in (stripped.find("["), stripped.find("{")) if idx >= 0]
    if not starts:
        return stripped

    start = min(starts)
    end_array = stripped.rfind("]")
    end_object = stripped.rfind("}")
    end = max(end_array, end_object)
    if end >= start:
        return stripped[start:end + 1].strip()

    return stripped


def parse_json_or_repair(text: str) -> tuple[Any, bool]:
    """解析 JSON；失败时使用 json-repair 兜底。"""
    try:
        return json.loads(text), False
    except json.JSONDecodeError as original_error:
        try:
            from json_repair import repair_json
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "JSON 解析失败，且未安装 json-repair。请安装 json-repair 后重试，"
                f"原始错误: {original_error}"
            ) from exc

        repaired = repair_json(text)
        return json.loads(repaired), True


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    return _type_name(value) == expected


def validate_against_schema(data: Any, schema: dict) -> list[str]:
    """轻量 JSON Schema 校验，覆盖本项目模板需要的 required/type/enum/range。"""
    errors: list[str] = []

    def check(value: Any, node: dict, path: str) -> None:
        expected_type = node.get("type")
        if expected_type:
            expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
            if not any(_matches_type(value, item) for item in expected_types):
                errors.append(f"{path}: 类型应为 {expected_type}，实际为 {_type_name(value)}")
                return

        if "enum" in node and value not in node["enum"]:
            errors.append(f"{path}: 值 {value!r} 不在枚举 {node['enum']} 中")

        if isinstance(value, str):
            if "minLength" in node and len(value) < node["minLength"]:
                errors.append(f"{path}: 字符串长度小于 {node['minLength']}")
            if "pattern" in node and not re.search(node["pattern"], value):
                errors.append(f"{path}: 不匹配 pattern {node['pattern']}")

        if isinstance(value, int) or isinstance(value, float):
            if "minimum" in node and value < node["minimum"]:
                errors.append(f"{path}: 数值小于 {node['minimum']}")
            if "maximum" in node and value > node["maximum"]:
                errors.append(f"{path}: 数值大于 {node['maximum']}")

        if isinstance(value, list):
            item_schema = node.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(value):
                    check(item, item_schema, f"{path}[{index}]")

        if isinstance(value, dict):
            for key in node.get("required", []):
                if key not in value:
                    errors.append(f"{path}.{key}: 缺少必填字段")
            properties = node.get("properties", {})
            for key, child in properties.items():
                if key in value and isinstance(child, dict):
                    check(value[key], child, f"{path}.{key}")

    check(data, schema, "$")
    return errors


def load_schema(schema_path: str | None) -> dict | None:
    if not schema_path:
        return None
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_json(input_path: str, output_path: str, schema_path: str | None = None) -> dict:
    content = Path(input_path).read_text(encoding="utf-8")
    json_text = extract_json_text(content)
    data, repaired = parse_json_or_repair(json_text)

    schema = load_schema(schema_path)
    errors = validate_against_schema(data, schema) if schema else []
    if errors:
        joined = "\n  - ".join(errors)
        raise ValueError(f"JSON schema 校验失败:\n  - {joined}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "output": str(output),
        "repaired": repaired,
        "items": len(data) if isinstance(data, list) else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="提取、修复并校验 LLM 输出中的 JSON")
    parser.add_argument("input_file")
    parser.add_argument("output_json")
    parser.add_argument("--schema", default=None)
    args = parser.parse_args()

    try:
        summary = normalize_json(args.input_file, args.output_json, args.schema)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] JSON 已输出: {summary['output']}")
    print(f"[INFO] 是否修复: {'是' if summary['repaired'] else '否'}")
    if summary["items"] is not None:
        print(f"[INFO] 条目数: {summary['items']}")


if __name__ == "__main__":
    main()
