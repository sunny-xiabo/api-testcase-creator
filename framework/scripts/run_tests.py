#!/usr/bin/env python3
# run_tests.py - CLI: 运行 pytest 测试并生成报告
# 用法: python3 run_tests.py <test_dir> [--mode smoke|full] [--report-dir DIR] [--reporter html|pytest-html]

import sys
import os
import subprocess
import json
from datetime import datetime

# 兼容源码目录运行和部署到 .api-testcase-assets 后运行
SCRIPT_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
for path in (os.path.dirname(ASSETS_DIR), ASSETS_DIR, os.path.join(ASSETS_DIR, 'framework')):
    if path not in sys.path:
        sys.path.insert(0, path)

# 导入内置 HTML 报告生成器
try:
    from framework.runners.html_reporter import HtmlReporter, parse_pytest_output
    from framework.runners.runner_shared import (
        generate_markdown_report as shared_generate_markdown_report,
        load_project_config as shared_load_project_config,
        summarize_pytest_output,
    )
except ModuleNotFoundError:
    from runners.html_reporter import HtmlReporter, parse_pytest_output
    from runners.runner_shared import (
        generate_markdown_report as shared_generate_markdown_report,
        load_project_config as shared_load_project_config,
        summarize_pytest_output,
    )


def run_pytest(test_dir: str, mode: str = "full", report_dir: str = "./report",
               reporter: str = "html") -> dict:
    """运行 pytest 并收集结果"""
    os.makedirs(report_dir, exist_ok=True)

    # 构建 pytest 命令
    cmd = [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"]

    # 冒烟模式只跑 P0
    if mode == "smoke":
        cmd.extend(["-m", "P0"])
    elif mode == "collect-only":
        cmd.extend(["--collect-only", "-q"])

    # 根据报告器选择参数
    html_report = os.path.join(report_dir, "report.html")

    if reporter == "pytest-html":
        # 使用 pytest-html
        cmd.extend(["--html", html_report, "--self-contained-html"])
    else:
        # 使用内置报告生成器或 XTestRunner（不添加 --html 参数，稍后单独生成）
        pass

    # JUnit XML（供后续分析）
    junit_xml = os.path.join(report_dir, "results.xml")
    if mode != "collect-only":
        cmd.extend(["--junitxml", junit_xml])

    print(f"[RUN] 执行命令: {' '.join(cmd)}")
    print(f"[RUN] 运行模式: {mode}")
    print(f"[RUN] 报告目录: {report_dir}")
    print(f"[RUN] 报告器: {reporter}")
    print()

    # 执行
    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = datetime.now()

    elapsed = (end_time - start_time).total_seconds()

    # 解析结果
    summary = {
        "mode": mode,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "elapsed_seconds": elapsed,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "report_path": html_report,
    }

    # 从 stdout 解析用例数
    summary.update(_parse_pytest_output(result.stdout))

    # 从项目配置中读取报告信息
    config = _load_project_config(test_dir)
    report_config = config.get("report", {})
    project_name = config.get("project", {}).get("name", "API 测试")

    # 生成报告（使用内置 XTestRunner 样式）
    if mode != "collect-only" and result.returncode == 0 and reporter == "html":
        html_report_path = os.path.join(report_dir, "html_report.html")
        html_reporter = HtmlReporter(
            title=report_config.get("title", f"{project_name} - API 测试报告"),
            description=report_config.get("description", ""),
            tester=report_config.get("tester", ""),
            language=report_config.get("language", "cn")
        )
        html_reporter.set_start_time(start_time)
        html_reporter.set_end_time(end_time)

        # 从 pytest 输出解析测试结果
        results = parse_pytest_output(result.stdout)
        for r in results:
            html_reporter.add_result(
                test_id=r.test_id,
                test_doc=r.test_doc,
                outcome=r.outcome,
                duration=r.duration,
                message=r.message
            )

        # 生成报告
        report_path = html_reporter.generate(html_report_path)
        if report_path:
            summary["html_report"] = report_path

    return summary


def _parse_pytest_output(output: str) -> dict:
    return summarize_pytest_output(output)


def _load_project_config(test_dir: str) -> dict:
    return shared_load_project_config(test_dir)


def generate_markdown_report(summary: dict, output_path: str):
    return shared_generate_markdown_report(summary, output_path)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 run_tests.py <test_dir> [--mode smoke|full] [--report-dir DIR] [--reporter html|pytest-html]")
        print("")
        print("参数:")
        print("  test_dir          测试代码目录")
        print("  --mode MODE       运行模式: smoke (冒烟) / full (完整) / collect-only (干跑)")
        print("  --report-dir DIR  报告输出目录")
        print("  --reporter NAME   报告生成器:")
        print("                    html (默认) - 内置 XTestRunner 样式报告，无额外依赖")
        print("                    pytest-html - pytest-html 报告（需要安装 pytest-html）")
        sys.exit(1)

    test_dir = sys.argv[1]
    mode = "full"
    report_dir = "./report"
    reporter = "html"  # 默认使用内置 XTestRunner 样式报告

    for i, arg in enumerate(sys.argv):
        if arg == "--mode" and i + 1 < len(sys.argv):
            mode = sys.argv[i + 1]
        if arg == "--report-dir" and i + 1 < len(sys.argv):
            report_dir = sys.argv[i + 1]
        if arg == "--reporter" and i + 1 < len(sys.argv):
            reporter = sys.argv[i + 1]

    # 运行测试
    summary = run_pytest(test_dir, mode=mode, report_dir=report_dir, reporter=reporter)

    # 生成 Markdown 摘要
    md_report = os.path.join(report_dir, "run_summary.md")
    generate_markdown_report(summary, md_report)

    # 输出结果
    print()
    print("=" * 50)
    print(f"测试完成")
    print(f"  总用例: {summary.get('total', 'N/A')}")
    print(f"  通过: {summary.get('passed', 'N/A')}")
    print(f"  失败: {summary.get('failed', 'N/A')}")
    print(f"  耗时: {summary.get('elapsed_seconds', 0):.1f}s")
    if summary.get('html_report'):
        print(f"  HTML 报告: {summary.get('html_report')}")
    if summary.get('xtestrunner_report'):
        print(f"  XTestRunner 报告: {summary.get('xtestrunner_report')}")
    print(f"  Markdown 摘要: {md_report}")
    print("=" * 50)

    sys.exit(summary.get("return_code", 1))


if __name__ == '__main__':
    main()
