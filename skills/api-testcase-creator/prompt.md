# 接口测试用例生成 Skill — api-testcase-creator

> 从 OpenAPI/Swagger 接口文档自动生成测试用例和 pytest 自动化代码。
> 程序做确定性的事，LLM 做需要创造力的事，用户在关键节点确认。
> 本 Skill 负责生成，运行测试请使用 `/api-testcase-runner`。

---

## 0. 初始化检查（每次触发自动执行）

1. 检查 `.api-testcase-assets/api-checkpoints.md` 是否存在：
   - 存在 → 继续
   - 不存在 → 提示用户创建并**中止流程**。
2. 检查 `.api-testcase-assets/api-review-dimensions.md` 是否存在，同上。
3. 读取 `.api-testcase-assets/project.config.md`（若存在），从中载入以下上下文：
   - 项目名称、项目英文标识
   - API 基础地址、认证方式
   - 业务域列表
   - 默认优先级规则、评审默认应用维度
4. **配置校验（强制阻断）**：检查 `project.config.md` 是否包含 `[填写` 开头的占位符。若检测到任何占位符，**直接中止流程**，输出：
   ```
   [BLOCK] project.config.md 中存在未填写的占位符，无法继续：
     - [填写项目中文名] → 请替换为实际项目名称
     - [填写英文缩写] → 请替换为实际英文标识
     - [填写姓名] → 请替换为测试负责人姓名
   请先完善配置，再重新触发 /api-testcase-creator。
   ```
   **不提供「是否继续」选项，必须填写完整后才能进入阶段 1。**
5. 初始化通过后，输出：

```
[OK] 资产加载成功
[DIR] 检查点索引：.api-testcase-assets/api-checkpoints.md
[DIR] 评审点索引：.api-testcase-assets/api-review-dimensions.md
[DIR] 项目配置：.api-testcase-assets/project.config.md（已载入上下文）
[DIR] 解析脚本：.api-testcase-assets/scripts/parse_spec.py
[DIR] JSON 修复脚本：.api-testcase-assets/scripts/repair_json.py
[DIR] 生成脚本：.api-testcase-assets/scripts/gen_testcode.py
[DIR] 验证脚本：.api-testcase-assets/scripts/validate_code.py
[DIR] 运行脚本：.api-testcase-assets/scripts/run_tests.py
>> 开始接口测试用例生成流程，共 7 个阶段，每步需您确认后继续。
```

---

## 1. 接口文档输入（阶段 1/7）

**提示用户：**

```
【阶段 1 — 接口文档输入】
请提供接口文档（选择一种）：
  A. OpenAPI 3.0 文件路径（.json / .yaml）
  B. Swagger 2.0 文件路径（.json / .yaml）
  C. 接口文档 URL（我将下载并解析）

请输入接口文档来源类型（A-C）并提供对应内容：
```

**收到输入后执行：**

- 若为 A/B 类型（本地文件）：
  1. 使用 Bash 执行解析脚本：
     ```
     python3 .api-testcase-assets/scripts/parse_spec.py '<文件路径>'
     ```
  2. 将输出的 JSON 保存备用

- 若为 C 类型（URL）：
  1. 使用 WebFetch 或 Bash + curl 下载文件到临时路径
  2. 执行解析脚本

**解析完成后，展示摘要供用户确认：**

```markdown
## 接口解析结果（请确认）

共解析到 N 个接口，M 个模块：

### [模块名1] (X 个接口)
| 方法 | 路径 | 说明 | 参数数 | 需认证 |
|------|------|------|--------|--------|
| POST | /api/orders | 创建订单 | 3 | 是 |
| GET | /api/orders | 查询订单列表 | 2 | 是 |

### [模块名2] (Y 个接口)
| 方法 | 路径 | 说明 | 参数数 | 需认证 |
|------|------|------|--------|--------|

### 接口依赖关系
- [依赖说明，如有]

[OK] 若以上解析正确，请回复「确认」继续阶段 2。
[FAIL] 若需修正，请指出错误内容后重新确认。
```

**用户确认后**，执行以下操作：
1. 提取模块名作为标识
2. **模块名清理**：移除文件系统不允许的字符
3. 创建本次运行的子目录：`.api-testcase-assets/history/<YYYYMMDD>_<HHMMSS>_<模块名>/`
4. 将解析结果写入 `.api-testcase-assets/history/<运行目录>/0-接口解析.md`
5. 后续所有文件均写入此子目录

---

## 2. 测试用例生成（阶段 2/7）

**触发条件**：用户确认阶段 1 结果后执行

**执行步骤：**

### 2.1 程序化生成基础用例

使用 Bash 执行以下 Python 代码，调用基础用例生成器：

```python
import sys
sys.path.insert(0, '.api-testcase-assets')
from framework.parsers.openapi_parser import OpenAPIParser
from framework.generators.base_case_gen import BaseCaseGenerator
import json

# 解析接口
parser = OpenAPIParser()
endpoints = parser.parse('<接口文件路径>')

# 生成基础用例
generator = BaseCaseGenerator()
cases = generator.generate(endpoints)

# 输出
print(json.dumps(cases, ensure_ascii=False, indent=2))
```

或者直接基于解析结果 JSON，在 prompt 中描述生成逻辑，由 LLM 执行生成。

**基础用例覆盖范围（程序自动推导）：**
- 每个接口：正向用例（参数全合法）
- 每个必填参数：缺失测试
- 每个字段：类型错误测试
- 有数值约束的字段：边界值测试（min/max/越界）
- 有长度约束的字段：边界值测试（minLength/maxLength）
- 有枚举的字段：非法枚举值测试
- 需认证的接口：无 Token / 伪造 Token 测试

### 2.2 LLM 补充业务场景用例

读取 `.api-testcase-assets/api-checkpoints.md`，按分类展示所有检查点：

```
【阶段 2 — 检查点选择 + 业务场景补充】
读取检查点索引，请选择适用于本次接口的检查点编号：

>> 鉴权与权限（API-AUTH）
  [AUTH-001] 无 Token 访问需认证接口 → 401
  [AUTH-002] Token 过期后访问 → 401

>> 业务逻辑（API-BIZ）
  [BIZ-001] 创建订单后库存应减少
  [BIZ-002] 已支付订单不能重复支付

>> 数据校验（API-DATA）
  [DATA-001] 响应 JSON 结构与接口文档一致
  [DATA-002] 列表接口返回条数 <= page_size

>> 幂等性与并发（API-IDEM）
  [IDEM-001] 同一请求重复提交 → 幂等结果
  [IDEM-003] 并发修改同一资源 → 最终一致

[NOTE] 请输入检查点编号（多个用逗号分隔，如：AUTH-001,BIZ-001）
   也可输入「全选」或「跳过」。
```

收到选择后，基于接口语义 + 选中的检查点，生成补充用例：
- 业务逻辑场景（如：下单后库存减少）
- 跨接口流程（如：登录 → 创建 → 支付 → 查询）
- 幂等性/并发场景

### 2.3 合并 + 展示

将程序化基础用例 + LLM 补充用例合并，统一编号，展示完整用例表：

```markdown
## 测试用例表（初稿）

| 用例ID | 所属接口 | 测试点 | 请求参数 | 前置条件 | 预期结果 | 检查点 | 场景类型 | 优先级 |
|--------|---------|--------|---------|---------|---------|--------|---------|--------|
| TC-001 | POST /api/orders | 正向创建订单 | product_id="P001", quantity=2 | 已登录 | 200, order_id 非空 | API-BASIC | 正向 | P0 |
| TC-002 | POST /api/orders | 缺少 product_id | quantity=2 | 已登录 | 400, error 含 "product_id" | API-001 | 异常 | P0 |
| TC-003 | POST /api/orders | quantity 边界值 0 | product_id="P001", quantity=0 | 已登录 | 400 | API-003 | 边界 | P1 |
| TC-004 | POST /api/orders | 未登录创建订单 | product_id="P001", quantity=2 | 未登录 | 401 | AUTH-001 | 异常 | P0 |

> 共生成 X 条用例，覆盖正向 X / 异常 X / 边界 X / 并发 X 条

[OK] 请回复「进入评审」进入阶段 3，或直接告诉我需要修改的用例编号和修改内容。
```

将用例表写入 `.api-testcase-assets/history/<运行目录>/1-用例准备.md`

---

## 3. 评审优化（阶段 3/7）

**触发条件**：用户回复「进入评审」后执行

**执行步骤：**

### 3.1 评审维度选择

读取 `.api-testcase-assets/api-review-dimensions.md`，展示评审维度：

```
【阶段 3 — 评审优化】
请选择评审维度（默认已选：PARAM-01,PARAM-02,AUTH-01,DATA-01）：

>> 参数校验（PARAM）
  [PARAM-01] 所有必填参数均有缺失测试用例
  [PARAM-02] 所有字段均有类型错误测试用例
  [PARAM-03] 有数值约束的字段均有边界值测试

>> 鉴权测试（AUTH）
  [AUTH-01] 所有需认证接口均有无 Token 测试
  [AUTH-02] 所有需认证接口均有伪造 Token 测试

>> 业务场景（BIZ）
  [BIZ-01] 核心业务流程有完整正向用例
  [BIZ-02] 业务规则约束有反向用例

>> 数据校验（DATA）
  [DATA-01] 成功响应有状态码断言
  [DATA-02] 关键响应字段有值断言

[NOTE] 请输入维度编号（多个用逗号分隔），或「使用默认」，或「跳过」。
```

### 3.2 执行评审

对当前用例表，按选定的评审维度逐一检查：

对于每个维度，检查用例表是否满足该维度的所有评审点，输出：

```markdown
### 评审结果 — 参数校验（PARAM）

| 评审点 | 状态 | 说明 |
|--------|------|------|
| PARAM-01 必填参数缺失测试 | ✅ 通过 | 所有必填参数均有对应缺失测试 |
| PARAM-02 类型错误测试 | ⚠️ 部分通过 | 字段 X 缺少类型错误测试 |
| PARAM-03 边界值测试 | ❌ 未通过 | 字段 Y 有 minimum 约束但无边界值测试 |

**建议新增用例：**
- TC-NEW-001: 字段 X 类型错误（string 填 int）→ 400
- TC-NEW-002: 字段 Y 边界值 minimum=1 → 200
- TC-NEW-003: 字段 Y 边界值 below minimum=0 → 400
```

### 3.3 用户决策

```
评审完成，请选择处理方式：
  [1] 全部接受 — 将所有建议新增/修改的用例加入用例表
  [2] 部分接受 — 告诉我接受哪些（如：接受 PARAM 和 AUTH 的建议）
  [3] 跳过 — 不做修改，直接进入阶段 4
```

用户选择后，更新用例表，写入：
- `.api-testcase-assets/history/<运行目录>/1-评审记要.md`（更新后的用例表）
- `.api-testcase-assets/history/<运行目录>/1-评审报告.md`（评审详情）

---

## 4. 代码生成（阶段 4/7）

**触发条件**：用户确认评审结果后执行

**执行步骤：**

### 4.1 准备用例数据

将最终用例表转为 JSON 格式，先保存为 `testcases.raw.md`：

```python
# 将用例表解析为 JSON
# 每条用例包含: id, endpoint, test_point, request, precondition, expected, checkpoint, scene_type, priority
```

然后执行 JSON 修复与 schema 校验，输出标准化后的 `export_data.json`：

```bash
python3 .api-testcase-assets/scripts/repair_json.py \
    .api-testcase-assets/history/<运行目录>/testcases.raw.md \
    .api-testcase-assets/history/<运行目录>/export_data.json \
    --schema .api-testcase-assets/templates/testcases.schema.json
```

若修复或 schema 校验失败，展示错误清单，并按错误清单重新输出 `testcases.raw.md` 后再次校验。校验通过后，后续代码生成必须以 `export_data.json` 为准。

### 4.2 生成 pytest 代码

使用 Bash 执行代码生成脚本：

```bash
python3 .api-testcase-assets/scripts/gen_testcode.py \
    .api-testcase-assets/history/<运行目录>/export_data.json \
    .api-testcase-assets/history/<运行目录>/code/tests \
    --project "<项目名称>" \
    --base-url "<API 基础地址>"
```

### 4.3 展示生成结果

```markdown
## 代码生成结果

已生成 pytest 代码到 `.api-testcase-assets/history/<运行目录>/code/tests/`：

| 文件 | 说明 |
|------|------|
| tests/test_order.py | 订单模块测试（12 个用例） |
| tests/test_user.py | 用户模块测试（8 个用例） |
| tests/conftest.py | 全局 fixture（auth_client, config） |
| tests/api_client.py | API 请求封装 |
| tests/config.yaml | 环境配置模板 |
| tests/requirements.txt | Python 依赖 |

[OK] 请回复「验证代码」进入阶段 5，或告诉我需要修改的内容。
```

---

## 5. 代码验证 + 后续选择（阶段 5/5）

**触发条件**：用户确认代码后执行

**执行步骤：**

使用 Bash 执行验证脚本：

```bash
python3 .api-testcase-assets/scripts/validate_code.py \
    .api-testcase-assets/history/<运行目录>/code/tests
```

**验证内容：**
1. py_compile 语法检查
2. import 检查
3. 测试方法存在性检查
4. pytest --collect-only 用例收集

**验证结果输出：**

```markdown
## 代码验证结果

已检查 N 个文件
[OK] 语法检查通过
[OK] import 检查通过
[INFO] 收集到 X 个测试用例

若有错误：
[FAIL] 发现 N 个错误:
  - [test_order.py] 语法错误: ...
  - [test_user.py] 警告: 文件中未找到 test_ 开头的测试方法
```

**错误处理：**
- 语法错误 → 自动修复并重新验证
- import 错误 → 提示用户补充依赖
- 收集失败 → 检查 conftest/fixture 问题

### 5.2 验证通过后 — 选择后续操作

验证通过后，展示分支选择：

```markdown
## 代码生成完成

已生成并验证通过的文件：
| 文件 | 说明 |
|------|------|
| tests/test_*.py | 测试用例文件（N 个） |
| tests/conftest.py | 全局 fixture |
| tests/api_client.py | API 请求封装 |
| tests/config.yaml | 环境配置模板 |
| tests/requirements.txt | Python 依赖 |

代码位置：`.api-testcase-assets/history/<运行目录>/code/tests/`

---

请选择后续操作：

  [A] 部署代码到项目
      将测试代码复制到项目 tests/ 目录，不立即运行
      适合：后续在 CI/CD 中运行，或稍后手动运行

  [B] 立即运行测试
      需要配置 API 地址和认证信息
      适合：本地调试，快速验证
      提示：也可稍后使用 /api-testcase-runner 运行

  [C] 导出 Postman Collection
      生成可导入 Postman 的 Collection 文件
      适合：分享给团队，导入其他工具

  [D] 完成，稍后处理
      结束本次流程，代码保存在历史目录中

请输入选择（A/B/C/D）：
```

### 选项 A：部署代码到项目

```
请选择部署路径：
  [1] 部署到 ./tests/（推荐）
  [2] 保持在当前目录，不部署
  [3] 指定其他路径
```

部署完成后：

```markdown
## 部署完成

测试代码已部署到 ./tests/

### 文件清单
| 文件 | 说明 |
|------|------|
| tests/test_*.py | N 个测试文件 |
| tests/conftest.py | fixture 定义 |
| tests/api_client.py | API 客户端封装 |
| tests/config.yaml | 配置文件（需填写） |
| tests/requirements.txt | Python 依赖 |

### 后续步骤

1. **填写配置**：编辑 `tests/config.yaml`，填写 API 地址和认证信息
2. **安装依赖**：`cd tests && pip install -r requirements.txt`
3. **运行测试**：`pytest -v` 或使用 `/api-testcase-runner`

### 运行测试
如需立即运行测试，请使用 `/api-testcase-runner`。
```

**更新历史索引**：在 `.api-testcase-assets/history/history-index.md` 追加本次运行记录。

### 选项 B：立即运行测试

```
[INFO] 即将启动测试运行流程。
[INFO] 这将调用 /api-testcase-runner 来执行测试。

请确认以下条件已满足：
  □ config.yaml 中的 base_url 已填写实际 API 地址
  □ 认证信息已配置（token 或账号密码）
  □ API 服务可达

是否已准备好？（确认/返回选择）
```

若用户确认：
1. 提示用户输入测试代码目录路径（默认为历史目录下的 code/tests）
2. 提示用户输入报告输出目录（默认为历史目录下的 report）
3. 调用 `/api-testcase-runner` 的逻辑执行测试

### 选项 C：导出 Postman Collection

使用 Bash 执行 Postman 生成脚本：

```bash
python3 .api-testcase-assets/scripts/gen_postman.py \
    .api-testcase-assets/history/<运行目录>/code/tests/export_data.json \
    .api-testcase-assets/history/<运行目录>/postman_collection.json \
    --name "<项目名称> API 测试" \
    --base-url "<API 基础地址>"
```

导出完成后：

```markdown
## Postman Collection 导出完成

文件路径：`.api-testcase-assets/history/<运行目录>/postman_collection.json`

### 使用方法
1. 打开 Postman
2. 点击 Import → 选择文件
3. 选择刚生成的 collection.json
4. 配置环境变量：base_url、token
5. 运行 Collection
```

### 选项 D：完成

```markdown
## 流程完成

本次生成的所有文件保存在：
`.api-testcase-assets/history/<运行目录>/`

### 文件清单
| 文件 | 说明 |
|------|------|
| 0-接口解析.md | 接口解析结果 |
| 1-用例准备.md | 测试用例表 |
| 1-评审记要.md | 评审后的用例表 |
| 1-评审报告.md | 评审详情 |
| code/tests/ | pytest 测试代码 |

### 后续使用
- 运行测试：使用 `/api-testcase-runner`
- 查看用例：编辑 `1-用例定稿.md`
- 重新生成：再次触发 `/api-testcase-creator`
```

**更新历史索引**：在 `.api-testcase-assets/history/history-index.md` 追加本次运行记录。

---

## 附录：目录和文件命名规范

| 项目 | 格式 | 示例 |
|------|------|------|
| 运行目录 | `<YYYYMMDD>_<HHMMSS>_<模块名>` | `20260624_143000_订单模块` |
| 用例ID | `TC-XXX`（三位补零） | TC-001, TC-012, TC-100 |
| 检查点编号 | `<域缩写>-<序号>` | AUTH-001, BIZ-002 |
| 评审点编号 | `<维度缩写>-<序号>` | PARAM-01, DATA-02 |

## 附录：Token 追踪

每次运行在每个阶段结束时记录 token 消耗，阶段 7 输出全阶段汇总对比表。
