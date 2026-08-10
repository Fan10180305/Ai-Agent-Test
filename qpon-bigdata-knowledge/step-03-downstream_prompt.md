# Step 03: 下游依赖全量测绘

## 角色定义
代码考古学家 + 依赖拓扑分析师。你的任务是从 `DubboReferenceConfig`、`infrastructure/service/` 下的所有网关类、以及全局 `@DubboReference` 注解扫描中，还原本服务的完整下游依赖图。你不推测调用意图，不做"是否合理"的评判，只忠实记录代码中的事实。

【项目类型说明】本项目经结构探测确认为非 Java/Maven 项目（ACTUAL_MODULE_PREFIX=NON_JAVA）。
模板中涉及 Java 特有路径（如 pom.xml、-start/、-app/、-dao/、-client/ 等）和 Java 特有概念
（如 DubboReferenceConfig、MyBatis、ShardingSphere、RocketMQ 等）的扫描节，执行 Agent 应：
1. 识别该节的分析意图（如「提取外部依赖契约」、「还原数据模型」、「审计异步机制」等）；
2. 将意图映射到本项目实际存在的等价物（如 Airflow DAG、Python 算子、SQL/BigQuery、配置文件、CLI 工具链等）；
3. 对无等价物的扫描节明确标注「N/A：本项目无对应结构，原因：[一句话说明]」，不跳过、不虚构。
4. **工作区边界约束覆盖**：模板中所有「若 `<project>-xxx/` 不存在 → 必须立即停止」的硬熔断指令，在 NON_JAVA 模式下**自动失效**，改为按上述第 1-3 条规则处理。禁止因 Java 路径不存在而触发熔断。
模板是引导分析思考的框架，不是死脚本，请充分发挥语义推断能力产出等深度的知识库内容。

【扫描边界硬约束】本次知识库的代码事实权威范围严格限定为工作区内的 `dags/` 目录（含子目录）。
禁止以仓库其他目录（如 scripts/、ai-knowledge-knowledge/）作为业务事实来源；仅可读取协作协议与产出目录。

## 上下文
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。本步骤聚焦下游依赖：Dubbo 消费者、HTTP 调用、其他协议调用。

## 最高指令挂载
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典（位于 `.cursor/rules/collaboration-protocol.mdc`）。

# 0. 核心接力策略（最高执行优先级）

Step03: expand BQ FQN/SQL along 441 sensor edges and 1077 factory tasks; track ES/Feishu/Datastream sinks; dags/ only

**[执行准则]**: 以上为上一步指挥官转交的"强制任务"。你必须优先响应并回显证据，否则将被判定为考古失败。

# 0.5 项目军规（项目级行为约束）

意图路由：先读知识库入口再改代码；Skill 优先调度流水线。
强制红线：禁止 macOS 专有 sed；路径锚定；Shell set -euo pipefail。
双写要求：改调度逻辑须同步更新知识库。
本轮相关约束：扫描权威范围为 dags/；产出写入 qpon-bigdata-knowledge/；NON_JAVA 语义映射。

**[执行准则]**: 项目军规对本步分析与写回具有高优先级约束，不得被普通先验信息覆盖。

## 先验知识注入

### 前序步骤 [!SUCCESS] 摘要
```
> [!SUCCESS] 对外契约测绘闭环验证
> - 扫描范围：dags/；airflow_config + DAG 入口 create_* + Sensor 边 + schemas
> - 提取结果：18 共享符号；1077 工厂任务注册；441 活 Sensor 边；16 DTO
> - WRITE_TARGET: qpon-bigdata-knowledge/02_External_Contracts.md
> - WRITE_RESULT: UPDATED
> - WRITE_BYTES: 26114
> - WRITE_SHA256: 5e05527ba9f8d53afee14d795e62b428f3714bd230fc3a57b956ad1e8acfaa7e
> - NO_CHANGE_REASON: N/A
> [!RELAY]
> - Context: create_composer_bq_task/python_task/external_sensor; BQ asia-southeast2 / oppo-gcp-prod-digfood-129869; 441 sensor edges
> - Constraint: Step03 沿 Sensor 边与工厂任务展开 task 内 BQ FQN/SQL；追踪 ES/Feishu/Datastream 落点；禁止 scripts/
```

如果 Step 0 产出了 `Legacy_qpon-bigdata_Claims.md`，请静默读取其"下游依赖声称"章节作为本步骤的验真 checklist。注意：该文件内容是旧文档声称，不是事实。


---

## 任务：下游依赖全量测绘

### 扫描顺序（严格按此顺序执行，不允许跳步）

**Step A：定位 DubboReferenceConfig**
- 全局搜索 `class DubboReferenceConfig`，找到统一配置类完整路径
- 完整读取该文件至 EOF，逐个提取每个 `@DubboReference` 注解字段及对应 `@Bean` 方法
- 对每个字段提取：接口全限定类名、registry、check、retries、timeout（如有）、loadbalance（如有）

**Step B：扫描 infrastructure/service/ 下所有文件**
- 用 LS/Glob 列出 `infrastructure/service/` 目录完整文件树
- 逐个读取每个 Java 类（含已注释的类）
- 记录：注入的外部接口字段、直接调用的方法名、调用条件（灰度开关/if 分支）
- **关键**：若某字段注入了外部接口但该类自身未直接调用（实际调用委托给其他 Gateway），必须标注为"注入但未直接调用，实际路由到: XxxGateway"
- **关键**：若整个类已被注释掉，标注"类级别注释，依赖失活"

**Step C：全局补充搜索**
- 搜索 `@DubboReference`、`@Reference` 注解，捕获未在 DubboReferenceConfig 集中注册的游离引用
- 搜索 `HttpClientUtils`、`RestTemplate`、`OkHttp`、`HttpClient` 等关键词，定位所有 HTTP 调用点
- 若存在自定义 HTTP 工具类，读取其实现，提取连接超时/读取超时的实际数值和配置来源

**Step D：调用点逆向追踪（每个 Dubbo 接口必须逐一执行）**
- 对 DubboReferenceConfig 中每个接口，全局搜索其接口名（短类名）在业务代码中的引用
- 按以下规则分类记录：
  - **直接调用**：`fooService.method()` 出现在业务类方法体中 → 记录调用方类名 + 方法名 + 接口方法 + 调用场景
  - **经由 Manager/Facade 间接调用**：接口被 Manager 封装，业务类调用 Manager → 同时记录 Manager 层和最终业务调用方
  - **注入但自身未调用，委托给 Gateway**：如 `ProductRewardDistributeService` 注入了 `LocalLifeOrderService` 但未直接调用 → 标注"注入未调用，实际通过 OrderServiceGateway 路由"
  - **幽灵依赖**：注册且注入，但全量代码中无任何方法调用 → 标注"幽灵依赖"

**Step E：HTTP 调用链路完整追踪**
- 对每个 HTTP 调用点，从最终业务触发方逐层追踪到 HTTP 工具类
- 格式：`业务触发方 → 中间层1 → 中间层2(@Async?) → HTTP工具类 → 目标URL来源`
- 异步层（`@Async` 注解的方法所在类）必须显式标注

---

## 提取任务

### 1. Dubbo 消费者接口全量清单

| 序号 | 接口全限定类名 | 所属外部服务（artifactId） | registry | check | retries | timeout | loadbalance |
|------|--------------|--------------------------|---------|-------|---------|---------|-------------|

说明：
- timeout 未显式配置时，写"未配置（继承全局默认）"，不写推测值
- 所属外部服务从 import 路径的 groupId/artifactId 推断，不杜撰中文服务名

### 2. 实际调用点追踪

对每个接口独立成节，列出：
1. 所有**直接调用方**（类名 + 方法名 + 接口方法 + 场景）
2. 所有**经由 Manager/Facade 的间接业务触发方**（标注经由哪个中间类）
3. **注入但未直接调用**的情况（标注实际调用路径）
4. 重量级别（基于去重后实际调用的接口方法数）：
   - 🔴 重度依赖（>5 个不同方法）
   - 🟡 中度依赖（2-5 个不同方法）
   - 🟢 轻度依赖（1 个方法）

### 3. 超时与容错配置审计

**3.1 全局 Dubbo 配置**
- 明确标注配置文件完整路径（区分 `main/resources` 和 `test/resources`）
- 提取：全局 timeout、retries、loadbalance、threadpool、threads

**3.2 接口级配置汇总表**

| 接口短类名 | retries | timeout（接口级） | 备注 |
|-----------|---------|-----------------|------|

**3.3 熔断降级**：检查 Sentinel/Hystrix 配置，未发现则显式写"未发现显式熔断降级配置"

### 4. HTTP/其他协议调用清单

**4.1 HTTP 调用点表**

| 业务触发方 | 完整调用链路 | 目标 URL 来源 | HTTP 方法 | 连接超时(ms) | 读取超时(ms) | 含异步层 |
|----------|------------|-------------|---------|------------|------------|--------|

规则：
- 完整调用链路**不允许跳过中间层**，每个中间类必须列出
- 异步层写"是（@Async in XxxClass）"或"否"
- 目标 URL 来源写"动态配置（Heracles key: xxx, fileName: xxx）"或"硬编码: xxx"

**4.2 其他协议**：gRPC/WebSocket 等，未发现则显式写"未发现"

### 5. 外部依赖拓扑图

**5.1 按外部服务分组**：以 client JAR artifactId 为单位，汇总接口列表和整体依赖级别

**5.2 ASCII 拓扑图**：三层结构：本服务 → 外部服务 → 接口，每接口标注重量级别

**5.3 幽灵依赖识别**
- 分两类列出：
  - **幽灵依赖**：在 DubboReferenceConfig 中注册，全量代码无方法调用
  - **类级别注释失活**：注入该接口的类整体已注释掉
- 未发现则显式写"无幽灵依赖"

### 6. Step 01 遗漏追踪

基于代码搜索事实，逐一回答（不允许猜测）：

a) Step 01 中标注"需确认"的 client 依赖，代码中是否有实际调用？调用了什么接口？哪个类调用？
b) Step 01 POM 出现但未找到调用的 client，是否确认为幽灵依赖？
c) 是否存在 Step 01 POM 未出现、但代码中以其他方式引入的外部依赖？

### 7. 旧文档交叉验证摘要

**有旧文档（LEGACY_STATUS=HAS_DOCS）时输出，NO_DOCS 时跳过。**

格式规则：
- ✅ 已验证：合并一行「旧文档声称 N 条下游依赖，代码验证 M 条完全吻合」
- ❌ 不符：逐条列出（旧文档声称 vs 代码实际）
- 🆕 新发现：旧文档未提及但代码中存在的调用
- 幽灵依赖（旧文档声称存在但代码未找到调用）：逐个列出

---

## Action
在 `qpon-bigdata-knowledge/` 目录下生成 `03_Downstream_Dependencies.md`

---

## Constraint — 工业级底线

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `DubboReferenceConfig` 或 `infrastructure/service/` 在工作区内不存在，必须立即停止并输出：`❌ 未在工作区找到 [路径]，无法完成审计。请确认 PROJECT_NAME 与目标项目一致。` 禁止推断替代路径，禁止访问工作区外目录。

**严防静默截断**：
- DubboReferenceConfig 中每个 `@DubboReference` 字段和每个 `@Bean` 方法必须逐个提取，不允许省略
- `infrastructure/service/` 下每个文件必须逐个读取，含已注释的类，注释状态如实标注
- HTTP 调用链路必须追踪到完整层次，不允许跳过中间层（尤其是异步网关层）
- 如果 Dubbo 消费者数量超过 30 个，优先保证接口名+超时配置完整，调用点追踪可精简到"调用方类名+场景"

**专业性底线**：
- 超时/重试数值直接写数字，不做"是否合理"评判
- 幽灵依赖只陈述"注册但未找到调用点"的事实，不推测原因
- 外部服务名从 client JAR 的 artifactId 推断，不杜撰中文服务名
- 网关类中"注入了但未直接调用"的字段，必须如实标注，不能算作调用点
- 调用链路中的异步层（`@Async`）必须显式标注，不能与同步调用混同
- 全局 Dubbo 配置文件路径必须区分 `main/resources` 与 `test/resources`，不能混淆
- `3.3 配置分析`节：**禁止**出现"原因推测"、"可能偏短"等主观评判语句，只允许陈述数值事实

---

## 结尾标准审计闭环

> [!SUCCESS] 下游依赖测绘闭环验证
> - 扫描范围：DubboReferenceConfig + infrastructure/service/（[N]个文件）+ 全局注解搜索 + HTTP调用点搜索
> - 提取结果：[X] 个外部服务、[Y] 个 Dubbo 消费者接口、[Z] 个直接调用点、[W] 个 HTTP 调用点
> - 幽灵依赖：[N] 个（注册但未调用）；类级别注释失活：[M] 个
> - 超时配置：全局默认来自 [配置文件路径]，值为 [T]ms；[M] 个接口有自定义超时
> - Step 01 遗漏追踪：[client-a] [状态]、[client-b] [状态]
> - 旧文档验证：[A] 项已验证 / [B] 项不符 / [C] 项新发现（NO_DOCS 时写 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对数据模型分析有决定性影响的依赖事实，如：幽灵依赖、超时异常、关键下游服务的数据格式要求等]
> - **推演约束 (Constraint)**: [基于下游依赖发现，强制 Step 04 重点关注的数据映射或状态流转细节]
> - **物理锚点 (Anchors)**: [对应依赖配置文件路径及行号]

**重要额外指令：完成所有分析和文件写入后，必须在响应的最后原样输出 [!SUCCESS] 审计闭环块到控制台 Stdout，以便指挥官提取。禁止仅写入文件。**

**[!SUCCESS] 写入回执（固定字段，必须输出）**
- WRITE_TARGET: <本步目标知识文件相对路径>
- WRITE_RESULT: UPDATED | NO_CHANGE
- WRITE_BYTES: <写入后文件字节数，整数>
- WRITE_SHA256: <写入后文件 SHA256>
- NO_CHANGE_REASON: <仅当 WRITE_RESULT=NO_CHANGE 时必填；否则写 N/A>

约束：
1) WRITE_RESULT=UPDATED 时，WRITE_BYTES 与 WRITE_SHA256 必须基于写入后的真实文件；
2) WRITE_RESULT=NO_CHANGE 时，必须给出 NO_CHANGE_REASON，禁止留空；
3) 若无法确认以上字段的真实性，必须显式宣告失败，禁止输出伪造回执。
