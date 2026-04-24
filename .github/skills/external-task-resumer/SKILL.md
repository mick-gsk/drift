---
name: task-resumer
description: |
  解决 OpenClaw/QClaw 复杂任务因步骤过多导致 Agent 自动中止的问题。

  核心能力：
  1. 任务复杂度分析 - 自动识别需要拆分的长流程任务
  2. 智能任务拆分 - 将大任务分解为可独立执行的子任务
  3. 子代理委派 - 使用 sessions_spawn 将子任务派给独立会话执行
  4. 进度追踪与恢复 - 维护任务状态，支持断点续作

  使用场景：
  - 涉及"多个文件"、"批量"、"重构"、"完整实现"的复杂任务
  - 当前会话步骤数 >10 需要预防性拆分
  - 用户说"继续上次的任务"或"恢复之前的任务"
  - 多阶段任务（分析→设计→实现→测试）需要分步执行

  触发关键词：继续、恢复、拆分、子任务、太长、步骤太多、批量、重构、多文件
license: MIT
---

# Task Resumer — 任务恢复与拆分技能

## 核心原则

**预防优于恢复**：在任务变得过于复杂之前主动拆分，避免 Agent 中止。
**子代理隔离**：使用 `sessions_spawn` 将子任务派给独立会话，隔离上下文消耗。
**状态持久化**：所有任务状态保存在 `.qclaw/tasks/` 目录，支持跨会话恢复。

---

## 快速决策流程

当收到用户请求时，按以下流程判断如何处理：

```
用户请求
    │
    ▼
是否有未完成的 tracked task？ ──是──→ 【恢复模式】加载并继续
    │否
    ▼
任务复杂度是否 > 阈值？ ────────是──→ 【拆分模式】分析并拆分任务
    │否                               (多文件/批量/重构/完整实现)
    ▼
【正常模式】直接执行
```

### 复杂度判断标准

| 指标 | 阈值 | 说明 |
|------|------|------|
| 涉及文件数 | >3 个 | 需要修改或创建多个文件 |
| 任务阶段数 | >2 个 | 明显的多阶段（如分析→设计→实现） |
| 操作类型 | 批量 | "批量处理"、"全部重构"等 |
| 当前步骤数 | >10 | 当前会话已执行较多步骤 |

---

## 三种工作模式

### 模式一：正常模式（简单任务）

**触发条件**：任务简单，不涉及上述复杂度指标。

**处理方式**：直接执行，不经过本技能。

---

### 模式二：拆分模式（预防性拆分）

**触发条件**：
- 用户请求涉及多个文件、批量操作、完整重构
- 或当前会话步骤数 >10

**执行步骤**：

1. **分析任务复杂度**
   ```bash
   python "{SKILL_DIR}/scripts/task_analyzer.py" --task "<任务描述>"
   ```
   返回：复杂度评分(1-10)、建议拆分策略、预估子任务数

2. **生成任务清单**
   ```bash
   python "{SKILL_DIR}/scripts/task_splitter.py" --task "<任务描述>" --output ".qclaw/tasks/current_manifest.json"
   ```
   生成任务清单文件，包含：
   - 主任务描述
   - 子任务列表（id, description, dependencies, status）
   - 执行顺序（拓扑排序后的依赖关系）

3. **执行子任务（串行或并行）**

   **串行执行**（有依赖关系）：
   ```python
   # 读取 manifest，找到下一个待执行的子任务
   # 使用 sessions_spawn 派发给子代理
   sessions_spawn(
       task=subtask_description,
       runtime="subagent",
       mode="run",
       label=f"task-{subtask_id}"
   )
   # 等待完成后更新 manifest 状态，继续下一个
   ```

   **并行执行**（无依赖关系）：
   ```python
   # 批量派发多个无依赖的子任务
   for subtask in ready_subtasks:
       sessions_spawn(...)
   # 等待全部完成后继续
   ```

4. **汇总结果**
   - 收集所有子任务输出
   - 向用户呈现完整结果
   - 清理或归档任务清单

---

### 模式三：恢复模式（断点续作）

**触发条件**：
- 用户说"继续上次的任务"、"恢复之前的任务"
- 或检测到 `.qclaw/tasks/` 有未完成的 tracked task

**执行步骤**：

1. **扫描未完成任务**
   ```bash
   python "{SKILL_DIR}/scripts/progress_tracker.py" --list
   ```
   返回：所有未完成任务列表（id, description, progress, last_updated）

2. **加载指定任务**
   ```bash
   python "{SKILL_DIR}/scripts/progress_tracker.py" --load <task_id>
   ```
   返回：任务清单内容、当前执行位置、已完成子任务、待办子任务

3. **继续执行**
   - 从上次中断的子任务开始
   - 使用 sessions_spawn 继续委派
   - 更新进度状态

4. **完成或再次中断**
   - 全部完成：归档任务，向用户汇报
   - 再次中断：保留状态，告知用户可随时恢复

---

## 任务清单格式 (manifest.json)

```json
{
  "task_id": "uuid",
  "created_at": "2026-04-21T01:30:00Z",
  "updated_at": "2026-04-21T02:15:00Z",
  "original_request": "用户原始请求",
  "status": "in_progress|completed|failed|paused",
  "subtasks": [
    {
      "id": "st-001",
      "description": "子任务描述",
      "status": "completed|in_progress|pending|failed",
      "dependencies": [],
      "output": "执行结果摘要",
      "session_key": "子代理会话key（如适用）"
    }
  ],
  "current_index": 1,
  "metadata": {
    "total_subtasks": 5,
    "completed_count": 1,
    "failed_count": 0
  }
}
```

---

## 脚本使用参考

### task_analyzer.py — 任务复杂度分析

```bash
python "{SKILL_DIR}/scripts/task_analyzer.py" --task "<任务描述>" [--verbose]
```

**输出**：
```json
{
  "complexity_score": 7,
  "should_split": true,
  "reason": "涉及5个文件的修改，建议拆分",
  "suggested_strategy": "按文件拆分",
  "estimated_subtasks": 5
}
```

### task_splitter.py — 任务拆分

```bash
python "{SKILL_DIR}/scripts/task_splitter.py"
  --task "<任务描述>"
  --output ".qclaw/tasks/<task_id>/manifest.json"
  [--strategy auto|by_file|by_phase|by_module]
```

**拆分策略**：
- `auto`：自动选择最佳策略（默认）
- `by_file`：按文件拆分（适合多文件修改）
- `by_phase`：按阶段拆分（适合分析→设计→实现）
- `by_module`：按模块拆分（适合系统级重构）

### progress_tracker.py — 进度追踪

```bash
# 列出所有任务
python "{SKILL_DIR}/scripts/progress_tracker.py" --list [--status all|in_progress|completed]

# 加载指定任务
python "{SKILL_DIR}/scripts/progress_tracker.py" --load <task_id>

# 更新子任务状态
python "{SKILL_DIR}/scripts/progress_tracker.py" --update <task_id> --subtask <st-id> --status completed

# 归档已完成任务
python "{SKILL_DIR}/scripts/progress_tracker.py" --archive <task_id>
```

---

## 典型使用场景示例

### 场景1：多文件代码重构

**用户请求**："帮我重构这个项目的所有 API 接口，统一错误处理格式"

**处理流程**：
1. 检测到涉及"所有 API 接口" → 复杂度指标触发
2. 运行 task_analyzer → 建议按文件拆分
3. 运行 task_splitter → 生成每个 API 文件的修改任务
4. 使用 sessions_spawn 逐个执行（或批量并行）
5. 汇总所有修改结果

### 场景2：长流程任务中途恢复

**用户请求**："继续上次的任务"

**处理流程**：
1. 运行 progress_tracker --list → 发现未完成任务
2. 加载任务清单 → 定位到上次中断的子任务
3. 继续执行剩余子任务
4. 完成后归档

### 场景3：预防性拆分（当前会话步骤过多）

**上下文**：当前会话已执行 12 个步骤，用户继续提出复杂请求

**处理流程**：
1. 检测到当前步骤数 >10
2. 主动建议："这个任务较复杂，建议拆分为子任务执行，避免中断。是否继续？"
3. 用户确认后进入拆分模式

---

## 注意事项

1. **任务 ID 生成**：使用 UUID 或时间戳+描述摘要，确保唯一性
2. **子任务粒度**：每个子任务应能在 5-10 个步骤内完成
3. **依赖管理**：严格处理子任务间的依赖关系，避免执行顺序错误
4. **错误处理**：子任务失败时，记录错误信息，提供重试或跳过选项
5. **清理策略**：已完成任务可归档到 `.qclaw/tasks/archived/`，保留 30 天后自动清理

---

## 进阶：自定义拆分策略

如需针对特定领域定制拆分逻辑，参考 [references/custom_splitters.md](references/custom_splitters.md)。
