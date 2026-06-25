"""运行器共享工具"""

from __future__ import annotations

import os
from typing import Any


def summarize_pytest_output(output: str) -> dict[str, Any]:
    """从 pytest 输出解析结果统计"""
    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "failures": [],
    }

    import re

    for raw_line in output.split("\n"):
        line = raw_line.strip()
        if 'passed' in line and 'in' in line and 's' in line:
            passed = re.search(r'(\d+) passed', line)
            failed = re.search(r'(\d+) failed', line)
            error = re.search(r'(\d+) error', line)
            skipped = re.search(r'(\d+) skipped', line)

            if passed:
                result["passed"] = int(passed.group(1))
            if failed:
                result["failed"] = int(failed.group(1))
            if error:
                result["error"] = int(error.group(1))
            if skipped:
                result["skipped"] = int(skipped.group(1))

            result["total"] = result["passed"] + result["failed"] + result["error"] + result["skipped"]

        if line.startswith('FAILED ') or '::FAILED' in line:
            result["failures"].append(line)

    return result


def load_project_config(test_dir: str) -> dict:
    """加载项目配置文件"""
    import yaml

    config_paths = [
        os.path.join(test_dir, "config.yaml"),
        os.path.join(test_dir, "config.yml"),
        os.path.join(os.path.dirname(test_dir), "config.yaml"),
        os.path.join(os.path.dirname(test_dir), "config.yml"),
    ]

    parent_dir = os.path.dirname(test_dir)
    for _ in range(3):
        assets_config = os.path.join(parent_dir, ".api-testcase-assets", "project.config.md")
        if os.path.exists(assets_config):
            try:
                with open(assets_config, 'r', encoding='utf-8') as f:
                    for line in f.read().split('\n'):
                        if '项目名称' in line and '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 3:
                                name = parts[2].strip()
                                if name and not name.startswith('['):
                                    return {"project": {"name": name}}
            except Exception:
                pass
        parent_dir = os.path.dirname(parent_dir)

    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass

    return {}


def generate_markdown_report(summary: dict[str, Any], output_path: str) -> None:
    """生成 Markdown 运行摘要"""
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    error = summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    elapsed = summary.get("elapsed_seconds", 0)
    pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "N/A"

    lines = [
        "# API 测试运行报告",
        "",
        "## 运行信息",
        f"- 运行模式: {summary.get('mode', 'unknown')}",
        f"- 开始时间: {summary.get('start_time', '')}",
        f"- 结束时间: {summary.get('end_time', '')}",
        f"- 耗时: {elapsed}s",
        f"- 命令: `{summary.get('command', '')}`",
        "",
        "## 测试结果",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 总用例数 | {total} |",
        f"| 通过 | {passed} ({pass_rate}) |",
        f"| 失败 | {failed} |",
        f"| 错误 | {error} |",
        f"| 跳过 | {skipped} |",
        "",
    ]

    if total > 0:
        rate = passed / total * 100
        if rate == 100:
            lines.append("**状态: 全部通过**")
        elif rate >= 90:
            lines.append(f"**状态: 大部分通过 ({pass_rate})**")
        else:
            lines.append(f"**状态: 存在失败 ({pass_rate})**")
        lines.append("")

    failures = summary.get("failures", [])
    if failures:
        lines.append("## 失败用例")
        lines.append("")
        for item in failures:
            lines.append(f"- {item}")
        lines.append("")

    stdout = summary.get("stdout", "")
    if "FAILED" in stdout or "ERROR" in stdout:
        lines.append("## 详细输出")
        lines.append("```")
        in_failures = False
        for line in stdout.split('\n'):
            if 'FAILURES' in line or 'ERRORS' in line:
                in_failures = True
            if in_failures:
                lines.append(line)
                if line.startswith('=') and 'short test summary' in line:
                    break
        lines.append("```")
        lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
