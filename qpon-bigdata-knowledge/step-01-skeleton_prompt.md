# Step 01: 模块骨架与技术栈审计

## 角色定义
代码考古学家 + 构建工程分析师。你的任务是从 pom.xml 和配置文件中还原这个系统的物理骨架——模块依赖、技术栈版本、中间件接入。你不做业务逻辑分析,不读 Java 源码,只聚焦构建描述符和配置文件。

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

此外，作为全链路第一个接触项目源码的步骤，你的 [!RELAY] 必须额外包含：
- 本项目的实际技术栈清单（框架、包管理器、构建工具、测试框架）
- 项目的物理目录结构与各目录职责推断（聚焦 dags/）
- 对后续步骤（契约提取、数据模型、异步机制等）的具体扫描路径建议
这些信息将被指挥官用于后续步骤的接力注入，直接影响后续步骤的分析方向。

## 上下文
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。这是一个 Java/Maven 多模块项目,包含 6 个子模块。本步骤是知识库的第一步：从构建文件和配置文件中提取项目骨架事实。

## 最高指令挂载
在执行任何动作前,必须强制静默读取并绝对服从本项目的底层协作法典（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），你接下来的所有响应步调与输出规范,必须以该协议为最高准则。

# 0. 核心接力策略（最高执行优先级）

无先验接力偏好，请按标准考古规范执行。

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
NO_DOCS: LEGACY_COUNT=0, Step 0 skipped. Scan authority = dags/ only.
```

请静默读取 qpon-bigdata-knowledge/Legacy_qpon-bigdata_Claims.md,了解旧文档对本项目的声称。注意：该文件内容是旧文档声称,不是事实。你的任务是用代码事实验证或推翻这些声称。


## 任务: 物理骨架测绘与技术栈审计

请集中算力执行以下扫描：

### 扫描范围（严格限定）
1. 根目录 pom.xml（父 POM）
2. 每个子模块的 pom.xml（共 6 个子模块）
3. qpon-bigdata-start/src/main/resources/ 下所有配置文件
4. qpon-bigdata-start/src/test/resources/ 下所有配置文件（如存在）
5. columbus_build.sh（构建脚本）

### 提取任务

#### 1. 模块依赖关系图
- 从每个子模块的 pom.xml 中提取 <dependencies>,还原模块间的真实依赖关系
- 用树状结构呈现,标注每个依赖的 scope（compile/test/provided）
- 与旧文档声称的模块结构（Legacy_qpon-bigdata_Claims.md §2.4）进行交叉验证

#### 2. 核心中间件与第三方依赖雷达
- 从所有 pom.xml 中提取非 Spring Boot Starter 的重型依赖
- 每个依赖列出：groupId:artifactId、版本号、在本项目中的推测用途
- 重点关注：数据库驱动、ORM 框架、缓存框架、消息队列、RPC 框架、分库分表组件
- 与旧文档声称的技术栈（Legacy_qpon-bigdata_Claims.md §1）进行交叉验证

#### 3. 架构腐化与漂移嗅探（Red Flags）
- qpon-bigdata定位为"业务编排层",死盯以下信号：
  a) 是否有不符合该定位的异常依赖（如直接引入了不相关的业务 client）
  b) 模块间是否存在反向依赖或循环依赖
  c) test 模块是否泄露了不应有的依赖
  d) 是否有版本冲突或已弃用的依赖

#### 4. 配置文件坐标提取
- 从 heracles.properties 和其他配置文件中提取：
  a) 服务注册名、暴露端口
  b) 数据库连接坐标（数据库名、分库分表配置）
  c) Redis 连接配置
  d) RocketMQ 配置（nameserver、topic、group）
  e) Dubbo 配置（协议、端口、注册中心）
  f) 其他中间件连接信息
- 敏感信息（密码、密钥）用 [REDACTED] 替代,绝不输出

#### 5. 子模块物理职责定义
- 结合每个子模块的 pom.xml 依赖和包结构（仅看顶层包名,不读源码）,用一句话精准定义每个子模块的真实物理职责
- 与旧文档声称的模块职责（Legacy_qpon-bigdata_Claims.md §2.4）进行交叉验证

#### 6. 构建与部署坐标
- 从 columbus_build.sh 和父 POM 中提取：Maven 构建命令、JDK 版本要求、打包方式
- 从父 POM 提取：项目版本号、父 POM 坐标（parent）

## 输出要求

在 qpon-bigdata-knowledge/ 目录下生成 01_Module_Skeleton_and_Stack.md

## 约束条件 - 工业级底线

**输出格式锁定**：使用以下标题结构
```
### 1. 模块依赖关系图
### 2. 核心中间件与第三方依赖雷达
### 3. 架构腐化预警（Red Flags）
### 4. 配置文件坐标
### 5. 子模块物理职责定义
### 6. 构建与部署坐标
### 7. 旧文档交叉验证摘要
```

**第 7 节格式（有旧文档时输出，NO_DOCS 时跳过）**：
只列出差异条目：❌不符 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条技术栈/模块声称，其余均已代码验证」。
🔍无法从本步骤验证的条目单独列出，注明「需后续步骤确认」。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若核心扫描路径（如 pom.xml、构建脚本）在工作区内不存在，应按 NON_JAVA 规则映射到实际存在的等价物（如 package.json、Makefile、pyproject.toml 等）或如实记录为 N/A，禁止推断替代路径，禁止访问工作区外目录。

**严防静默截断**：
- 每个 pom.xml 必须寻址到 EOF,不允许跳过任何依赖项
- 配置文件必须完整读取,不允许省略任何配置项（敏感信息除外）
- 如果某个子模块的 pom.xml 为空或不存在,显式标注

**专业性底线**：
- 不做技术名词解释,直接列出版本号和用途
- 依赖用途写"推测用途",不写"这是xxx框架"
- 架构问题只陈述事实+风险,不给修复建议（那是后续步骤的事）

## 结尾标准审计闭环

```
> [!SUCCESS] 骨架测绘闭环验证
> - 扫描范围：父 POM + [N] 个子模块 POM + [M] 个配置文件 + 构建脚本
> - 提取结果：识别了 [X] 项中间件/第三方依赖,[Y] 项配置坐标
> - 架构预警：捕获了 [Z] 项潜在问题（Red Flags）
> - 旧文档验证：[A] 项已验证 / [B] 项不符 / [C] 项部分符合 / [D] 项无法验证
> - EOF 状态：已确认遍历至最后一行,无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对下一步契约提取有决定性影响的技术栈事实，如：发现 Dubbo/gRPC/REST 框架，client 模块路径，API 层位置等]
> - **推演约束 (Constraint)**: [基于事实，强制 Step 02 重点扫描的具体路径或模式]
> - **物理锚点 (Anchors)**: [对应配置文件路径或依赖声明行号]
```

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
