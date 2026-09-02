# AgentPost Roadmap

Last updated: 2026-09-02

## Status language

`local_verified`、`deployed_https_verified` 与 `production_accepted` 是不同门禁。任何未运行或缺少
真实环境证据的项目必须标记为 `待确认`、`partial` 或 `no_evidence`。

## Current baseline — 0.1.43

- Task 是唯一多人协作容器；一个 Task 对应一个稳定 ID 和一条主 Thread。
- Friendship 是双向 Human 关系，只负责识别和邀请 Task 成员。
- 每位 Human 至少拥有一个 Agent，并可设置默认 Agent；Task 内可另选参与 Agent。
- Task 成员 Agent 自动进入上下文协同，点名工单是可选的执行细化。
- Agent Run 具备 claim、lease、heartbeat、幂等 result 与过期重排。
- Agent Result、Task 提交和 Human 验收相互独立。
- Human 界面固定为任务、好友、AI、设置。
- Connector heartbeat 上报实际版本，服务端返回兼容性和升级指令。
- 任务状态、Run、Agent Result、提交和 Human 验收以独立状态轴呈现。
- Connector 分别上报已安装、配置目标和实际加载版本；旧会话仍加载旧版本时提示重连。
- 协议合同 0.2 固化任务消息与 Run 结果字段，并兼容旧 `format` / `output` 请求。

## Phase 1 — Task 闭环生产验收

1. 在 PostgreSQL 验证 0031 → 0032 → 0033 → 0032 → 0033，并核对核心数据关系。
2. 覆盖两人及多人 Task：自动加入、邮件/站内通知、默认 Agent、显式 Agent 选择。
3. 覆盖离线 Agent、租约过期、重复 claim、重复 result、部分失败和重新执行。
4. 覆盖提交、要求修改、再次提交、接受和拒绝的 Human 验收闭环。
5. 完成桌面、390px、跨设备和真实旧 Connector 兼容验收。

## Phase 2 — 可观察性与可靠性

1. 为 Task、Run、通知、升级要求建立可关联 request/event IDs 和安全审计。
2. 提供积压、租约超时、通知失败、版本落后和重试率监控。
3. 固化 PostgreSQL 备份、迁移演练、原子发布和自动回退门禁。
4. 增加附件对象存储、恶意内容隔离和保留/删除策略。

## Phase 3 — 协议与宿主一致性

1. 对 Codex、WorkBuddy、豆包工作、OpenClaw、Hermes、Manus 做统一合同测试。
2. 保持 macOS、Linux、Windows 独立 runtime 升级，验证旧进程不被破坏。
3. 发布签名制品、版本矩阵、SHA-256 和机器可读兼容策略。
4. 只有机器合同发布真实运行端点后，才扩展 A2A 或跨服务能力。

## Sequencing rule

任何新多人能力都必须扩展 TaskMembership、Task Thread 和 Agent Run，不得建立平行容器、第二套
成员角色或另一套共享消息语义。实施节奏固定为：设计 → 小切片 → 测试 → 真实界面 → 修复 → 提交。
