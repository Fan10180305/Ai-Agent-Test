# 0. 核心接力策略（最高执行优先级）

Step07: audit Composer/Variable for Sensor timeout/slots/concurrency; TT webhook Variable/token reachability; write_es_service_url/es_* and Cloud Run timeouts; PubSub subscription + is_paused_upon_creation; logs/metrics for Sensor up_for_retry storms and callback send failures; dags/ only

**[执行准则]**: 以上为上一步指挥官转交的"强制任务"。你必须优先响应并回显证据，否则将被判定为考古失败。

# 0.5 项目军规（项目级行为约束）

意图路由：先读知识库入口再改代码；Skill 优先调度流水线。
强制红线：禁止 macOS 专有 sed；路径锚定；Shell set -euo pipefail。
双写要求：改调度逻辑须同步更新知识库。
本轮相关约束：扫描权威范围为 dags/；产出写入 qpon-bigdata-knowledge/；NON_JAVA 语义映射。

**[执行准则]**: 项目军规对本步分析与写回具有高优先级约束，不得被普通先验信息覆盖。

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

# Step 07: 配置体系与可观测性全量测绘

[Role] 配置与可观测性审计师。
你的任务是从代码中还原本服务的配置体系、缓存策略、错误码字典、日志规范。
这是运维排障的"最后一公里"——配置改错了服务会挂、缓存不一致会出脏数据、
错误码不清楚就无法定位问题、日志格式不统一就无法 grep。
你同时承担"衍生约束提炼"职责。

[Context]
我们正在为 qpon-bigdata（qpon-bigdata）构建 AI 可加载的项目知识库。
已完成步骤（具体数字由 001 根据前序产出动态注入）：
- Step 0: 旧文档声称（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已确认配置中心、缓存框架、中间件接入情况
- Step 03: 下游依赖 — 已完成，超时与容错配置已记录
- Step 04: 数据模型 — 已完成，TypeHandler 信息已记录
- Step 05: 业务编排 — 已完成，缓存使用点已初步发现
- Step 06: 异步机制 — 已完成，分布式锁和补偿机制已记录

本步骤是知识库考古阶段的最后一步。

已知关键线索（由 001 根据前序步骤动态注入）：
> [!SUCCESS] Step06 done
> WRITE_TARGET: qpon-bigdata-knowledge/06_Async_Jobs_and_Compensation.md
> WRITE_BYTES: 24630
> WRITE_SHA256: 1399d893486216cb21440a28f590448d09db1f8ca0740fb7d7bbf7e2cb2b4549
> NO_CHANGE_REASON: N/A

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件，建立先验认知：
1. qpon-bigdata-knowledge/01_Module_Skeleton_and_Stack.md — §4 配置坐标
2. qpon-bigdata-knowledge/06_Async_Jobs_and_Compensation.md — §8 衍生约束（格式参考）
如有旧文档：qpon-bigdata-knowledge/Legacy_qpon-bigdata_Claims.md — §7 风险声称、§8 待确认项


[Task: 配置体系与可观测性全量测绘]

### 扫描范围

**区域 A：配置文件**
- qpon-bigdata-start/src/main/resources/ — 全部配置文件
- qpon-bigdata-start/src/test/resources/ — 测试配置（对比差异）
- 全项目搜索 @Value、@ConfigurationProperties、Environment.getProperty 等配置注入点

**区域 B：缓存层**
- 全项目搜索 JetCache 相关注解（@Cached、@CacheUpdate、@CacheInvalidate、@CreateCache）
- 全项目搜索 RedisTemplate、StringRedisTemplate 的直接使用
- qpon-bigdata-service/src/main/java/**/infrastructure/repository/ — 带缓存逻辑的 Repository
- qpon-bigdata-service/src/main/java/**/infrastructure/configuration/ — 缓存配置类

**区域 C：错误码与异常**
- 全项目搜索自定义异常类（extends Exception/RuntimeException）
- 全项目搜索错误码常量/枚举（ErrorCode、ResultCode、BizCode、ErrorBean 等关键词）
- 扫描错误响应的构造模式

**区域 D：日志与监控**
- 搜索 log.error、log.warn 的高频使用模式
- 搜索 @Monitor、metrics、trace 等监控相关注解/类
- 搜索 MDC（Mapped Diagnostic Context）的使用

**区域 E：Spring 配置类**
- qpon-bigdata-service/src/main/java/**/infrastructure/configuration/ — 全部配置类
- qpon-bigdata-dao/src/main/java/**/configuration/ — 数据源配置类
- 搜索全项目 @Configuration 注解的类

### 提取任务

#### 1. 配置项决策清单
扫描必须全量（区域 A 每个配置文件逐行读取至 EOF），但**输出只保留对排障和需求交付有价值的配置项**，纯中间件连接参数合并一行。

**以下配置项必须显式列出**：
- 业务开关类（feature.xxx.enabled、灰度控制、降级开关）
- 超时/重试类（影响服务行为的超时参数）
- 缓存 TTL 类（影响数据一致性的过期时间）
- 分布式锁参数（锁过期时间、获取超时）
- MQ Topic/Group（消息路由相关）
- 定时任务调度参数（影响任务执行频率的）
- 环境差异配置（测试环境与生产环境行为不同的）

**以下配置项合并统计**：
- 数据库连接参数（JDBC URL/用户名/密码）→ 合并为一行：「数据库连接：[N 个数据源，库名列举，连接参数脱敏]」
- Redis 连接参数（host/port/password）→ 合并为一行：「Redis 连接：[集群/单机，地址脱敏]」
- Dubbo 框架参数（协议/端口/序列化）→ 合并为一行：「Dubbo 框架：[协议，端口，注册中心]」
- 日志框架参数 → 合并为一行：「日志：[框架，级别，格式]」

**输出格式（按功能分组）**：
```
**[分组名]**
| 配置 Key | 默认值/当前值 | 用途 | 环境差异 |
```

分组：业务开关 / 缓存参数 / 超时与容错 / MQ 路由 / 定时任务 / 中间件连接（合并统计）

敏感信息（密码、密钥）用 [REDACTED] 替代。

#### 2. 缓存策略全景
对每个缓存使用点提取：
a) 缓存方式（JetCache 注解 / RedisTemplate 直接操作）
b) 缓存 key 结构/命名规则
c) 过期时间（TTL）
d) 缓存更新策略（写穿、旁路、异步刷新）
e) 缓存失效策略（主动清除 / 自然过期）
f) 缓存雪崩/穿透防护（如有）
g) 被哪个业务场景使用

汇总表格：
| 缓存名/Key 模式 | 方式 | TTL | 更新策略 | 使用场景 |

如有旧文档待确认的缓存策略项，在本节末尾逐一给出明确结论。

#### 3. 错误码字典
扫描必须全量，但**输出改为按模块分组的简表**，不逐条平铺。

**输出格式**：
```
**[模块名] 错误码**（共 N 个，码值范围 XXXXXXX~XXXXXXX）
| 错误码值 | 常量名 | 使用场景（一句话） |
```

特别标注：
- 码值重复的条目（🔴 重复码值冲突）
- 无实际使用点的错误码（⚠️ 疑似废弃）

各模块分组完成后，输出一行汇总：「共 N 个错误码，分布在 M 个类/枚举中」。

#### 4. 异常处理体系
a) 自定义异常类清单（类名、继承链、使用场景）
b) 全局异常处理器（如有 @ExceptionHandler、@ControllerAdvice）
c) Dubbo 异常过滤器（如有自定义 Filter 处理异常）
d) 异常处理模式分析：是统一包装还是各自处理？
   吞异常的位置有哪些？（log.error 后 return null 或 continue 的模式）

#### 5. 日志规范分析
a) 日志框架（SLF4J + Logback / Log4j2 / 其他）
b) 日志格式模式（PatternLayout，如果配置文件中可见）
c) MDC 使用情况（TraceID、UserID 等）
d) 关键日志点采样（log.error 的 top 10 使用场景）
e) 日志级别分布（从代码中 log.debug/info/warn/error 的使用频率推断）

#### 6. Spring 配置类清单
对每个 @Configuration 类提取：
a) 类名 + 全限定路径
b) 注册的 Bean 清单
c) 配置的中间件/组件
d) 条件注解（@ConditionalOn...）

#### 7. 业务开关与特性标志
搜索代码中的业务开关模式：
a) 通过配置控制的功能开关（如 feature.xxx.enabled）
b) 灰度发布控制
c) 降级开关

#### 8. 衍生约束清单
从本步骤发现的事实中提炼约束：
| 约束编号 | 约束内容 | 来源事实 | 严重级别 |
| G-07-XX | 具体约束描述 | 本步骤第 N 节的具体发现 | 🔴强制/🟡建议 |

重点方向：
- 缓存 key 命名规范（从现有 key 模式中提炼）
- 错误码使用规范（从错误码体系中提炼，重点标注码值冲突问题）
- 配置变更注意事项（从配置项关联性中提炼）
- 日志规范（从现有日志模式中提炼）

[Action]
在 qpon-bigdata-knowledge/ 目录下生成 07_Config_and_Observability.md

[Constraint - 工业级底线]

**输出格式锁定**：使用以下标题结构
```
### 1. 配置项决策清单
### 2. 缓存策略全景
### 3. 错误码字典
### 4. 异常处理体系
### 5. 日志规范分析
### 6. Spring 配置类清单
### 7. 业务开关与特性标志
### 8. 衍生约束清单
### 9. 旧文档交叉验证摘要（有旧文档时输出，NO_DOCS 时跳过）
```

**第 9 节格式（有旧文档时）**：
只列出差异条目：❌不符 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条，其余均已代码验证」。
待确认项必须逐一给出明确结论（✅已确认 / ❌与声称不符 / ⚠️部分符合）。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `qpon-bigdata-start/src/main/resources/` 等扫描路径在工作区内不存在，必须立即停止并输出：`❌ 未在工作区找到 [路径]，无法完成审计。请确认 PROJECT_NAME 与目标项目一致。` 禁止推断替代路径，禁止访问工作区外目录。

**扫描完整性保证**：
- 扫描必须全量：区域 A~E 每个文件逐一读取至 EOF，不允许跳过
- 输出必须提炼：扫描全量 ≠ 输出全量，输出按本文档的格式规则提炼

**专业性底线**：
- 配置 key 原样列出，不翻译
- 缓存 TTL 写具体数值（秒/分），不做「是否合理」评判
- 错误码按代码中的值原样记录，码值重复必须标注
- 日志级别分布只统计事实，不评判
- 风险标注基于代码事实，不假设「可能存在但未看到的」保障

**结尾标准审计闭环**：

> [!SUCCESS] 配置与可观测性测绘闭环验证
> - 扫描范围：resources/ 配置文件 + 全项目缓存/错误码/日志/配置类搜索
> - 提取结果：[X] 个业务影响配置项、[Y] 个缓存点、[Z] 个错误码（[M] 个模块）、[W] 个配置类
> - 缓存覆盖：[N] 个业务场景使用缓存
> - 衍生约束：[D] 条（🔴 [E] 条强制 / 🟡 [F] 条建议）
> - 旧文档差异：❌不符 [A] 条 / 🆕新发现 [B] 条 / ✅其余 [C] 条已验证（NO_DOCS 时标注 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对模块深潜分析有决定性影响的配置事实，如：高风险配置项、缺失的监控覆盖、错误码体系的异常分布等]
> - **推演约束 (Constraint)**: [基于配置发现，强制 Step 08 深潜时重点关注的模块内部配置耦合或风险点]
> - **物理锚点 (Anchors)**: [对应配置文件路径及关键配置 key 行号]

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
