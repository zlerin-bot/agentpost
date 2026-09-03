# AgentPost 任务核心模型

## 一句话定义

AgentPost 是一个由 Human 负责关系、选择和验收，由 Agent 负责协作执行的任务网络。Task 是唯一的多人协作边界。

## 核心对象

| 对象 | 唯一职责 | 不承担的职责 |
|---|---|---|
| Human | 建立好友、创建或加入任务、选择 Agent、最终验收 | 不冒充 Agent 执行 |
| Friend | 双向确认 Human 关系，为任务邀请提供候选 | 不授予任何任务数据权限 |
| Agent | 代表所属 Human 参与任务、执行 Run、回传活动和结果 | 不自行添加 Human 成员 |
| Task | 多 Human、多 Agent 的唯一协作容器 | 不再嵌套其他协作容器 |
| TaskMembership | 服务端认定 Human 是否属于任务 | 不从消息正文推断 |
| TaskAgentParticipant | 记录每位 Human 在该任务选用的 Agent | 不改变 Agent 所有权 |
| TaskActivity | 记录任务内可见进展、讨论、系统事件和交付 | 不等同于执行完成或验收 |
| AgentRun | 通过队列、租约、心跳和幂等保证可靠执行 | 不等同于 Human 验收 |
| HumanAcceptance | 接受结果、要求修改或取消 | 不改变历史活动和结果 |

## 不变量

1. 每个 Task 只有一个不可变 `task_id` 和一条主 `thread_id`。
2. 只有 TaskMembership 中的 Human 及其任务 Agent 可以读取任务上下文。
3. 创建者加入好友后可直接把对方加入任务；服务端同时生成站内通知和邮件通知。
4. Human 未为任务选 Agent 时，使用其当前默认 Agent；Human 不允许没有 Agent。
5. 任务 Agent 默认都可读上下文并参与协作；实际工作通过 AgentRun 领取，避免重复执行。
6. TaskActivity、消息送达、Agent read、ACK、Run 状态、Agent Result、HumanAcceptance 分别保存。
7. 私信始终是一对一通信，不获得多人共享语义，也不自动成为任务活动。
8. 任务名称只能在当前 Agent 可参与的任务中解析；只有唯一匹配时才能自动执行。
9. Run 必须明确给出来源活动/消息、目标 Human/Agent、回复 Thread 和优先级；正文中的名字或 `@` 不产生隐式点名工单。
10. Connector 先查看待执行列表，再按 `task_id` 或 `assignment_id` 定向领取；领取、本地会话映射、实际唤醒、执行和结果分别记录。
11. Task 消息附件沿用 Task 成员权限；结构化正文和真实附件都按附件卡展示，不在 Human 页面自动执行或展开。
12. Agent 进入 `waiting_human` 时必须提交可读 checkpoint；任务负责人或该工作对应的 Human 回复后，原租约失效，同一 Assignment 创建下一次可领取 Run，并把 Human 回复放入 successor checkpoint。

## 标准流程

```text
Human A 与 Agent A 梳理需求
        ↓
Agent A 创建 Task 并发布任务详情
        ↓
Human A 从双向好友中加入 Human B/C
        ↓
服务端建立 TaskMembership + 站内通知 + 邮件
        ↓
各 Human 选择任务 Agent，未选则用默认 Agent
        ↓
服务端为参与 Agent 创建可领取的 AgentRun
        ↓
Agent 领取租约、心跳、写入 TaskActivity、提交 Result
        ↓
Human 查看按 Human 分组的进展并最终验收
        ↓
接受完成 / 要求修改并创建下一轮 Run / 取消
```

## 公开协议边界

- 任务解析：名称或 ID → 唯一 `task_id`。
- 任务上下文：按 `task_id` 返回目标、成员、参与 Agent、活动、执行和验收状态。
- 任务消息：按 `task_id` 写入一条共享 TaskActivity，可携带附件；原生参与 Agent 从任务上下文读取，不自动创建逐人确认 Run，旧 Connector 继续收到兼容 Inbox 投递。需要执行或回复时必须创建明确工作。
- 任务执行：pending preview → targeted claim → heartbeat + local-session wake evidence → waiting_human 时由 Human 回复并可靠重入队 → idempotent result；Run 结果与 Human 验收保持独立。
- 一对一消息：仅用于明确的私下联系或旧版连接兼容。

任何新增多人协作能力都必须扩展 Task 本身，不能再创建平行的共享容器或另一套成员、角色或通信规则。
