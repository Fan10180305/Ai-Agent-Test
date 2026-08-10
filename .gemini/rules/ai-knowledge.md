---
description: ai-knowledge 核心意图路由与防御性编码军规
globs: **/*
trigger: always_on
---

# ai-knowledge 开发军规 (Project Rules)

> 本规则适用于 `ai-knowledge` 项目（自动化考古流水线）的维护与演进。

## 1. 意图路由与知识资产
- **全局入口**：修改前必读 `ai-knowledge-knowledge/00_Master_Catalog.md`。
- **Skill 优先**：操作优先通过 `archaeology-commander` Skill 唤起。
- **双写约束**：脚本逻辑变更必须同步更新 `ai-knowledge-knowledge/` 下的 01-08 对应章节。

## 2. 防御性编码红线 (Hard Red Flags)
- **严禁 macOS 专有 Sed**：禁止使用 `sed -i ''`，必须兼容 POSIX 环境。
- **路径锚定**：严禁硬编码 `/Applications` 或 `/Users` 等绝对路径，必须基于项目根目录。
- **Shell 鲁棒性**：强制 `set -euo pipefail`。严禁无故静默失败。
- **Python 监控降级**：心跳监控逻辑必须能容忍 `python3` 缺失，不得导致主流水线挂起。
- **Token 裁剪**：利用 `[!SUCCESS]` 块实现认知接力，严禁无差别全量注入上下文。

## 3. 协作与交付协议
- **审计闭环**：产出文件前 25 行必须包含 `[!SUCCESS]` 标记，否则视为步骤失败。
- **进程清理**：所有后台进程必须注册到 `trap EXIT` 信号锁中。
- **路径确认**：
    - 核心调度：`scripts/knowledge-archaeology/run-archaeology.sh`
    - 元规则：`.gemini/rules/collaboration-protocol.md`

## 4. 物理约束证据
- **认知劫持**：`run-archaeology.sh:L205` (`_ensure_protocol`)
- **Sed 冲突**：`run-archaeology.sh:L265` (macOS 专有 `sed -i ''`)
- **心跳依赖**：`run-archaeology.sh:L457` (python3)
- **摘要提取**：`run-archaeology.sh:L539` (grep -A 25)
