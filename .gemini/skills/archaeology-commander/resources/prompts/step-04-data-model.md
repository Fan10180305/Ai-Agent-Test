# Step 04: 数据模型与生命周期全量测绘

[Role] 数据模型考古学家。
你的任务是从 dao 模块中还原本服务的完整数据模型——
实体定义、表结构、索引设计、分库分表策略、MyBatis 映射的 SQL 操作全景。
你不分析业务逻辑，不读 service/app 模块，只聚焦"数据长什么样、怎么存、怎么查"。

[Context]
我们正在为 {{project_name}}（{{project_display_name}}）构建 AI 可加载的项目知识库。
已完成步骤（具体数字由 001 根据前序产出动态注入）：
- Step 0: 旧文档声称提取（NO_DOCS 时跳过交叉验证）
- Step 01: 骨架测绘 — 已确认 ShardingSphere 版本、数据库名、分片表初步线索
- Step 02: 对外契约 — 已完成，枚举定义可作为状态机字段值的参考
- Step 03: 下游依赖 — 已完成

本步骤聚焦 {{project_name}}-dao 模块，以及分库分表配置。

已知关键线索（由 001 根据前序步骤动态注入）：
{{step04_prior_findings}}

[最高指令挂载]
在执行任何动作前，必须强制静默读取并绝对服从本项目的底层协作法典
（位于 .cursor/rules/collaboration-protocol.mdc 或 .gemini/rules/collaboration-protocol.md 根据环境加载），
你接下来的所有响应步调与输出规范，必须以该协议为最高准则。

[先验知识注入]
请静默读取以下文件，建立先验认知：
1. {{output_dir}}01_Module_Skeleton_and_Stack.md — §2 依赖雷达（ShardingSphere）、§4 配置坐标（数据库连接）
2. {{output_dir}}02_External_Contracts.md — §3 枚举定义清单（作为状态机字段枚举值的参考来源）
如有旧文档：{{output_dir}}Legacy_{{project_name}}_Claims.md — §3 数据模型声称、§8 待确认项
{{evolution_mode_context}}

[Task: 数据模型全量测绘]

### 扫描范围（三个区域）

**区域 A：实体类（必扫）**
- {{project_name}}-dao/src/main/java/**/entity/ 下所有 .java 文件
- 逐文件读取至 EOF

**区域 B：MyBatis Mapper（必扫）**
- {{project_name}}-dao/src/main/java/**/mapper/ 下所有 Mapper 接口（.java）
- {{project_name}}-dao/src/main/resources/mapper/ 下所有 Mapper XML（.xml）
- 逐文件读取至 EOF

**区域 C：配置与基础设施（必扫）**
- {{project_name}}-dao/src/main/java/**/configuration/ — 数据源配置类
- {{project_name}}-dao/src/main/java/**/handler/ — MyBatis TypeHandler
- {{project_name}}-dao/src/main/java/**/typehandler/ — 类型处理器
- {{project_name}}-start/src/main/resources/ 和 src/test/resources/ 中与数据库相关的配置
- 全项目搜索 ShardingSphere 分片配置（sharding-jdbc 配置类或 YAML/properties）

### 提取任务

#### 1. 实体决策摘要
扫描必须全量（区域 A 每个 .java 逐文件读取至 EOF），但**输出只保留对排障和需求交付有价值的字段**，普通字段只写总数统计。

**以下字段必须显式列出**：
- 主键字段（标注 IdType 策略：AUTO / INPUT）
- 分片键字段（分片表必须标注，普通表跳过）
- 状态机字段（status/state/isFinish 等）——必须同步列出全部枚举值及含义（从 Step 02 枚举或代码中直接摘录，不推测）
- 外键关联字段（关联其他表的 ID；若关联分片表，标注 ⚠️跨分片风险）
- 有非标准注解的字段（@TableField(typeHandler=...)、@TableLogic、@Version）
- 时间范围控制字段（effectiveStartTime/effectiveEndTime 等影响数据有效性判断的）

**其余普通字段**：合并写成一行。

**写法规则（必须严格执行，不得跳过）**：
1. 先数清「总字段数」中有多少字段被上方各行（主键/状态机/关键关联/特殊注解/时间控制/分片键）已经显式列出，记为 K
2. 「其他字段」数 = 总字段数 - K，记为 R
3. 输出格式：「其他字段：R 个（逐一列出 R 个字段名，不写类型）」
4. **自验证**：输出前默数列举的字段名数量，必须精确等于 R；如不等，重新计算

例：总字段数 10，主键 1 个 + 分片键 1 个 + 关联字段 1 个 = 已显式列出 3 个，其他 = 10 - 3 = 7 个，
输出：「其他字段：7 个（businessNo / eventData / createTime / updateTime / operatorId / operatorName / tenantCode）」

**输出格式（每个实体一个子节）**：
```
#### {实体类名}（表名 | 分片表×N张 或 普通表 | 分片键：字段名）
- 总字段数：N 个；主键：{字段名}（IdType.AUTO / INPUT）
- 状态机：{字段名} — INIT(初始) / SUCCESS(成功) / FAIL(失败) ...
- 关键关联：{字段名} → {关联表名}（⚠️跨分片风险，如适用）
- 特殊注解：{字段名} — @TableField(typeHandler=XxxHandler.class)
- 逻辑删除：{字段名} / 无；乐观锁：{字段名} / 无
- 其他字段：N 个（字段名列举，不写类型）
```

继承关系：如多个实体继承同一基类，在本节**开头**一次性说明基类公共字段，后续实体不重复列出基类字段。
查询结果 DO（无 @TableName，非实体表）：单独放在本节末尾，只写用途和核心字段，不展开全部字段。

#### 2. 表与实体映射总表
汇总表格（每行一张表）：
| 实体类 | 表名 | 字段数 | 主键策略 | 逻辑删除 | 乐观锁 | 是否分片表 | 备注 |

如有旧文档，末尾附差异比对：只列出 ❌幽灵表 和 🆕新发现 条目；✅已验证的合并为一行统计（「旧文档声称 N 张，代码实际 M 张，其余 K 张均已验证」）。

#### 3. 查询模式矩阵
扫描必须全量（区域 B 每个 XML 和 .java 逐文件读取至 EOF），但**输出改为按场景聚合的矩阵，不按 Mapper 文件平铺**。

**3.1 写操作清单**（INSERT / UPDATE / DELETE）
| 操作类型 | 涉及表 | 触发场景（方法名缩写） | 批量/单条 | 风险标注 |

风险标注规则：跨分片表操作 → ⚠️跨分片；UPDATE/DELETE 无分片键 WHERE → 🔴全分片扫描；动态 IN 列表 → ⚠️IN列表。

**3.2 查询模式矩阵**（SELECT）
| 查询场景（方法名缩写） | 分片键是否在 WHERE | JOIN 表数 | 其他条件字段 | 分页 | 风险标注 |

风险标注规则：分片表查询无分片键 → 🔴全分片扫描；JOIN 分片表 → ⚠️跨分片JOIN；含子查询 → ⚠️子查询。

**3.3 BaseMapper 统一说明**
继承 BaseMapper<T> 的 Mapper 在此节开头统一说明：「以下 N 个 Mapper 均继承 BaseMapper，提供标准 CRUD（insert/selectById/updateById/deleteById/selectList）」，不逐个重复。

#### 4. 分库分表配置解析
- 找到 ShardingSphere 的分片配置（Java Config 或配置文件）
- 提取：
  a) 数据源配置（几个数据源、数据源命名）
  b) 分片表清单（哪些表做了分片）
  c) 分片算法（分片键、分片策略、分片数量）
  d) 广播表/默认数据源配置
- 如果未找到 ShardingSphere 配置，明确标注「依赖已引入但未找到分片配置」

#### 5. 数据源与连接配置
- 从配置文件中提取数据源配置（脱敏处理）：
  a) 数据源类型（HikariCP / Druid / 其他）
  b) 数据库名（schema）
  c) 连接池参数（最大连接数、最小空闲等）
  d) 是否多数据源
- 敏感信息（密码、连接地址的 IP/端口）用 [REDACTED] 替代

#### 6. TypeHandler 与类型映射
- 提取所有自定义 TypeHandler：
  a) Handler 类名
  b) 处理的 Java 类型 → 数据库类型映射
  c) 被哪些实体/字段使用

#### 7. 索引与查询模式分析
基于第 3 节查询模式矩阵，补充以下分析：
- 高频查询字段汇总（出现在 3 个以上查询的字段）
- 分片表的查询模式是否都包含分片键（无分片键的查询标注 🔴全分片扫描风险）
- 复合索引推断：列出代码期望存在的复合索引（基于多字段 WHERE 组合推断，不做「是否合理」评判）
- 注意：我们无法从代码中确认实际数据库索引，只能推断「代码期望有这些索引」

#### 8. 实体状态机还原
- 对有 status/state/isFinish 字段的实体，从枚举或常量中还原状态值（已在 §1 摘要中列出，此节补充状态流转方向）
- 从 Mapper 的 UPDATE 语句中推断状态流转（SET status=? WHERE status=? 模式）
- 如有旧文档，与旧文档声称的状态机交叉验证

[Action]
在 {{output_dir}} 目录下生成 04_Data_Model_and_Lifecycle.md

[Constraint - 工业级底线]

**输出格式锁定**：使用以下标题结构
```
### 1. 实体决策摘要
### 2. 表与实体映射总表
### 3. 查询模式矩阵
### 4. 分库分表配置解析
### 5. 数据源与连接配置
### 6. TypeHandler 与类型映射
### 7. 索引与查询模式分析
### 8. 实体状态机还原
### 9. 旧文档交叉验证摘要（有旧文档时输出，NO_DOCS 时跳过）
```

**第 9 节格式（有旧文档时）**：
只列出差异条目：❌幽灵表/接口 和 🆕新发现；✅已验证的合并为一行：「旧文档声称 N 条，其余均已代码验证」。

**工作区边界**：所有文件访问必须限定在当前工作区根目录下。若 `{{project_name}}-dao/` 在工作区内不存在，必须立即停止并输出：`❌ 未在工作区找到 [路径]，无法完成审计。请确认 PROJECT_NAME 与目标项目一致。` 禁止推断替代路径，禁止访问工作区外目录。

**扫描完整性保证**：
- 扫描必须全量：区域 A/B/C 每个文件逐一读取至 EOF，不允许跳过
- 输出必须提炼：扫描全量 ≠ 输出全量，输出按本文档的格式规则提炼

**专业性底线**：
- 字段类型写 Java 类型，不转述为自然语言
- SQL 操作直接标注 SELECT/INSERT/UPDATE/DELETE，不解释 SQL 含义
- 分片算法写具体实现类名或策略表达式，不做简化解释
- 状态值直接从代码中摘录，不做推测性补充
- 风险标注基于代码事实，不假设「可能存在但未看到的」保障
- **「其他字段：N 个」的 N 必须通过「总字段数 - 已显式列出字段数」精确计算，禁止估算；列举的字段名数量必须等于 N，不允许多写或少写**
- **总字段数必须通过数源码字段声明行精确统计，不允许从注释或文档推断**

**结尾标准审计闭环**：

> [!SUCCESS] 数据模型测绘闭环验证
> - 扫描范围：dao 模块 entity/ [N] 个实体类 + mapper/ [M] 个 XML + [P] 个配置文件
> - 提取结果：[X] 个实体、[Y] 张表、[W] 个 TypeHandler
> - 分库分表：[状态描述，与 Step 01 配置对比]
> - 表清单统计：代码实际 [N] 张（分片表 [M] 张，普通表 [K] 张）
> - 旧文档差异：❌幽灵表 [A] 张 / 🆕新发现 [B] 张 / ✅其余 [C] 张已验证（NO_DOCS 时标注 N/A）
> - EOF 状态：已确认遍历至最后一行，无静默截断

> [!RELAY] 定向审计约束
> - **物理事实 (Context)**: [本步发现的、对业务编排分析有决定性影响的数据事实，如：核心业务表的状态字段、关键的分片键、补偿表结构等]
> - **推演约束 (Constraint)**: [基于数据模型发现，强制 Step 05 重点关注的业务流转或状态机逻辑]
> - **物理锚点 (Anchors)**: [对应实体类文件路径及关键字段行号]
