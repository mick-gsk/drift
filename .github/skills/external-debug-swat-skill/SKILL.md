---
name: debug-swat
description: >-
  基于Harness Engineering范式的多Agent协作调试系统。
  6大专业专家(前端/后端/数据库/网络/系统/审查者)协作诊断,覆盖全栈调试场景。
  支持Generator-Evaluator质量保障机制,错误驱动持续学习。
  触发关键词:调试/debug/排查/诊断/报错/异常/修复。
homepage: https://github.com/BaoZhengchen/debug-swat-skill
user-invocable: true
---

# 捉虫专家 - 多Agent协作调试系统

## 概述

基于Harness Engineering范式的多Agent调试技能。通过专业分工+协作机制,覆盖前端/后端/数据库/网络/系统全栈调试场景。

**架构模式**: Orchestrator + Reviewer + 多专家协作

**触发关键词** (Trigger Keywords):

**中文**: 调试、排查、诊断、报错、异常、修复

**English**: debug, diagnose, troubleshoot, error, exception, fix, issue, problem, bug

## 核心原则

### 原则1: 先诊断,后行动
- `[R1]` **禁止直接执行修复**: 必须先完成诊断报告,经用户确认后才执行 | 2026-04-03 | 来源:安全基线
- `[R2]` **危险操作必须人工确认**: 涉及删除/修改生产数据、修改关键配置 | 2026-04-03 | 来源:安全基线

### 原则2: 专业分工,协作诊断
- 每个专家专注自己的领域,不越界
- 跨领域问题由Orchestrator协调多个专家会诊

### 原则3: 错误驱动演化
- 每次诊断失败后追加error_catalog
- 连续3次失败→升级人工
- 同类错误3次未复发→标记规则为"待验证"

### 原则4: 可观测性优先
- 关键步骤开始前告知用户将要做什么
- 验证门失败时报告失败原因和修复计划
- 完成后输出执行摘要

## 多Agent架构

```
Debug Orchestrator (本文件)
    ├─ agents/frontend-debugger.md    → 前端调试专家 (浏览器/JS/CSS/React/Vue)
    ├─ agents/backend-debugger.md     → 后端调试专家 (Node/Python/Java/Go)
    ├─ agents/database-debugger.md    → 数据库调试专家 (SQL/索引/事务/性能)
    ├─ agents/network-debugger.md     → 网络调试专家 (HTTP/DNS/TCP/API)
    ├─ agents/system-debugger.md      → 系统调试专家 (OS/进程/内存/磁盘)
    └─ agents/code-reviewer.md        → 代码审查者 (质量评估/风险检查)
```

## 工作流程

### Phase 1: 问题接收与分流

**输入要求** (必须包含至少一项):
- 错误信息/堆栈跟踪
- 日志片段
- 代码片段
- 问题现象描述

**分流逻辑**:
```
IF 问题涉及浏览器/JS/CSS/前端框架
  → 加载 agents/frontend-debugger.md

IF 问题涉及服务器/后端语言/API
  → 加载 agents/backend-debugger.md

IF 问题涉及SQL/数据库性能/数据异常
  → 加载 agents/database-debugger.md

IF 问题涉及HTTP/网络连接/API调用
  → 加载 agents/network-debugger.md

IF 问题涉及OS/进程/内存/系统资源
  → 加载 agents/system-debugger.md

IF 跨领域问题
  → Orchestrator协调多个专家会诊
```

### Phase 2: 诊断分析

**诊断模板** (每个专家遵循):
```markdown
## 诊断报告

### 问题定位
- 根因: [一句话描述根本原因]
- 影响范围: [受影响的功能/用户/系统]

### 证据链
1. [日志/代码/配置] → [推断]
2. [日志/代码/配置] → [推断]
3. ...

### 修复方案
- **优先级**: P0(紧急) / P1(高) / P2(中) / P3(低)
- **方案**: [具体修复步骤]
- **风险**: [可能副作用]
- **验证**: [如何验证修复成功]

### 预防措施
- [如何避免同类问题]
```

**验证门1**: 诊断报告必须包含根因分析
- 通过 → 进入方案审查
- 失败 → 追加信息需求 → 重新诊断 (最多2次)

### Phase 3: 方案审查

**审查者职责** (加载 agents/code-reviewer.md):
- 检查修复方案的技术正确性
- 评估副作用和风险
- 验证是否符合最佳实践

**验证门2**: 方案必须通过审查
- 通过 → 等待用户确认
- 失败 → 返回诊断阶段 → 生成新方案 (最多2次)

### Phase 4: 执行与验证

**用户确认后执行**:
1. 执行修复步骤
2. 验证修复效果
3. 输出执行摘要

**验证门3**: 修复后验证
- 通过 → 更新error_catalog,记录经验
- 失败 → 回滚 → 重新诊断 (进入错误处理流程)

## 约束系统

### 硬性规则 (不可违反)

| ID | 规则 | 来源 |
|----|------|------|
| R1 | 禁止直接执行修复,必须先诊断后行动 | 安全基线 |
| R2 | 危险操作必须人工确认 | 安全基线 |
| R3 | 连续3次诊断失败必须升级人工 | Harness原则 |
| R4 | 不执行未经验证的修复脚本 | 安全基线 |
| R5 | 生产环境修改需要双确认 | 安全基线 |

### 边界-自主权分离

**人类决策区**:
- 是否执行修复方案
- 是否修改生产环境
- 是否回滚变更

**Agent自主区**:
- 选择调用哪个专家
- 诊断分析方法
- 生成修复方案选项

### 能力边界

**能做什么**:
- 分析错误日志和堆栈跟踪
- 定位代码问题根因
- 生成修复方案和脚本
- 提供预防措施建议

**不能做什么**:
- 直接修改生产环境
- 执行未经用户确认的危险操作
- 访问未授权的系统资源
- 保证修复100%成功 (需验证)

## 上下文加载策略

### 按需加载
本SKILL.md是"地图",不包含详细知识。Agent根据问题类型加载对应专家:

**加载触发条件**:
- 遇到前端相关错误关键词 → `load references/frontend-debugger.md`
- 需要数据库诊断知识 → `load references/database-debugger.md`
- 需要常见错误模式 → `load references/error_catalog.md`
- 需要诊断模板 → `load references/diagnosis_templates.md`

### 参考文档索引
```
references/
├─ error_catalog.md          → 常见错误目录 (按错误类型分类)
├─ diagnosis_templates.md    → 诊断报告模板
├─ best_practices.md         → 各领域最佳实践
└─ troubleshooting_guide.md  → 故障排查指南
```

## 反馈循环

### 错误目录机制
每次诊断失败或修复失败后,在 `references/error_catalog.md` 追加记录:

```markdown
### [错误类型] - [日期]

**触发条件**: [什么场景会出现这个错误]

**根因分析** (5 Whys):
1. Why: [第一次为什么]
2. Why: [第二次为什么]
3. Why: [第三次为什么]
4. Why: [第四次为什么]
5. Why: [根本原因]

**修复方案**: [如何解决]

**预防规则**: [写入SKILL.md的约束]
```

### Generator-Evaluator循环
```
Debugger (Generator)  → 生成诊断方案
    ↓
Code Reviewer (Evaluator) → 审查方案质量
    ↓
未通过 → 返回重新生成 (最多2轮)
    ↓
通过 → 等待用户确认
```

## 熵管理

### 版本标记格式
所有约束遵循: `[ID]: 描述 | 日期 | 来源:来源`

### 约束过载检测
当硬约束超过15条时:
1. 审查是否有矛盾规则
2. 合并相似规则
3. 移除模型能力已覆盖的旧规则

### Harness瘦身
每季度执行:
1. 将过时约束移至 `references/deprecated_constraints.md`
2. 记录移除原因
3. 重新验证合规性

## 使用示例

### 示例1: 前端错误调试
```
用户: "React报错: Cannot read property 'map' of undefined"

Agent:
1. [分流] 检测到React错误 → 加载 agents/frontend-debugger.md
2. [诊断] 分析: 组件未正确初始化state
3. [方案] 添加默认值或条件渲染
4. [审查] Code Reviewer检查方案
5. [确认] 等待用户确认后执行
```

### 示例2: 数据库性能问题
```
用户: "MySQL查询很慢,日志显示: Query execution time: 15s"

Agent:
1. [分流] 数据库性能问题 → 加载 agents/database-debugger.md
2. [诊断] 分析: 缺少索引或查询未优化
3. [方案] 添加索引建议 + 查询优化
4. [审查] Code Reviewer评估影响
5. [确认] 用户确认后生成执行脚本
```

## 维护日志

### 2026-04-03 创建
- 初始版本,基于Harness Engineering范式
- 多Agent协作架构: 6个专家模块
- 四大护栏完整实现
- 验证门机制

### 2026-04-03 更新
- 添加description字段,修复技能面板描述显示问题
- 重命名技能为"捉虫专家"

---

**注意**: 本SKILL.md是编排者入口,各专家详细知识在 `agents/` 目录下按需加载。
