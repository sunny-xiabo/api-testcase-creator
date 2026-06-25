# API TestCase Creator

> LLM 驱动的 API 测试设计助手。
>
> 从 OpenAPI / Swagger / Postman 自动生成测试用例、pytest 自动化代码和 Postman Collection，并通过多 Reviewer 风险评审机制补充业务场景、权限场景、流程场景和幂等场景。

---

## 为什么需要它？

传统 API 测试设计通常存在两个问题。

### 方式一：纯人工设计

```text
阅读接口文档
    ↓
分析参数
    ↓
编写测试用例
    ↓
评审补充
```

问题：

- 耗时长
- 容易遗漏边界场景
- 测试经验难沉淀
- 不同测试人员质量差异大

### 方式二：纯 LLM 生成

```text
OpenAPI
    ↓
Prompt
    ↓
LLM
    ↓
测试用例
```

问题：

- 输出不稳定
- 容易出现幻觉
- 缺少项目上下文
- 用例质量难以保证

## API TestCase Creator 的思路

程序负责确定性部分。

LLM 负责测试专家思考过程。

```text
                OpenAPI / Swagger / Postman
                              │
                              ▼
                    接口解析与标准化
                              │
                              ▼
                   程序生成基础测试集
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         参数场景        边界场景        鉴权场景
                              │
                              ▼
                  多 Reviewer 风险评审
                              │
      ┌───────────┬───────────┬───────────┬───────────┐
      ▼           ▼           ▼           ▼           ▼
   参数专家    权限专家    业务专家    数据专家   安全幂等专家
                              │
                              ▼
                    主审汇总与去重
                              │
                              ▼
                     风险场景补充
                              │
                              ▼
                     JSON 校验修复
                              │
                              ▼
               pytest / Postman / HTML Report
```

## 核心理念

### Rule-based First

基础测试场景由程序生成：

- 正向用例
- 必填缺失
- 类型错误
- 边界值
- 枚举非法值
- 鉴权异常

避免把确定性问题交给 LLM。

### LLM Review Driven

LLM 不负责生成所有用例。

LLM 负责：

- 业务规则分析
- 风险识别
- 场景补洞
- 用例评审

这更接近资深测试工程师的工作方式。

### Knowledge Driven

支持项目级测试知识沉淀：

```text
.api-testcase-assets/
├── api-checkpoints.md
├── api-review-dimensions.md
├── scene-types.yaml
└── review-dimensions.yaml
```

项目经验可以持续积累和复用。

## 核心能力

| 能力 | 说明 |
|------|------|
| OpenAPI / Swagger / Postman 解析 | 自动识别格式并统一建模 |
| 基础测试生成 | 正向、边界、类型、鉴权场景 |
| 多 Reviewer 评审 | 参数、权限、业务、数据、安全幂等 |
| 风险场景补充 | 业务异常、越权、流程、幂等、并发 |
| JSON 修复校验 | json-repair + schema 校验 |
| pytest 代码生成 | fixture、配置、客户端封装 |
| Postman Collection | 可直接导入执行 |
| HTML 报告 | 零依赖 XTestRunner 风格 |
| 多平台分发 | Claude Code、Cursor、Codex Agents |

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

### 使用 Skill

先编辑目标项目中的配置：

```text
.api-testcase-assets/project.config.md
```

填写项目名称、API 基础地址、认证方式、测试负责人和业务域。配置中如果仍有 `[填写...]` 占位符，生成流程会阻断。

生成测试用例和代码：

```text
/api-testcase-creator
```

运行已生成测试：

```text
/api-testcase-runner
```

## 多 Reviewer 评审机制

评审阶段采用轻量专家组模式。

每个 Reviewer 聚焦单一领域：

| Reviewer | 关注点 |
|----------|--------|
| 参数 Reviewer | required、type、enum、boundary |
| 权限 Reviewer | Token、越权、多角色 |
| 业务 Reviewer | 业务规则、状态流转 |
| 数据 Reviewer | 响应结构、断言、分页 |
| 安全幂等 Reviewer | 注入、重复提交、并发 |

最终由主 Reviewer：

- 去重
- 合并
- 排序
- 过滤明显不适用建议
- 输出评审决策

上下文控制规则：

- 接口数超过 10 时按 tag/module 分批评审。
- 每个 reviewer 最多输出 5 条发现、5 条建议用例、3 条不适用项。
- 用户可以全部接受、部分接受、跳过，或补充关注点后再评一轮。

## 示例

输入：

```yaml
POST /orders

product_id:
  type: string
  required: true

quantity:
  type: integer
  minimum: 1
```

基础生成：

```text
✓ 正向创建订单
✓ product_id 缺失
✓ quantity 类型错误
✓ quantity < 1
✓ 无 Token
✓ 伪造 Token
```

评审补充：

```text
✓ 重复提交订单
✓ 库存不足
✓ 已下架商品
✓ 越权访问他人订单
✓ 并发创建订单
```

## 输出结果

### 测试用例表

结构化测试设计文档，适合评审、沉淀和二次修改。

### pytest 自动化代码

生成可执行测试代码、配置文件、API 客户端和 pytest fixture。

### Postman Collection

可直接导入 Postman 执行，包含基础断言脚本。

### HTML 测试报告

内置 XTestRunner 风格报告生成器，零依赖。

## 工作流

### `/api-testcase-creator`

| 阶段 | 说明 | 产物 |
|------|------|------|
| Stage 0 | 初始化检查，读取项目配置和检查点库 | 配置校验结果 |
| Stage 1 | 解析接口文档 | `0-接口解析.md`、接口摘要 |
| Stage 2 | 程序基础用例 + LLM 业务场景补充 | `1-用例准备.md` |
| Stage 3 | 多 Reviewer 风险评审与主审汇总 | `1-评审报告.md`、`1-评审决策.md` |
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

## 项目定位

API TestCase Creator 不是测试平台。

它是一个：

**可部署到项目内部的 AI 测试设计 Skill。**

通过：

- 程序化规则生成
- 项目知识库
- 多 Reviewer 风险评审
- 人工确认决策

帮助团队构建更加稳定、可复用的 API 测试设计流程。

## License

MIT
