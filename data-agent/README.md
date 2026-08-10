# Qpon 自主看数 / 数据分析 Agent

飞书对话驱动的只读 BigQuery 分析 Agent，部署在 Cloud Run。

## 能力

- 飞书机器人收消息 → Gemini 工具循环自主查表/写 SQL/解读结果
- 只读访问，dataset 白名单：`qpon_rpt_d` / `qpon_dws_d` / `qpon_dwd_d`
- 拦截 DML/DDL；扫描字节上限；结果行数上限
- 额外提供 `POST /v1/ask` 便于本地联调

## 架构

```
飞书事件 → Cloud Run /feishu/event → DataAgent(Gemini + BQ tools) → 飞书回复
```

## 本地运行

```bash
cd data-agent
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 GEMINI_API_KEY 等
# BQ：本机 gcloud auth application-default login，且账号对白名单 dataset 有 Data Viewer + Job User
uvicorn app.main:app --reload --port 8080
```

健康检查：`GET http://127.0.0.1:8080/healthz`

试问（需在 `.env` 设 `ENABLE_HTTP_ASK=true`，建议同时设 `ASK_API_KEY`）：

```bash
curl -X POST http://127.0.0.1:8080/v1/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ASK_API_KEY" \
  -d "{\"question\":\"昨天 qpon_rpt_d 业务指标表 GTV 大概多少？\"}"
```

Cloud Run 默认 `ENABLE_HTTP_ASK=false`，生产入口只有飞书事件。部署使用 `--no-cpu-throttling`，保证异步回复有 CPU。
单测（不连 BQ）：

```bash
pip install pytest
pytest -q
```

## Cloud Run 部署

### 1. 服务账号与 IAM（最小权限）

建议 SA：`qpon-data-agent@$PROJECT.iam.gserviceaccount.com`

| 角色 | 范围 |
|---|---|
| `roles/bigquery.jobUser` | 项目级 |
| `roles/bigquery.dataViewer` | 仅 `qpon_rpt_d` / `qpon_dws_d` / `qpon_dwd_d` 三个 dataset |
| `roles/secretmanager.secretAccessor` | 本服务用到的 Secret |
| `roles/run.invoker` | 若关闭公开访问，再给飞书回调所用的调用方 |

示例（dataset 级 Data Viewer）：

```bash
for DS in qpon_rpt_d qpon_dws_d qpon_dwd_d; do
  bq add-iam-policy-binding \
    --member="serviceAccount:qpon-data-agent@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    "${PROJECT_ID}:${DS}"
done
```

### 2. Secret Manager

创建并写入（名称需与 `deploy.sh` 一致，或改脚本）：

- `gemini-api-key`
- `feishu-app-id`
- `feishu-app-secret`
- `feishu-verification-token`
- `feishu-encrypt-key`

### 3. 构建并发布

```bash
chmod +x deploy.sh
# 按需改 PROJECT_ID / REGION / IMAGE_REPO / SA_EMAIL
./deploy.sh
```

记下输出的 Cloud Run URL。

### 4. 飞书应用配置

1. 开放平台创建企业自建应用
2. 权限：`im:message`、`im:message.group_at_msg`（按实际权限名勾选收发消息）
3. 事件订阅：请求地址 `https://<Cloud-Run-URL>/feishu/event`
   - 订阅 `im.message.receive_v1`
   - 填写 Verification Token / Encrypt Key（与 Secret 一致）
4. 发布应用，将机器人拉进群；群聊需 @机器人，单聊可直接提问

## 环境变量

见 `.env.example`。关键项：

| 变量 | 含义 |
|---|---|
| `BQ_ALLOWED_DATASETS` | 白名单，逗号分隔 |
| `BQ_MAX_BYTES_BILLED` | 单次查询最大计费字节 |
| `BQ_MAX_ROWS` | 返回行上限 |
| `FEISHU_ALLOWLIST_OPEN_IDS` | 可选，限制可提问用户 |

## 安全说明

- 应用层强制只读 + dataset 白名单；IAM 再收一层
- 密钥全部走环境变量 / Secret Manager，**不要**写进仓库
- 飞书回调若需内网可达：用公司合规入口或 Cloud Run 鉴权方案，**禁止**内网穿透到公网个人隧道
- 仓内其它 DAG 中的硬编码飞书密钥不得复用到本服务

## 目录

```
data-agent/
  app/
    main.py           # FastAPI
    config.py
    agent/loop.py     # Gemini 工具循环
    tools/bq.py       # BQ 只读工具
    tools/catalog.py  # 领域表提示
    feishu/           # 加解密 + Open API
  Dockerfile
  deploy.sh
  requirements.txt
  tests/
```
