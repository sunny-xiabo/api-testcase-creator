# api-testcase-creator

LLM 驱动的 API 测试用例生成工具。它可以从 OpenAPI / Swagger / Postman 接口文档生成测试用例表、pytest 自动化代码、Postman Collection，并提供轻量多角色评审和 XTestRunner 样式 HTML 报告。

这个项目不是测试平台，而是一个可部署到目标项目中的 Skill 工具集：程序负责稳定解析和代码生成，LLM 负责业务场景补充、风险评审和用例优化。

## 核心能力

| 能力 | 说明 |
|------|------|
| 接口文档解析 | 支持 OpenAPI 3.0、Swagger 2.0、Postman Collection v2.x |
| 基础用例生成 | 自动生成正向、必填缺失、类型错误、边界值、枚举、鉴权异常用例 |
| LLM 业务补充 | 基于接口语义和检查点库补充业务流程、反向规则、幂等并发场景 |
| 多角色评审 | 参数边界、鉴权权限、业务流程、数据断言、安全幂等 reviewer 独立评审后汇总 |
| JSON 修复校验 | 使用 `json-repair` 修复 LLM 输出，并用 schema 校验结构化用例 |
| pytest 代码生成 | 生成可运行的测试文件、`conftest.py`、`api_client.py`、`config.yaml` |
| 测试运行报告 | 支持冒烟、完整、干跑模式，生成 Markdown 和零依赖 HTML 报告 |
| 多平台分发 | 构建 Claude Code、Cursor、Codex Agents 三类 Skill 文件 |

## 快速开始

### 初始化工具

```bash
git clone git@github.com:sunny-xiabo/api-testcase-creator.git
cd api-testcase-creator
./setup.sh
./doctor.sh
```

默认会创建本地 `.venv`、安装依赖并构建 `dist`。

如果想使用已有环境：

```bash
# 使用当前 python3 / conda 环境
./setup.sh --system

# 使用指定 Python
./setup.sh --python /path/to/python
```

### 部署到目标项目

```bash
# 初始化、构建并部署
./setup.sh /path/to/your-project

# 覆盖目标项目已有资产
./setup.sh /path/to/your-project --force
```

也可以分两步：

```bash
./build.sh --clean
./init-api-testcase.sh _template /path/to/your-project
```

部署后目标项目会得到：

```text
your-project/
├── .claude/commands/
│   ├── api-testcase-creator.md
│   └── api-testcase-runner.md
├── .cursor/skills/
├── .agents/skills/
├── .api-testcase-assets/
│   ├── project.config.md
│   ├── api-checkpoints.md
│   ├── api-review-dimensions.md
│   ├── review-dimensions.yaml
│   ├── scene-types.yaml
│   ├── templates/
│   ├── scripts/
│   ├── framework/
│   └── history/
└── .gitignore
```

### 配置目标项目

编辑：

```text
.api-testcase-assets/project.config.md
```

填写项目名称、API 基础地址、认证方式、测试负责人和业务域。配置中如果仍有 `[填写...]` 占位符，生成流程会阻断，避免在缺少上下文时生成低质量用例。

### 使用 Skill

在支持的 Agent 工具中执行：

```text
/api-testcase-creator
```

按提示提供 OpenAPI / Swagger / Postman 文件，确认解析结果后生成用例和代码。

运行已生成测试：

```text
/api-testcase-runner
```

## 生成流程

### `/api-testcase-creator`

| 阶段 | 说明 | 产物 |
|------|------|------|
| Stage 0 | 初始化检查，读取项目配置和检查点库 | 配置校验结果 |
| Stage 1 | 解析接口文档 | `0-接口解析.md`、接口摘要 |
| Stage 2 | 程序基础用例 + LLM 业务场景补充 | `1-用例准备.md` |
| Stage 3 | 多角色 reviewer 评审与主审汇总 | `1-评审报告.md`、`1-评审决策.md` |
| Stage 4 | JSON 修复校验并生成 pytest 代码 | `export_data.json`、`code/tests/` |
| Stage 5 | 验证代码并选择部署/运行/导出 | 校验结果、可选运行报告 |

### `/api-testcase-runner`

| 阶段 | 说明 |
|------|------|
| Stage 1 | 定位历史目录或指定测试代码目录 |
| Stage 2 | 检查配置、依赖、API 可达性 |
| Stage 3 | 冒烟、完整或干跑模式运行 pytest |
| Stage 4 | 输出通过率、失败列表和报告路径 |
| Stage 5 | 失败分析与修复建议 |

## 多角色评审

评审阶段采用轻量多 reviewer 模式，不做复杂平台化。

默认 reviewer：

| Reviewer | 关注点 |
|----------|--------|
| 参数边界 reviewer | 必填、类型、边界、枚举、pattern |
| 鉴权权限 reviewer | 无 Token、伪造 Token、越权、多角色 |
| 业务流程 reviewer | 业务规则、状态流转、跨接口链路 |
| 数据断言 reviewer | 响应字段、错误结构、分页、数据一致性 |
| 安全幂等 reviewer | 注入、敏感信息、重复提交、并发 |

上下文控制规则：

- 接口数超过 10 时按 tag/module 分批评审。
- 每个 reviewer 最多输出 5 条发现、5 条建议用例、3 条不适用项。
- 主 agent 会去重、合并、删除明显不适用建议，并按优先级汇总。
- 用户可以全部接受、部分接受、跳过，或补充关注点后再评一轮。

## JSON 修复与校验

LLM 输出给人看的 Markdown，也会输出给程序用的 JSON。进入代码生成前会先执行：

```bash
python framework/scripts/repair_json.py \
  testcases.raw.md \
  export_data.json \
  --schema framework/templates/testcases.schema.json
```

处理链路：

```text
LLM 输出 -> 提取 JSON -> json.loads -> json-repair 兜底 -> schema 校验 -> 标准 JSON
```

如果修复或校验失败，Skill 会展示错误清单，并要求重新输出结构化 JSON。

## CLI 工具

这些脚本既可在本仓库运行，也会部署到目标项目的 `.api-testcase-assets/scripts/`。

### 解析接口文档

```bash
python framework/scripts/parse_spec.py api-spec.json endpoints.json
python framework/scripts/parse_spec.py api-spec.yaml --format openapi
python framework/scripts/parse_spec.py postman_collection.json endpoints.json
```

### 生成 pytest 代码

```bash
python framework/scripts/gen_testcode.py \
  testcases.json \
  ./tests \
  --project "我的项目" \
  --base-url "https://api.example.com"
```

### 生成 Postman Collection

```bash
python framework/scripts/gen_postman.py \
  testcases.json \
  postman_collection.json \
  --name "API 测试" \
  --base-url "https://api.example.com"
```

### 验证生成代码

```bash
python framework/scripts/validate_code.py ./tests
```

### 运行测试

```bash
# 完整模式
python framework/scripts/run_tests.py ./tests --mode full --report-dir ./report

# 冒烟模式，只跑 P0
python framework/scripts/run_tests.py ./tests --mode smoke

# 干跑模式，只收集不执行
python framework/scripts/run_tests.py ./tests --mode collect-only
```

## 项目结构

```text
api-testcase-creator/
├── skills/
│   ├── api-testcase-creator/
│   │   ├── meta.yaml
│   │   └── prompt.md
│   └── api-testcase-runner/
│       ├── meta.yaml
│       └── prompt.md
├── framework/
│   ├── parsers/
│   ├── generators/
│   ├── runners/
│   ├── scripts/
│   ├── templates/
│   ├── review-dimensions.yaml
│   └── scene-types.yaml
├── projects/
│   └── _template/
├── dist/
├── tests/
├── report/
├── setup.sh
├── doctor.sh
├── build.py
├── build.sh
├── init-api-testcase.sh
└── requirements.txt
```

## 目录说明

| 路径 | 说明 |
|------|------|
| `skills/` | Skill 源文件，修改 prompt 后重新 build |
| `dist/` | 构建产物，包含 Claude / Cursor / Codex 分发文件 |
| `framework/parsers/` | OpenAPI、Swagger、Postman 解析 |
| `framework/generators/` | 测试用例、pytest 代码、Postman Collection 生成 |
| `framework/runners/` | pytest 运行和 HTML/Markdown 报告 |
| `framework/scripts/` | 可部署的 CLI 工具 |
| `framework/templates/` | 用例表配置和 JSON schema |
| `projects/_template/` | 部署到目标项目的配置、检查点、评审维度模板 |
| `report/` | 示例 HTML 报告 |
| `tests/` | 核心单元测试 |

## 支持格式

| 输入 | 支持情况 |
|------|----------|
| OpenAPI 3.0 | JSON / YAML |
| Swagger 2.0 | JSON / YAML，内部转换为 OpenAPI 3.0 结构 |
| Postman Collection | v2.x JSON，支持文件夹嵌套 |

Postman Collection 通常缺少完整 schema，因此从 Postman 生成的参数类型和 required 信息会弱于 OpenAPI / Swagger。

## 生成用例范围

程序自动生成：

- 正向调用
- 必填参数缺失
- 参数类型错误
- 数值边界值
- 字符串长度边界值
- 枚举非法值
- 无 Token / 伪造 Token

LLM 评审和补充：

- 业务规则反向用例
- 状态流转场景
- 跨接口链路
- 越权访问
- 响应字段断言
- 幂等和并发风险
- 安全风险场景

## 报告

内置 HTML 报告为 XTestRunner 样式，零依赖生成，包含：

- 通过、失败、错误、跳过统计
- 通过率和耗时
- 用例明细
- 失败详情展开
- 状态筛选
- 响应式布局

同时生成：

- Markdown 运行摘要
- JUnit XML
- 原始 pytest 输出日志

## 开发

初始化：

```bash
./setup.sh
```

检查环境：

```bash
./doctor.sh
```

运行测试：

```bash
uv run pytest tests -q
```

重新构建 Skill：

```bash
./build.sh --clean
```

如果使用自己的环境：

```bash
./setup.sh --system
./doctor.sh --system
```

## 依赖

框架依赖：

- Python 3.10+
- PyYAML
- json-repair

生成后的测试代码依赖：

- pytest
- requests
- PyYAML

HTML 报告使用内置生成器，不依赖 XTestRunner 或 pytest-html。

## License

MIT
