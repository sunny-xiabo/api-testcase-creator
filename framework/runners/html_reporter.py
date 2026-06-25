# html_reporter.py - 内置 HTML 报告生成器（XTestRunner 样式）
# 使用 XTestRunner 的 CSS 样式 and 布局结构，不依赖 XTestRunner 库

import os
import datetime
import html
from typing import List, Dict, Any, Optional


class TestResult:
    """测试结果"""

    def __init__(self, test_id: str, test_doc: str = "", outcome: str = "passed",
                 duration: float = 0.0, message: str = "", endpoint: str = "",
                 scene_type: str = "", priority: str = ""):
        self.test_id = test_id
        self.test_doc = test_doc
        self.outcome = outcome  # passed, failed, error, skipped
        self.duration = duration
        self.message = message
        self.endpoint = endpoint
        self.scene_type = scene_type
        self.priority = priority


class HtmlReporter:
    """HTML 报告生成器（XTestRunner 样式）"""

    def __init__(self, title: str = "API 测试报告", description: str = "",
                 tester: str = "", language: str = "cn"):
        self.title = title
        self.description = description
        self.tester = tester
        self.language = language
        self.results: List[TestResult] = []
        self.start_time: Optional[datetime.datetime] = None
        self.end_time: Optional[datetime.datetime] = None

    def add_result(self, test_id: str, test_doc: str = "", outcome: str = "passed",
                   duration: float = 0.0, message: str = "", endpoint: str = "",
                   scene_type: str = "", priority: str = ""):
        """添加测试结果"""
        result = TestResult(
            test_id=test_id,
            test_doc=test_doc,
            outcome=outcome,
            duration=duration,
            message=message,
            endpoint=endpoint,
            scene_type=scene_type,
            priority=priority
        )
        self.results.append(result)

    def set_start_time(self, time: datetime.datetime = None):
        """设置开始时间"""
        self.start_time = time or datetime.datetime.now()

    def set_end_time(self, time: datetime.datetime = None):
        """设置结束时间"""
        self.end_time = time or datetime.datetime.now()

    def generate(self, output_path: str) -> str:
        """生成 HTML 报告"""
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 计算统计
        stats = self._calculate_stats()

        # 生成 HTML
        html = self._render_html(stats)

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"[OK] HTML 报告已生成: {output_path}")
        return output_path

    def _calculate_stats(self) -> Dict[str, Any]:
        """计算统计数据"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.outcome == "passed")
        failed = sum(1 for r in self.results if r.outcome == "failed")
        error = sum(1 for r in self.results if r.outcome == "error")
        skipped = sum(1 for r in self.results if r.outcome == "skipped")

        # 计算耗时
        elapsed = 0.0
        if self.start_time and self.end_time:
            elapsed = (self.end_time - self.start_time).total_seconds()
        else:
            elapsed = sum(r.duration for r in self.results)

        # 按场景类型统计
        scene_type_stats = {}
        for r in self.results:
            if r.scene_type:
                scene_type_stats[r.scene_type] = scene_type_stats.get(r.scene_type, 0) + 1

        # 按优先级统计
        priority_stats = {}
        for r in self.results:
            if r.priority:
                priority_stats[r.priority] = priority_stats.get(r.priority, 0) + 1

        # 按接口统计
        endpoint_stats = {}
        for r in self.results:
            if r.endpoint:
                endpoint_stats[r.endpoint] = endpoint_stats.get(r.endpoint, 0) + 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "error": error,
            "skipped": skipped,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "fail_rate": round(failed / total * 100, 1) if total > 0 else 0,
            "error_rate": round(error / total * 100, 1) if total > 0 else 0,
            "skip_rate": round(skipped / total * 100, 1) if total > 0 else 0,
            "elapsed": round(elapsed, 2),
            "scene_type_stats": scene_type_stats,
            "priority_stats": priority_stats,
            "endpoint_stats": endpoint_stats,
        }

    def _render_html(self, stats: Dict[str, Any]) -> str:
        """渲染 HTML 报告（XTestRunner 样式）"""
        total = stats["total"]
        passed = stats["passed"]
        failed = stats["failed"]
        error = stats["error"]
        skipped = stats["skipped"]
        pass_rate = stats["pass_rate"]
        fail_rate = stats["fail_rate"]
        error_rate = stats["error_rate"]
        skip_rate = stats["skip_rate"]
        elapsed = stats["elapsed"]

        # 格式化时间
        start_time_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else ""
        end_time_str = self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else ""
        duration_str = f"{elapsed:.2f}s"

        # 生成用例详情行
        test_rows = ""
        for i, r in enumerate(self.results):
            status_class = {"passed": "success", "failed": "warning", "error": "danger", "skipped": "secondary"}.get(r.outcome, "")
            status_text = {"passed": "通过", "failed": "失败", "error": "错误", "skipped": "跳过"}.get(r.outcome, r.outcome)
            
            # SVG 状态小徽标
            svg_icon = {
                "passed": '<svg class="badge-icon" style="width: 14px; height: 14px; flex-shrink: 0;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
                "failed": '<svg class="badge-icon" style="width: 14px; height: 14px; flex-shrink: 0;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>',
                "error": '<svg class="badge-icon" style="width: 14px; height: 14px; flex-shrink: 0;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>',
                "skipped": '<svg class="badge-icon" style="width: 14px; height: 14px; flex-shrink: 0;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 9a1 1 0 000 2h4a1 1 0 100-2H8z"></path></svg>'
            }.get(r.outcome, "")

            # 详情行（可展开）
            detail_id = f"detail_{i}"
            detail_content = ""
            if r.message:
                escaped_message = html.escape(r.message)
                detail_content = f"""
                <tr id="{detail_id}" class="hiddenRow detail-row">
                    <td colspan="8">
                        <div class="error-detail-container">
                            <div class="error-detail-header">
                                <span>崩溃报错详细堆栈</span>
                                <button class="btn-copy" onclick="copyError('{detail_id}_text')">
                                    <svg style="width: 12px; height: 12px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                                    <span>复制报错</span>
                                </button>
                            </div>
                            <pre id="{detail_id}_text" class="error-detail-content">{escaped_message}</pre>
                        </div>
                    </td>
                </tr>"""

            # 持续时间着色
            dur_class = "duration-slow" if r.duration > 1.0 else "duration-fast" if r.duration < 0.1 else ""

            # 接口样式：将方法与路径分离，做彩色徽章化
            endpoint_disp = "-"
            if r.endpoint:
                parts = r.endpoint.strip().split(" ", 1)
                if len(parts) == 2:
                    method, path = parts[0].upper(), parts[1]
                    method_class = {
                        "GET": "method-get",
                        "POST": "method-post",
                        "PUT": "method-put",
                        "DELETE": "method-delete",
                        "PATCH": "method-patch"
                    }.get(method, "method-other")
                    endpoint_disp = f'<div class="endpoint-container"><span class="method-badge {method_class}">{html.escape(method)}</span><span class="path-text">{html.escape(path)}</span></div>'
                else:
                    endpoint_disp = f'<span class="endpoint-badge">{html.escape(r.endpoint)}</span>'

            test_rows += f"""
            <tr class="test-row" id="t{i}" data-status="{r.outcome}">
                <td>
                    <span style="font-weight: 600; display: inline-flex; align-items: center; gap: 8px;">{r.test_id}</span>
                </td>
                <td>{html.escape(r.test_doc) if r.test_doc else "-"}</td>
                <td>{endpoint_disp}</td>
                <td>{html.escape(r.scene_type) if r.scene_type else "-"}</td>
                <td><span class="badge priority-{r.priority}">{r.priority}</span></td>
                <td><span class="{dur_class}">{r.duration:.3f}s</span></td>
                <td>
                    <span class="badge badge-{status_class}">
                        {svg_icon}
                        <span>{status_text}</span>
                    </span>
                </td>
                <td>
                    {"<button onclick='showDetail(\"" + detail_id + "\")' class='btn-action'>查看</button>" if r.message else "-"}
                </td>
            </tr>
            {detail_content}"""

        # 计算环形图和柱状图参数
        dashoffset = 314.16 - (pass_rate / 100) * 314.16
        max_val = max(passed, failed, error, skipped, 1)
        passed_height = max((passed / max_val) * 140, 6)
        failed_height = max((failed / max_val) * 140, 6)
        error_height = max((error / max_val) * 140, 6)
        skipped_height = max((skipped / max_val) * 140, 6)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <title>{self.title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {{
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --bg-header: #f1f5f9;
            --border-color: #e2e8f0;
            
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            
            --color-pass: #10b981;
            --color-pass-glow: rgba(16, 185, 129, 0.08);
            --color-fail: #f59e0b;
            --color-fail-glow: rgba(245, 158, 11, 0.08);
            --color-error: #ef4444;
            --color-error-glow: rgba(239, 68, 68, 0.08);
            --color-skip: #64748b;
            --color-skip-glow: rgba(100, 116, 139, 0.08);
            --color-info: #3b82f6;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            font-size: 14px;
            line-height: 1.5;
        }}

        /* 导航栏 */
        .navbar {{
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
            backdrop-filter: blur(10px);
        }}

        .navbar-brand {{
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.025em;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .navbar-brand svg {{
            width: 24px;
            height: 24px;
            fill: none;
            stroke: var(--color-pass);
            stroke-width: 2.5;
        }}

        .navbar-title {{
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            background: rgba(0, 0, 0, 0.03);
            padding: 6px 16px;
            border-radius: 9999px;
            border: 1px solid var(--border-color);
        }}

        /* 布局容器 */
        .container-fluid {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 30px 24px;
        }}

        /* 仪表盘统计卡片 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
            border: 1px solid var(--border-color);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }}

        .stat-card::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
        }}

        .stat-card.passed::after {{ background: var(--color-pass); }}
        .stat-card.failed::after {{ background: var(--color-fail); }}
        .stat-card.error::after {{ background: var(--color-error); }}
        .stat-card.skipped::after {{ background: var(--color-skip); }}
        .stat-card.total::after {{ background: var(--color-info); }}

        /* 卡片悬浮发光与呼吸动效 */
        .stat-card.passed:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -3px rgba(16, 185, 129, 0.12), 0 4px 6px -2px rgba(16, 185, 129, 0.04);
            border-color: rgba(16, 185, 129, 0.2);
        }}
        .stat-card.failed:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -3px rgba(245, 158, 11, 0.12), 0 4px 6px -2px rgba(245, 158, 11, 0.04);
            border-color: rgba(245, 158, 11, 0.2);
        }}
        .stat-card.error:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -3px rgba(239, 68, 68, 0.12), 0 4px 6px -2px rgba(239, 68, 68, 0.04);
            border-color: rgba(239, 68, 68, 0.2);
        }}
        .stat-card.skipped:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -3px rgba(100, 116, 139, 0.12), 0 4px 6px -2px rgba(100, 116, 139, 0.04);
            border-color: rgba(100, 116, 139, 0.2);
        }}
        .stat-card.total:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -3px rgba(59, 130, 246, 0.12), 0 4px 6px -2px rgba(59, 130, 246, 0.04);
            border-color: rgba(59, 130, 246, 0.2);
        }}

        .stat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .stat-title {{
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .stat-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .stat-icon.passed {{ background: var(--color-pass-glow); color: var(--color-pass); }}
        .stat-icon.failed {{ background: var(--color-fail-glow); color: var(--color-fail); }}
        .stat-icon.error {{ background: var(--color-error-glow); color: var(--color-error); }}
        .stat-icon.skipped {{ background: var(--color-skip-glow); color: var(--color-skip); }}
        .stat-icon.total {{ background: rgba(59, 130, 246, 0.1); color: var(--color-info); }}

        .stat-icon svg {{
            width: 18px;
            height: 18px;
        }}

        .stat-number {{
            font-size: 36px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 6px;
            letter-spacing: -0.05em;
        }}

        .stat-rate {{
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 14px;
        }}

        .stat-rate .badge {{
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 11px;
        }}

        /* 进度条 */
        .progress {{
            height: 6px;
            background: rgba(0, 0, 0, 0.03);
            border-radius: 3px;
            overflow: hidden;
        }}

        .progress-bar {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s ease-out;
        }}

        /* 用例和概述双列布局 */
        .dashboard-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}

        @media (max-width: 1024px) {{
            .dashboard-row {{
                grid-template-columns: 1fr;
            }}
        }}

        .info-card {{
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        }}

        .info-card-header {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            font-size: 15px;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .info-card-header svg {{
            width: 18px;
            height: 18px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
        }}

        .info-card-body {{
            padding: 20px;
        }}

        /* 概述信息列表 */
        .info-list {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }}

        .info-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .info-item-label {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .info-item-value {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
        }}

        .info-item.full-width {{
            grid-column: span 2;
        }}

        /* 图表区 */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 20px;
            align-items: center;
            height: 100%;
        }}

        @media (max-width: 640px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-box {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
        }}

        /* 环形图 */
        .progress-ring {{
            /* Unrotated container to keep text horizontal */
        }}
        .progress-ring__circle {{
            transition: stroke-dashoffset 0.8s ease-in-out;
        }}

        /* 柱状图 */
        .bar-chart {{
            display: flex;
            justify-content: space-around;
            align-items: flex-end;
            height: 140px;
            padding-top: 10px;
            position: relative;
            border-bottom: 2px solid var(--border-color);
            width: 100%;
        }}

        .bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 22%;
            height: 100%;
            justify-content: flex-end;
        }}

        .bar-item {{
            width: 100%;
            max-width: 40px;
            border-radius: 6px 6px 0 0;
            transition: all 0.3s ease;
            position: relative;
        }}

        /* 柱形悬浮发光特效 */
        .bar-passed {{ background: linear-gradient(to top, var(--color-pass), #34d399); }}
        .bar-failed {{ background: linear-gradient(to top, var(--color-fail), #fbbf24); }}
        .bar-error {{ background: linear-gradient(to top, var(--color-error), #f87171); }}
        .bar-skipped {{ background: linear-gradient(to top, var(--color-skip), #9ca3af); }}

        .bar-passed:hover {{ box-shadow: 0 0 12px rgba(16, 185, 129, 0.4); filter: brightness(1.1); }}
        .bar-failed:hover {{ box-shadow: 0 0 12px rgba(245, 158, 11, 0.4); filter: brightness(1.1); }}
        .bar-error:hover {{ box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); filter: brightness(1.1); }}
        .bar-skipped:hover {{ box-shadow: 0 0 12px rgba(100, 116, 139, 0.4); filter: brightness(1.1); }}

        .bar-label {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 8px;
            white-space: nowrap;
        }}

        .bar-val {{
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 4px;
        }}

        /* 列表区控制面板 */
        .control-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }}

        @media (max-width: 768px) {{
            .control-bar {{
                flex-direction: column;
                align-items: stretch;
            }}
        }}

        .search-box {{
            position: relative;
            flex-grow: 1;
        }}

        .search-box input {{
            width: 100%;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 16px 10px 40px;
            color: var(--text-primary);
            font-size: 13.5px;
            outline: none;
            transition: all 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--color-info);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
        }}

        .search-box svg {{
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            fill: none;
            stroke: var(--text-secondary);
            stroke-width: 2;
        }}

        /* 过滤按钮组 */
        .filter-group {{
            display: flex;
            background: #f1f5f9;
            border: 1px solid var(--border-color);
            padding: 4px;
            border-radius: 8px;
            gap: 4px;
        }}

        .filter-btn {{
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            background: transparent;
            color: var(--text-secondary);
            border: none;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .filter-btn:hover {{
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.5);
        }}

        .filter-btn.active {{
            background: #ffffff;
            color: var(--text-primary);
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}

        .filter-btn .btn-badge {{
            background: rgba(0, 0, 0, 0.05);
            color: var(--text-secondary);
            padding: 1px 5px;
            font-size: 11px;
            border-radius: 4px;
            font-weight: 700;
        }}

        .filter-btn.active .btn-badge {{
            background: rgba(0, 0, 0, 0.08);
            color: var(--text-primary);
        }}

        /* 表格卡片 */
        .table-card {{
            background: var(--bg-card);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
            overflow: hidden;
            margin-bottom: 24px;
        }}

        .table-responsive {{
            overflow-x: auto;
        }}

        .table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .table th {{
            background: #f8fafc;
            font-weight: 600;
            color: var(--text-secondary);
            padding: 14px 20px;
            text-align: left;
            font-size: 12.5px;
            letter-spacing: 0.05em;
            border-bottom: 2px solid var(--border-color);
        }}

        .table td {{
            padding: 14px 20px;
            border-bottom: 1px solid var(--border-color);
            font-size: 13.5px;
            vertical-align: middle;
        }}

        .table tr.test-row {{
            transition: background 0.15s;
        }}

        .table tr.test-row:hover {{
            background: rgba(0, 0, 0, 0.01);
        }}

        /* 按钮和徽章等小组件 */
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            gap: 4px;
        }}

        .badge-success {{ background: #d1fae5; color: #065f46; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-secondary {{ background: #f1f5f9; color: #475569; }}

        .priority-P0 {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}
        .priority-P1 {{ background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }}
        .priority-P2 {{ background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
        .priority-P3 {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}

        /* 接口方法彩色徽标 */
        .endpoint-container {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
        }}

        .method-badge {{
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            color: #ffffff !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            line-height: 1.2;
        }}

        .method-get {{ background-color: #3b82f6; }}
        .method-post {{ background-color: #10b981; }}
        .method-put {{ background-color: #f59e0b; }}
        .method-delete {{ background-color: #ef4444; }}
        .method-patch {{ background-color: #8b5cf6; }}
        .method-other {{ background-color: #6b7280; }}

        .path-text {{
            color: var(--text-primary);
            font-weight: 500;
        }}

        .duration-fast {{ color: #10b981; }}
        .duration-slow {{ color: #d97706; font-weight: 600; }}

        /* 报错崩溃栈框 */
        .error-detail-container {{
            background: #0f131a;
            border: 1px solid #2d3139;
            border-radius: 8px;
            margin: 8px 0;
            overflow: hidden;
        }}

        .error-detail-header {{
            background: #161b22;
            padding: 10px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #2d3139;
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 600;
        }}

        .error-detail-content {{
            margin: 0;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
            line-height: 1.6;
            color: #d1d5db; /* 默认浅白，关键词着色由 JS 接管 */
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
        }}

        .btn-action {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12.5px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .btn-action:hover {{
            background: var(--bg-main);
            border-color: var(--text-secondary);
        }}

        .btn-copy {{
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-secondary);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.2s;
        }}

        .btn-copy:hover {{
            color: var(--text-primary);
            border-color: rgba(255, 255, 255, 0.3);
            background: rgba(255, 255, 255, 0.05);
        }}

        /* Toast 气泡通知 */
        .toast-notification {{
            position: fixed;
            top: 24px;
            right: 24px;
            background: #10b981;
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.3), 0 4px 6px -2px rgba(16, 185, 129, 0.15);
            font-weight: 600;
            font-size: 13.5px;
            z-index: 1000;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .toast-notification.show {{
            opacity: 1;
            transform: translateY(0);
        }}

        /* 空状态容器 */
        .empty-state-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 60px 20px;
            text-align: center;
        }}

        .empty-state-icon {{
            width: 56px;
            height: 56px;
            color: var(--text-muted);
            margin-bottom: 16px;
            stroke-width: 1.5;
        }}

        .empty-state-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 6px;
        }}

        .empty-state-desc {{
            font-size: 13px;
            color: var(--text-secondary);
            max-width: 360px;
        }}

        .footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 12px;
            padding: 24px;
            margin-top: 40px;
            border-top: 1px solid var(--border-color);
        }}

        .hiddenRow {{
            display: none;
        }}
    </style>
</head>
<body>
    <!-- Toast 通知容器 -->
    <div id="toast" class="toast-notification">
        <svg style="width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <span class="toast-text">复制成功！</span>
    </div>

    <!-- 导航栏 -->
    <nav class="navbar">
        <div class="navbar-brand">
            <svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path></svg>
            <span>API 自动化测试报告</span>
        </div>
        <div class="navbar-title">{self.title}</div>
    </nav>

    <div class="container-fluid">
        <!-- 统计面板 -->
        <div class="stats-grid">
            <!-- 总数 -->
            <div class="stat-card total">
                <div class="stat-header">
                    <span class="stat-title">用例总数</span>
                    <div class="stat-icon total">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
                    </div>
                </div>
                <div class="stat-number">{total}</div>
                <div class="stat-rate">
                    <span class="badge" style="background: rgba(59, 130, 246, 0.1); color: #2563eb;">100%</span>
                    <span>全部已生成用例</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-success" style="width: 100%; background-color: var(--color-info);"></div>
                </div>
            </div>

            <!-- 通过 -->
            <div class="stat-card passed">
                <div class="stat-header">
                    <span class="stat-title">通过用例</span>
                    <div class="stat-icon passed">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    </div>
                </div>
                <div class="stat-number" style="color: var(--color-pass);">{passed}</div>
                <div class="stat-rate">
                    <span class="badge badge-success">{pass_rate}%</span>
                    <span>通过占比</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-success" style="width: {pass_rate}%"></div>
                </div>
            </div>

            <!-- 失败 -->
            <div class="stat-card failed">
                <div class="stat-header">
                    <span class="stat-title">失败用例</span>
                    <div class="stat-icon failed">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                    </div>
                </div>
                <div class="stat-number" style="color: var(--color-fail);">{failed}</div>
                <div class="stat-rate">
                    <span class="badge badge-warning">{fail_rate}%</span>
                    <span>失败占比</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-warning" style="width: {fail_rate}%"></div>
                </div>
            </div>

            <!-- 错误 -->
            <div class="stat-card error">
                <div class="stat-header">
                    <span class="stat-title">错误用例</span>
                    <div class="stat-icon error">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>
                    </div>
                </div>
                <div class="stat-number" style="color: var(--color-error);">{error}</div>
                <div class="stat-rate">
                    <span class="badge badge-danger">{error_rate}%</span>
                    <span>错误占比</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-danger" style="width: {error_rate}%"></div>
                </div>
            </div>

            <!-- 跳过 -->
            <div class="stat-card skipped">
                <div class="stat-header">
                    <span class="stat-title">跳过用例</span>
                    <div class="stat-icon skipped">
                        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 9a1 1 0 000 2h4a1 1 0 100-2H8z"></path></svg>
                    </div>
                </div>
                <div class="stat-number" style="color: var(--text-muted);">{skipped}</div>
                <div class="stat-rate">
                    <span class="badge badge-secondary">{skip_rate}%</span>
                    <span>跳过占比</span>
                </div>
                <div class="progress">
                    <div class="progress-bar bg-secondary" style="width: {skip_rate}%"></div>
                </div>
            </div>
        </div>

        <!-- 双列排版：基本信息 & 动态图表 -->
        <div class="dashboard-row">
            <!-- 运行基本信息 -->
            <div class="info-card">
                <div class="info-card-header">
                    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <span>环境与运行配置摘要</span>
                </div>
                <div class="info-card-body">
                    <div class="info-list">
                        <div class="info-item">
                            <span class="info-item-label">测试执行人</span>
                            <span class="info-item-value">{html.escape(self.tester) if self.tester else "-"}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-item-label">运行总耗时</span>
                            <span class="info-item-value" style="color: #2563eb;">{duration_str}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-item-label">测试启动时间</span>
                            <span class="info-item-value">{start_time_str}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-item-label">测试结束时间</span>
                            <span class="info-item-value">{end_time_str}</span>
                        </div>
                        <div class="info-item full-width">
                            <span class="info-item-label">测试描述说明</span>
                            <span class="info-item-value" style="font-weight: 400; color: var(--text-secondary);">{html.escape(self.description) if self.description else "-"}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 数据可视化图表 -->
            <div class="info-card">
                <div class="info-card-header">
                    <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 3.055A9.003 9.003 0 1020.945 13H11V3.055z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path></svg>
                    <span>测试数据分布概览</span>
                </div>
                <div class="info-card-body" style="height: calc(100% - 53px); display: flex; align-items: center; justify-content: center; min-height: 220px; padding: 20px 30px;">
                    <div class="charts-grid" style="width: 100%;">
                        <!-- SVG 环形进度图 -->
                        <div class="chart-box">
                            <svg class="progress-ring" width="120" height="120">
                                <circle class="progress-ring__background" stroke="#e2e8f0" stroke-width="8" fill="transparent" r="50" cx="60" cy="60" />
                                <circle class="progress-ring__circle" stroke="var(--color-pass)" stroke-dasharray="314.16 314.16" stroke-dashoffset="{dashoffset}" stroke-width="8" stroke-linecap="round" fill="transparent" r="50" cx="60" cy="60" transform="rotate(-90 60 60)" />
                                <text x="50%" y="45%" text-anchor="middle" dominant-baseline="middle" fill="var(--text-primary)" font-size="20" font-weight="800" font-family="'Inter', sans-serif">{pass_rate}%</text>
                                <text x="50%" y="68%" text-anchor="middle" dominant-baseline="middle" fill="var(--text-secondary)" font-size="11" font-weight="600" font-family="'Inter', sans-serif">通过率</text>
                            </svg>
                        </div>
                        <!-- 自适应柱状图 -->
                        <div class="chart-box">
                            <div class="bar-chart">
                                <div class="bar-col">
                                    <span class="bar-val" style="color: var(--color-pass);">{passed}</span>
                                    <div class="bar-item bar-passed" style="height: {passed_height}px;"></div>
                                    <span class="bar-label">通过</span>
                                </div>
                                <div class="bar-col">
                                    <span class="bar-val" style="color: var(--color-fail);">{failed}</span>
                                    <div class="bar-item bar-failed" style="height: {failed_height}px;"></div>
                                    <span class="bar-label">失败</span>
                                </div>
                                <div class="bar-col">
                                    <span class="bar-val" style="color: var(--color-error);">{error}</span>
                                    <div class="bar-item bar-error" style="height: {error_height}px;"></div>
                                    <span class="bar-label">错误</span>
                                </div>
                                <div class="bar-col">
                                    <span class="bar-val" style="color: var(--text-muted);">{skipped}</span>
                                    <div class="bar-item bar-skipped" style="height: {skipped_height}px;"></div>
                                    <span class="bar-label">跳过</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 搜索与状态过滤器面板 -->
        <div class="control-bar">
            <!-- 实时过滤搜索框 -->
            <div class="search-box">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                <input type="text" id="searchInput" placeholder="搜索接口、测试用例ID、描述、场景类型或优先级...">
            </div>

            <!-- 状态过滤群组 -->
            <div class="filter-group">
                <button class="filter-btn active" onclick="filterStatus('all', this)">
                    <span>全部摘要</span>
                    <span class="btn-badge">{total}</span>
                </button>
                <button class="filter-btn" onclick="filterStatus('passed', this)" style="color: var(--color-pass);">
                    <span>通过</span>
                    <span class="btn-badge" style="color: var(--color-pass);">{passed}</span>
                </button>
                <button class="filter-btn" onclick="filterStatus('failed', this)" style="color: var(--color-fail);">
                    <span>失败</span>
                    <span class="btn-badge" style="color: var(--color-fail);">{failed}</span>
                </button>
                <button class="filter-btn" onclick="filterStatus('error', this)" style="color: var(--color-error);">
                    <span>错误</span>
                    <span class="btn-badge" style="color: var(--color-error);">{error}</span>
                </button>
                <button class="filter-btn" onclick="filterStatus('skipped', this)">
                    <span>跳过</span>
                    <span class="btn-badge">{skipped}</span>
                </button>
            </div>
        </div>

        <!-- 测试用例执行明细 -->
        <div class="table-card">
            <div class="table-responsive">
                <table class="table" id="testTable">
                    <thead>
                        <tr>
                            <th>测试用例ID</th>
                            <th>描述 / 测试点</th>
                            <th>接口路径</th>
                            <th>场景类型</th>
                            <th>优先级</th>
                            <th>执行耗时</th>
                            <th>结果</th>
                            <th>报错诊断</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                        <!-- 动态空状态行 -->
                        <tr id="emptyStateRow" class="hiddenRow">
                            <td colspan="8">
                                <div class="empty-state-container">
                                    <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75l-2.489-2.489m0 0a3.375 3.375 0 10-4.773-4.773 3.375 3.375 0 004.774 4.774zM21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                    <div class="empty-state-title">未找到匹配的结果</div>
                                    <div class="empty-state-desc">请尝试调整搜索关键字或筛选不同的状态类别</div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 页脚 -->
        <div class="footer">
            由 api-testcase-creator 自动生成
        </div>
    </div>

    <script>
        let currentStatus = 'all';
        let currentQuery = '';

        // 展示与收缩报错详细堆栈
        function showDetail(id) {{
            const el = document.getElementById(id);
            if (!el) return;
            if (el.classList.contains('hiddenRow')) {{
                el.classList.remove('hiddenRow');
            }} else {{
                el.classList.add('hiddenRow');
            }}
        }}

        // 触发自适应 Toast 通知
        function showToast(message) {{
            const toast = document.getElementById('toast');
            if (!toast) return;
            toast.querySelector('.toast-text').textContent = message;
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 2000);
        }}

        // 复制堆栈文本到剪贴板
        function copyError(id) {{
            const el = document.getElementById(id);
            if (!el) return;
            const text = el.textContent;
            navigator.clipboard.writeText(text).then(() => {{
                showToast('报错堆栈已成功复制到剪贴板！');
            }}).catch(err => {{
                // 降级使用 textarea 复制
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                document.body.appendChild(textarea);
                textarea.select();
                try {{
                    document.execCommand('copy');
                    showToast('报错堆栈已成功复制到剪贴板！');
                }} catch (e) {{
                    console.error('复制失败', e);
                }}
                document.body.removeChild(textarea);
            }});
        }}

        // 多维度联合实时检索逻辑
        function updateFilters() {{
            const rows = document.querySelectorAll('.test-row');
            const query = currentQuery.toLowerCase().trim();
            let visibleRows = 0;
            
            rows.forEach(row => {{
                const status = row.getAttribute('data-status');
                const textContent = row.textContent.toLowerCase();
                
                const matchesStatus = (currentStatus === 'all' || status === currentStatus);
                const matchesSearch = (!query || textContent.includes(query));
                
                const detailId = row.id.replace('t', 'detail_');
                const detailRow = document.getElementById(detailId);
                
                if (matchesStatus && matchesSearch) {{
                    row.style.display = '';
                    visibleRows++;
                }} else {{
                    row.style.display = 'none';
                    if (detailRow) {{
                        detailRow.classList.add('hiddenRow');
                    }}
                }}
            }});

            const emptyState = document.getElementById('emptyStateRow');
            if (emptyState) {{
                if (visibleRows === 0) {{
                    emptyState.classList.remove('hiddenRow');
                }} else {{
                    emptyState.classList.add('hiddenRow');
                }}
            }}
        }}

        // 单选过滤器切换
        function filterStatus(status, btn) {{
            currentStatus = status;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            updateFilters();
        }}

        // 绑定搜索输入框事件
        document.getElementById('searchInput').addEventListener('input', function(e) {{
            currentQuery = e.target.value;
            updateFilters();
        }});

        // 报错崩溃栈关键词着色逻辑
        function highlightTraceback(text) {{
            let htmlText = text;
            // 红色高亮错误类型与常见库的异常
            htmlText = htmlText.replace(/([\\w\\.]+Error:.*)/g, '<span style="color: #f87171; font-weight: 600;">$1</span>');
            htmlText = htmlText.replace(/(Skipped:.*)/g, '<span style="color: #94a3b8; font-weight: 500;">$1</span>');
            // 蓝色高亮文件路径与行号
            htmlText = htmlText.replace(/(File &quot;[^&]+&quot;, line \\d+)/g, '<span style="color: #60a5fa; font-weight: 500; text-decoration: underline;">$1</span>');
            // 绿色高亮测试函数名
            htmlText = htmlText.replace(/(in \\w+)/g, '<span style="color: #34d399; font-weight: 500;">$1</span>');
            // 橙色高亮断言对比
            htmlText = htmlText.replace(/(assert .*)/g, '<span style="color: #fbbf24;">$1</span>');
            // 白色高亮 Stacktrace 头
            htmlText = htmlText.replace(/(Stacktrace:)/g, '<span style="color: #ffffff; font-weight: bold; border-bottom: 1px solid #2d3139; padding-bottom: 2px;">$1</span>');
            return htmlText;
        }}

        // 页面加载完成后应用堆栈着色
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('.error-detail-content').forEach(pre => {{
                pre.innerHTML = highlightTraceback(pre.innerHTML);
            }});
        }});
    </script>
</body>
</html>"""

def parse_pytest_output(output: str) -> List[TestResult]:
    """解析 pytest 输出，提取测试结果"""
    import re
    results = []
    lines = output.split('\n')

    for line in lines:
        line = line.strip()

        # 检测测试用例行
        if line.startswith("PASSED") or line.startswith("FAILED") or \
           line.startswith("ERROR") or line.startswith("SKIPPED"):
            # 解析测试 ID
            parts = line.split(" ", 1)
            if len(parts) >= 2:
                outcome = parts[0].lower()
                test_id = parts[1].strip()

                # 提取接口和测试点
                endpoint = ""
                test_doc = ""
                if "::" in test_id:
                    # 格式: test_file.py::TestClass::test_method
                    parts = test_id.split("::")
                    if len(parts) >= 3:
                        test_doc = parts[-1]

                # 创建测试结果
                result = TestResult(
                    test_id=test_id,
                    test_doc=test_doc,
                    outcome=outcome,
                    duration=0.0,
                    message=""
                )
                results.append(result)

    return results
