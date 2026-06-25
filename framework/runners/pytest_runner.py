# pytest_runner.py - pytest 运行器 + 报告集成
# 运行 pytest 测试并生成多种格式的报告

import os
import sys
import subprocess
from datetime import datetime

# 导入内置 HTML 报告生成器
from .html_reporter import HtmlReporter, parse_pytest_output
from .runner_shared import (
    generate_markdown_report as shared_generate_markdown_report,
    load_project_config as shared_load_project_config,
    summarize_pytest_output,
)


class PytestRunner:
    """pytest 测试运行器"""

    def __init__(self, test_dir: str, report_dir: str = "./report"):
        self.test_dir = test_dir
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)

    def run(self, mode: str = "full", markers: list = None) -> dict:
        """
        运行测试

        mode: full / smoke / collect-only
        markers: pytest markers 过滤

        返回: 运行结果摘要
        """
        test_dir = os.path.abspath(self.test_dir)
        report_dir = os.path.abspath(self.report_dir)

        # 构建命令
        cmd = [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"]

        # 模式
        if mode == "smoke":
            cmd.extend(["-m", "P0"])
        elif mode == "collect-only":
            cmd.extend(["--collect-only", "-q"])

        # markers
        if markers:
            marker_expr = " and ".join(f"({m})" for m in markers if m)
            if marker_expr:
                cmd.extend(["-m", marker_expr])

        # 报告输出
        if mode != "collect-only":
            # JUnit XML
            junit_xml = os.path.join(report_dir, "results.xml")
            cmd.extend(["--junitxml", junit_xml])

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
            "elapsed_seconds": round(elapsed, 2),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
        }

        # 从 stdout 解析用例数
        summary.update(self._parse_pytest_output(result.stdout))

        # 保存报告
        if mode != "collect-only":
            summary["junit_xml"] = junit_xml

            # 保存原始输出
            log_path = os.path.join(report_dir, "output.log")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n\n=== STDERR ===\n")
                    f.write(result.stderr)

            reporter = XTestRunnerReporter(report_dir)
            summary["html_report"] = reporter.generate(summary)

        return summary

    def _parse_pytest_output(self, output: str) -> dict:
        return summarize_pytest_output(output)

    def _load_project_config(self) -> dict:
        return shared_load_project_config(self.test_dir)

    def generate_markdown_report(self, summary: dict, output_path: str = None) -> str:
        """生成 Markdown 运行报告"""
        if output_path is None:
            output_path = os.path.join(self.report_dir, "run_summary.md")
        shared_generate_markdown_report(summary, output_path)
        return output_path


class XTestRunnerReporter:
    """HTML 报告生成器（优先使用内置，可选 XTestRunner）"""

    def __init__(self, report_dir: str = "./report"):
        self.report_dir = report_dir

    def _load_project_config(self) -> dict:
        return shared_load_project_config(self.report_dir)

    def generate(self, summary: dict, testcases: list = None, output_path: str = None,
                 use_xtestrunner: bool = False) -> str:
        """
        生成 HTML 报告

        summary: pytest 运行结果摘要
        testcases: 原始用例列表（可选，用于展示用例详情）
        use_xtestrunner: 是否使用 XTestRunner（如果可用）
        """
        if use_xtestrunner:
            print("[WARN] XTestRunner 插件模式暂不可用，已使用内置 HTML 报告生成器")
        return self._generate_builtin(summary, testcases, output_path)

    def _generate_builtin(self, summary: dict, testcases: list = None, output_path: str = None) -> str:
        """使用内置 HTML 报告生成器"""
        if output_path is None:
            output_path = os.path.join(self.report_dir, "html_report.html")

        # 从 pytest 输出解析测试结果
        stdout = summary.get("stdout", "")
        results = parse_pytest_output(stdout)

        # 创建内置 HTML 报告生成器
        reporter = HtmlReporter(
            title=summary.get("title", "API 测试报告"),
            description=summary.get("description", ""),
            tester=summary.get("tester", ""),
            language=summary.get("language", "cn")
        )

        # 如果 summary 中没有标题，尝试从项目配置中读取
        if not summary.get("title"):
            config = self._load_project_config()
            project_name = config.get("project", {}).get("name", "")
            if project_name:
                reporter.title = f"{project_name} - API 测试报告"

        # 设置时间
        from datetime import datetime
        if summary.get("start_time"):
            reporter.set_start_time(datetime.fromisoformat(summary["start_time"]))
        if summary.get("end_time"):
            reporter.set_end_time(datetime.fromisoformat(summary["end_time"]))

        # 添加解析到的结果
        for result in results:
            reporter.add_result(
                test_id=result.test_id,
                test_doc=result.test_doc,
                outcome=result.outcome,
                duration=result.duration,
                message=result.message
            )

        # 生成报告
        return reporter.generate(output_path)


class HtmlReportGenerator:
    """HTML 报告生成器（兼容旧接口）"""

    def __init__(self, report_dir: str = "./report"):
        self.report_dir = report_dir

    def generate(self, summary: dict, testcases: list = None, output_path: str = None) -> str:
        """生成 HTML 报告"""
        if output_path is None:
            output_path = os.path.join(self.report_dir, "html_report.html")

        # 使用内置 HTML 报告生成器
        reporter = HtmlReporter(
            title=summary.get("title", "API 测试报告"),
            description=summary.get("description", ""),
            tester=summary.get("tester", ""),
            language=summary.get("language", "cn")
        )

        # 设置时间
        from datetime import datetime
        if summary.get("start_time"):
            reporter.set_start_time(datetime.fromisoformat(summary["start_time"]))
        if summary.get("end_time"):
            reporter.set_end_time(datetime.fromisoformat(summary["end_time"]))

        # 从 pytest 输出解析测试结果
        stdout = summary.get("stdout", "")
        results = parse_pytest_output(stdout)

        # 添加解析到的结果
        for result in results:
            reporter.add_result(
                test_id=result.test_id,
                test_doc=result.test_doc,
                outcome=result.outcome,
                duration=result.duration,
                message=result.message
            )

        # 生成报告
        return reporter.generate(output_path)
