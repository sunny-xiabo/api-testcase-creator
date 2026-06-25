# api-testcase-creator

从 OpenAPI/Swagger/Postman 接口文档自动生成测试用例和 pytest 自动化代码，支持评审优化与 XTestRunner 样式 HTML 报告（零依赖）。

## 功能特性

### 双 Skill 架构

本项目提供两个独立的 Skill，职责分离，可独立使用：

| Skill | 命令 | 说明 |
|-------|------|------|
| **api-testcase-creator** | `/api-testcase-creator` | 从接口文档生成测试用例和代码 |
| **api-testcase-runner** | `/api-testcase-runner` | 运行测试用例并生成报告 |

**设计原则**：生成和运行解耦，避免因环境问题阻断用例生成流程。

### 输入支持

| 格式 | 版本 | 说明 |
|------|------|------|
| OpenAPI | 3.0.x | JSON / YAML |
| Swagger | 2.0 | JSON / YAML，自动转换为 OpenAPI 3.0 |
| Postman Collection | v2.1 | JSON，支持文件夹嵌套 |

格式自动检测，无需手动指定。

### 生成能力

| 产出物 | 说明 |
|--------|------|
| 测试用例表 | 结构化用例，含测试点、请求参数、预期结果、优先级 |
| pytest 代码 | 可执行的自动化测试代码，含 fixture、请求封装、配置 |
| Postman Collection | 可直接导入 Postman 运行，含断言脚本 |
| HTML 报告 | XTestRunner 样式，含统计图表、场景分布、优先级分布（零依赖） |
| Markdown 运行摘要 | 轻量文本报告，适合归档和分享 |
| JSON 修复与校验 | 提取/修复 LLM 输出的 JSON，并按用例 schema 校验 |

### 用例覆盖

程序自动生成以下类型的测试用例（无需 LLM）：

- **正向用例** -- 参数全合法，预期成功
- **必填参数缺失** -- 逐个必填字段缺失，预期 400
- **参数类型错误** -- 逐个字段填错误类型，预期 400
- **边界值测试** -- 有 min/max/minLength/maxLength 约束的字段
- **枚举值测试** -- 有 enum 约束的字段，测试非法值
- **认证测试** -- 无 Token / 伪造 Token，预期 401

### 多平台分发

构建后自动适配以下平台：

- **Claude Code** -- `/api-testcase-creator`、`/api-testcase-runner` 斜杠命令
- **Cursor** -- Skill 系统
- **Codex (OpenAI Agents)** -- source-command

## 快速开始

### 1. 一键初始化

```bash
cd api-testcase-creator
./setup.sh
```

默认会创建本地 `.venv`、安装依赖、构建 `dist`。如果希望使用已有 Python 环境：

```bash
# 使用当前系统 python3 / conda 环境
./setup.sh --system

# 使用指定 Python
./setup.sh --python /path/to/python
```

### 2. 初始化并部署到目标项目

```bash
# 默认使用 .venv
./setup.sh /path/to/your/project

# 使用已有环境并部署
./setup.sh --system /path/to/your/project

# 覆盖已有资产
./setup.sh /path/to/your/project --force
```

也可以分两步执行：

```bash
./build.sh
./init-api-testcase.sh _template /path/to/your/project
```

### 3. 环境检查

```bash
./doctor.sh
```

部署后的目录结构：

```
your-project/
├── .claude/commands/
│   ├── api-testcase-creator.md   # 生成测试用例和代码
│   └── api-testcase-runner.md    # 运行测试和生成报告
├── .api-testcase-assets/
│   ├── project.config.md          # 项目配置（需填写）
│   ├── api-checkpoints.md         # 检查点库
│   ├── api-review-dimensions.md   # 评审期望库
│   ├── review-dimensions.yaml
│   ├── scene-types.yaml
│   ├── templates/
│   ├── scripts/
│   └── history/
└── .gitignore
```

### 4. 配置项目

编辑 `.api-testcase-assets/project.config.md`，填写：

- 项目名称、英文标识
- API 基础地址、认证方式
- 业务域列表

### 5. 生成用例

在 Claude Code 中触发：

```
/api-testcase-creator
```

按提示提供 OpenAPI/Swagger/Postman 文件，确认后自动生成用例和代码。

### 6. 运行测试（可选）

生成代码后，可以：

- **立即运行**：在阶段 5 选择「立即运行测试」
- **稍后运行**：使用 `/api-testcase-runner` 独立运行

```
/api-testcase-runner
```

## 工作流

### Skill 1: api-testcase-creator（生成）

| 阶段 | 说明 | 处理方式 |
|------|------|---------|
| Stage 0 | 初始化检查 | 校验配置文件完整性 |
| Stage 1 | 接口文档输入 | 程序解析 OpenAPI/Swagger/Postman |
| Stage 2 | 测试用例生成 | 程序生成基础用例 + LLM 补充业务场景 |
| Stage 3 | 评审优化 | 多维度评审（参数/鉴权/业务/数据/流程/性能/安全/幂等） |
| Stage 4 | 代码生成 | 模板生成 pytest 代码 |
| Stage 5 | 代码验证 + 分支选择 | 验证代码 → 选择：部署/运行/导出/完成 |

### Skill 2: api-testcase-runner（运行）

| 阶段 | 说明 | 处理方式 |
|------|------|---------|
| Stage 1 | 测试代码定位 | 选择历史目录或指定路径 |
| Stage 2 | 环境预检 | 配置检查、依赖检查、API 可达性 |
| Stage 3 | 运行测试 | 冒烟/完整/干跑模式 |
| Stage 4 | 结果展示 | 通过率、失败列表、报告路径 |
| Stage 5 | 失败分析 | 失败详情、分类汇总、修复建议 |

## 项目结构

```
api-testcase-creator/
├── skills/
│   ├── api-testcase-creator/            # Skill 1: 生成测试用例和代码
│   │   ├── meta.yaml                    # Skill 元数据
│   │   └── prompt.md                    # 5 阶段工作流 prompt
│   └── api-testcase-runner/             # Skill 2: 运行测试和生成报告
│       ├── meta.yaml                    # Skill 元数据
│       └── prompt.md                    # 5 阶段工作流 prompt
├── framework/
│   ├── parsers/                         # 接口文档解析层
│   │   ├── base.py                      # 解析器基类
│   │   ├── endpoint_model.py            # 统一接口数据模型
│   │   ├── openapi_parser.py            # OpenAPI 3.0 + Swagger 2.0
│   │   └── postman_parser.py            # Postman Collection v2.1
│   ├── generators/                      # 代码生成层
│   │   ├── base_case_gen.py             # 程序化用例生成器
│   │   ├── code_gen.py                  # 用例 -> pytest 代码
│   │   └── postman_gen.py               # 用例 -> Postman Collection
│   ├── runners/                         # 测试运行层
│   │   └── pytest_runner.py             # pytest 运行 + 报告生成
│   ├── scripts/                         # CLI 工具
│   │   ├── parse_spec.py                # 解析接口文档
│   │   ├── gen_testcode.py              # 生成 pytest 代码
│   │   ├── gen_postman.py               # 生成 Postman Collection
│   │   ├── validate_code.py             # 代码验证
│   │   ├── repair_json.py               # 修复并校验 LLM JSON 输出
│   │   └── run_tests.py                 # 运行测试 + 报告
│   ├── templates/
│   │   └── testcase-table-config.json   # 用例表列配置
│   │   └── testcases.schema.json        # 测试用例 JSON schema
│   ├── review-dimensions.yaml           # 8 维度评审定义
│   └── scene-types.yaml                 # 场景类型定义
├── projects/
│   └── _template/
│       ├── project.config.md            # 项目配置模板
│       ├── api-checkpoints.md           # API 检查点库
│       └── api-review-dimensions.md     # 评审期望库
├── build.py                             # 构建脚本
├── build.sh                             # 构建入口
├── init-api-testcase.sh                 # 部署脚本
└── README.md
```

## CLI 工具

### 解析接口文档

```bash
# 自动检测格式
python3 framework/scripts/parse_spec.py api-spec.json endpoints.json

# 指定格式
python3 framework/scripts/parse_spec.py api-spec.yaml --format openapi

# Postman Collection
python3 framework/scripts/parse_spec.py postman.json endpoints.json
```

### 生成 pytest 代码

```bash
python3 framework/scripts/gen_testcode.py \
    endpoints.json \
    ./tests \
    --project "我的项目" \
    --base-url "https://api.example.com"
```

### 修复并校验 LLM 输出 JSON

```bash
python3 framework/scripts/repair_json.py \
    llm-testcases.md \
    testcases.json \
    --schema framework/templates/testcases.schema.json
```

### 生成 Postman Collection

```bash
python3 framework/scripts/gen_postman.py \
    endpoints.json \
    postman_collection.json \
    --name "API 测试" \
    --base-url "https://api.example.com"
```

### 验证代码

```bash
python3 framework/scripts/validate_code.py ./tests
```

### 运行测试

```bash
# 完整模式
python3 framework/scripts/run_tests.py ./tests --mode full --report-dir ./report

# 冒烟模式（只跑 P0）
python3 framework/scripts/run_tests.py ./tests --mode smoke

# 干跑模式（只收集不运行）
python3 framework/scripts/run_tests.py ./tests --mode collect-only
```

## 生成代码示例

### pytest 测试代码

```python
class TestPostApiOrders:
    """POST /api/orders 接口测试"""

    def test_create_order_success(self, auth_client):
        """TC-001: 正向创建订单"""
        resp = auth_client.post("/api/orders", json={
            "product_id": "P001", "quantity": 2
        })
        assert resp.status_code == 200

    def test_missing_product_id(self, auth_client):
        """TC-002: 缺少必填参数 product_id"""
        resp = auth_client.post("/api/orders", json={"quantity": 2})
        assert resp.status_code == 400
        assert "product_id" in resp.text

    def test_quantity_below_min(self, auth_client):
        """TC-003: quantity 边界值 below_min = 0"""
        resp = auth_client.post("/api/orders", json={
            "product_id": "P001", "quantity": 0
        })
        assert resp.status_code == 400

    def test_no_auth(self, client):
        """TC-004: 无 Token 访问需认证接口"""
        resp = client.post("/api/orders", json={
            "product_id": "P001", "quantity": 2
        })
        assert resp.status_code == 401
```

### conftest.py

```python
@pytest.fixture(scope="session")
def auth_client(base_url, auth_info):
    """API 客户端（带认证）"""
    return ApiClient(base_url, auth=auth_info)

@pytest.fixture(scope="session")
def config():
    """项目配置"""
    return load_config()
```

### config.yaml

```yaml
env:
  base_url: "https://api-dev.example.com"
  timeout: 30

auth:
  type: bearer
  token: ""  # 填写实际 token

report:
  format: [html, markdown]
  title: "API 测试报告"
  tester: ""
  language: cn
```

## HTML 报告（XTestRunner 样式）

内置 XTestRunner 样式报告生成器，零依赖，包含：

- **导航栏** - 固定在顶部，显示报告标题
- **概述卡片** - 测试人员、时间、描述
- **统计卡片** - 通过/失败/错误/跳过，带进度条
- **柱状图** - CSS 实现，展示统计数据
- **状态筛选** - 摘要/通过/失败/错误/跳过
- **用例详情** - 可展开查看错误信息
- **响应式设计** - 支持移动端

## 检查点库

支持项目级别的检查点沉淀，分以下类别：

| 类别 | 编号前缀 | 说明 |
|------|----------|------|
| 鉴权与权限 | AUTH- | 无 Token、过期 Token、越权 |
| 业务逻辑 | BIZ- | 项目特定的业务规则 |
| 数据校验 | DATA- | 响应结构、字段值、分页 |
| 幂等并发 | IDEM- | 重复提交、并发修改 |
| 性能 | PERF- | 响应时间、大数据量 |
| 安全 | SEC- | 注入、敏感数据、路径遍历 |
| 跨接口流程 | CHAIN- | 上下游依赖、全链路 |

通用模式（必填缺失、类型错误、边界值）由程序自动推导，不需要在检查点库中维护。

## 评审维度

| 维度 | 编号 | 检查内容 |
|------|------|---------|
| 参数校验 | PARAM | 必填缺失、类型错误、边界值、枚举值 |
| 鉴权测试 | AUTH | 无 Token、伪造 Token、越权 |
| 业务场景 | BIZ | 正向流程、业务规则、状态流转 |
| 数据校验 | DATA | 状态码、响应字段、错误信息 |
| 流程覆盖 | CHAIN | 上下游依赖、数据传递 |
| 性能测试 | PERF | 响应时间、大数据量 |
| 安全测试 | SEC | 注入攻击、敏感数据暴露 |
| 幂等并发 | IDEM | 重复请求、并发操作 |

## 使用示例

### 场景 1：完整流程（生成 + 运行）

```
# 1. 生成测试用例和代码
/api-testcase-creator

# 2. 在阶段 5 选择「立即运行测试」
# 或者稍后运行：
/api-testcase-runner
```

### 场景 2：只生成代码（部署到 CI/CD）

```
# 1. 生成测试用例和代码
/api-testcase-creator

# 2. 在阶段 5 选择「部署代码到项目」

# 3. 将 tests/ 目录提交到 Git，配置 CI/CD 运行
```

### 场景 3：运行已有测试

```
# 直接运行已部署的测试
/api-testcase-runner

# 选择测试代码目录（./tests/ 或历史目录）
# 选择运行模式（冒烟/完整/干跑）
# 查看报告
```

## 运行模式说明

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 冒烟模式 | 只运行 P0 用例 | 首次运行、快速验证、CI/CD 快速检查 |
| 完整模式 | 运行全部用例 | 发版前全面验证、定期回归测试 |
| 干跑模式 | 只收集不运行 | 验证代码正确性、检查用例数量 |

## 报告格式

| 格式 | 说明 | 适用场景 |
|------|------|----------|
| HTML | 交互式报告，含图表 | 团队分享、详细分析 |
| Markdown | 轻量文本报告 | 归档、Git 提交、快速查看 |
| JUnit XML | 标准 CI 格式 | Jenkins、GitLab CI 等集成 |

## 依赖

### 项目依赖（构建和运行框架）

- Python 3.10+
- PyYAML

### 生成的测试代码依赖（运行测试时）

- pytest
- requests
- PyYAML
- pytest-html（可选，HTML 报告）

### 可选依赖

- XTestRunner（可选，使用原生 XTestRunner 报告）

## License

MIT
