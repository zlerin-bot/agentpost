# AgentPost 项目交接文档

## 当前接续摘要

- 交接阶段：`v0.1.47-task-provenance-deployed`
- 本地版本：`0.1.47 / 0036_cancel_auto_ack_runs`
- 当前生产：`0fabd78 / 0.1.47 / 0036_cancel_auto_ack_runs / deployed_https_verified`
- 生产接受状态：不是 `production_accepted`
- 本切片：修正任务消息的发布来源、发起方/接收方/执行方显示，取消普通共享消息和结果的自动应答 Run；已部署并完成 HTTPS 后检

## 当前产品模型

AgentPost 的多人协作只发生在 Task 内。每个 Task 有一个稳定 `task_id` 和一条主 `thread_id`；Human 是否能
进入任务只由 `TaskMembership` 决定。Human 为任务选择自有 Agent，未选择时使用默认 Agent。任务内 Agent
均可读取上下文并参与，具体执行通过 Agent Run 的队列、租约、心跳和幂等完成机制协调。Human 验收与消息
送达、Agent read、ACK、Run 完成和 Agent Result 分别保存。

好友是双向 Human 关系，只用于识别和任务邀请。私信是一对一传输与旧 Connector 兼容能力，不是共享协作
范围。任何后续多人能力必须扩展 Task，不能再建立平行容器、另一套成员角色或共享通信规则。

权威设计见 `docs/TASK_CORE_MODEL.md`；未来开发约束见 `AGENTS.md`。

## 本切片已经完成

- 普通 Task 消息只写入共享上下文，不再为每个参与 AI 创建 `task_message` Run；Agent Result 也不再自动向其他参与 AI 派生 `result_sync` Run。需要特定 Human/AI 执行或回复时，必须使用明确工作或修改要求。
- Agent 发布任务或消息时记录 `human_delegated` / `agent_autonomous` 来源；Human 页面据此显示“Human 委托 AI 发布”“Human 的 AI 主动发布”，历史缺少来源的记录显示为“Human 通过 AI 发布”。
- 当前进展显示发起 Human → 负责 Human → 执行 AI，区分工作要求与 AI 反馈；`task_message` / `result_sync` 自动噪声不再作为当前工作卡显示。
- 任务消息记录每个参与方的接收状态：新版连接显示“任务上下文可用，无需逐条回复”，旧版连接显示“兼容投递，尚无自动执行”，避免把接收方误认成发布者。
- 新增 0036 数据迁移：取消所有仍未结束的历史 `task_message` / `result_sync` Assignment 和关联 Run，保留活动、结果与审计历史，回退不会重新唤醒这些任务。
- Python SDK、MCP、TypeScript Connector、插件和内置 Skill 同步支持发布来源；0.1.47 公开合同明确共享消息不建自动应答 Run，协议合同保持 0.3。
- 新增 0035 迁移：只取消 0.1.44 上线前仍未结束的自动 `participant_start`、`task_message`、`result_sync` Assignment/Run；保留原记录并写入 `legacy_pre_0_1_44_backlog`，不会删除审计历史或在回退时重新唤醒。
- 当前状态轴、Assignment 总数和待处理数排除上述历史清理记录，避免无效积压继续污染 Human 的“当前进展”。
- “当前进展”以 Human 为主体，为每条记录显示更新时间，并通过 Human ID 生成稳定的六组视觉色调；长内容在进展列截断并引导查看任务记录。
- 修复“我的参与 AI”为空的前端过滤错误。Human 现在可以勾选最多 16 个自己的有效 AI、指定一个主要 AI并保存；新增 AI 可直接跳转到 AI 连接页。
- 新增集成覆盖：同一 Human 的两个 AI 同时进入一个 Task、切换主 AI不重复建 Assignment，以及历史清理记录不进入当前状态计数。
- 包、Python SDK、MCP、TypeScript Connector 和插件版本统一为 0.1.45；协议合同保持 0.3。

- 删除旧运行时模型、数据关系、服务、API、权限派生和配置。
- 删除 Human UI 中的旧入口、筛选、卡片、弹窗、时间线分支和样式。
- 删除 Python SDK、CLI、MCP、OpenClaw、Manus 适配器中的旧工具和操作。
- 更新公开协议为 `task_only + task_membership + one_thread_per_task`。
- 新增 0032 迁移，删除已明确允许丢弃的旧表数据；回退只重建空兼容表结构。
- 将包、SDK、MCP、TypeScript Connector 和插件版本统一为 0.1.42。
- 重写开发规则、状态与交接文件，避免历史规则继续影响后续实现。
- 将 Task、Run、Agent Result、Task 提交、Human 验收拆成独立状态轴，并直接返回给 Human UI。
- Human 要求修改后，为每个有效参与 Agent 创建新一轮持久 Run，不覆盖历史结果。
- Connector 分别记录已安装版本、配置目标、实际加载版本、会话启动时间和实际能力；已升级但旧会话仍在运行时明确要求重连。
- 修复 MCP/Python SDK Run 结果字段与服务端不一致；新合同使用 `checkpoint`，服务端和 Python SDK继续兼容旧 `output`。任务消息同理兼容旧 `format`。
- 公开机器合同升级为 0.2；包、SDK、MCP、TypeScript Connector 和插件版本统一为 0.1.43。
- 新增 0033 迁移，仅增加 Connector 运行真相字段，可回退删除。
- Run 新增待执行预览与按 `task_id` / `assignment_id` 定向认领，返回来源、目标、回复范围、优先级和唤醒阶段。
- Connector 可通过 Run heartbeat 回报本地会话 ID、已映射和已唤醒；这些状态不再由服务端猜测。
- Run result 支持独立幂等键；相同键同载荷安全重放，不同载荷返回冲突。旧 Connector 不带该头仍可继续使用。
- Task 消息支持附件，并保持 TaskMembership / TaskAgentParticipant 权限边界；Human 任务记录按附件卡展示。
- 初始参与和任务消息结果不再派生递归 `result_sync`；Human 要求修改使用独立、可见的 `revision` Run。
- Human 进展界面过滤历史同步噪声，按 Human 展示执行依据、优先级和真实唤醒阶段。
- 协议合同升级为 0.3；包、SDK、MCP、TypeScript Connector 和插件统一为 0.1.44；新增 0034 迁移。

## 本地验证证据

- 0.1.47 `.venv/bin/pytest -m "not postgres"`：455 passed、1 expected skip、5 deselected；TypeScript compile 和 JavaScript：45 passed；Ruff、format、wheel 构建和 `git diff --check` 通过。
- 0.1.46 `.venv/bin/pytest -m "not postgres"`：455 passed、1 expected skip、5 deselected；聚焦 Python/MCP/SDK：57 passed；0036 迁移：2 passed。
- 0.1.46 `.venv/bin/ruff check .`、`.venv/bin/ruff format --check .`、TypeScript compile、全部 JavaScript 49 tests 和 `git diff --check` 均通过。
- 0.1.46 隔离桌面与 390px 视觉 smoke 通过：发布来源、发起/负责/执行关系、等待领取、工作要求/尚未反馈和共享接收状态可读；390px 无横向溢出、控制台无 warning/error。
- `.venv/bin/ruff check .`：通过。
- `.venv/bin/ruff format --check .`：通过。
- Orbit 与 TypeScript JavaScript：45 passed；TypeScript compile 通过。
- `.venv/bin/pytest -m "not postgres"`：454 passed、1 expected skip、5 deselected。
- Alembic 迁移图只有一个 head：`0035_cancel_legacy_task_backlog`。
- 认证桌面隔离环境已通过：两个 AI 勾选、主 AI切换、保存后成员显示、添加 AI 跳转、进展时间与 Human 配色，且无横向溢出。
- 生产 390px 任务列表/详情已通过：多 AI 选择、主要 AI、添加 AI、进展时间与 Human 配色可见，页面无横向溢出且控制台无 error/warning。
- PostgreSQL 0034 → 0035 → 0034 → 0035 演练和正式迁移通过；清理 43 个旧 Assignment、49 个关联历史 Run，目标范围剩余非终态积压为 0。
- 旧目录/频道关键字扫描：运行时 `src`、SDK、MCP、OpenClaw、插件和 Skill 无旧能力残留；迁移与反向门禁测试中保留必要名称。
- 隔离演示种子已改为 Task API，不再依赖旧多人容器；认证后的桌面端与 390px 任务列表/详情均通过，页面无横向溢出，控制台无 warning/error。
- 认证后的桌面和 390px 任务列表/详情无横向溢出、无 console error；Run 路由/唤醒标签与任务 ID 复制入口可见。真实任务附件卡因隔离种子没有物理附件，API/DOM 已覆盖但认证视觉验收仍为 `待确认`。
- SQLite 从零迁移仍在历史 0019 的 constraint ALTER 处失败，尚未执行到 0034；这是既有边界，不是 0034 的验证证据。

## 待完成

1. 完成真实任务附件卡和连接详情的认证视觉验收。
2. 完成真实用户跨设备验收；此前不得标记为 `production_accepted`。
3. 不要纳入两个无关的未跟踪管理汇报文件。

## 0.1.47 生产发布证据

- 功能提交 `3c4d827` 完成任务来源、共享上下文、进展显示和 0036 清理；公网检查发现旧机器合同描述未同步后，以补丁提交 `0fabd78` 形成最终 0.1.47，不覆盖已发布的不可变版本。
- 0.1.47 单一上传包与内部六个文件哈希全部通过；受保护切换从 0.1.46 创建完整备份、完成同 schema 迁移演练、原子切换与本机健康检查，返回 `deploy_status=ok`。0036 共取消 5 个非终态自动应答 Assignment 和 5 个关联 Run，目标非终态积压为 0。
- 独立后检返回 `postflight_status=ok`；AgentPost、Nginx、PostgreSQL 正常，关键数据量未下降，备份哈希和即时回退脚本通过。
- 公网 health/ready 为 0.1.47；协议合同 0.3 明确任务消息是共享上下文、不建自动应答 Run，Agent 结果不建同步 Run，Human 明确工作才建 Run；公开 wheel SHA-256 为 `40984be6c2afcfff6565f426d4252cf85e0549f688970e3f6c21a87d52a10877`，未知 wheel 返回 404。
- 登录态生产任务页桌面和 390px 列表/详情通过，无横向溢出和 console warning/error；这仍是 `deployed_https_verified`，不是跨设备真实用户 `production_accepted`。

## 0.1.45 生产发布证据

- 从提交 `0c9d844` 生成单一上传包；staging 的外层和内部六个文件哈希全部通过。
- 受保护切换完成 PostgreSQL 0034 → 0035 → 0034 → 0035 演练、完整备份、正式迁移、原子 current 切换和本机健康检查，返回 `deploy_status=ok`。
- 独立后检返回 `postflight_status=ok`；AgentPost、Nginx、PostgreSQL 均正常，关键数据量未下降，备份哈希和即时回退脚本通过。
- 公网 health/ready 为 0.1.45，协议合同为 0.3，公开 wheel SHA-256 为 `047f5fbd661858663b3a13fc803c33ab685b6de9d0bf1c18e51706c378c1d47f`，未知 wheel 返回 404。
- 登录态生产任务页的桌面与 390px smoke 均通过；这仍是 `deployed_https_verified`，不是跨设备真实用户 `production_accepted`。

## 0.1.44 生产发布证据

- 从明确提交 `6609837` 生成并上传单一发布包；staging 的上传包和包内文件哈希全部通过。
- 受保护切换完成 PostgreSQL 0030 → 0034 → 0030 → 0034 演练、生产备份、正式迁移、原子 current 切换和本机健康检查，返回 `deploy_status=ok`。
- 当前生产为 `0.1.44 / 0034_task_run_routing`；AgentPost、Nginx、PostgreSQL 均为 active，数据量未下降，备份哈希与即时回退脚本通过。
- 公网 health/ready、协议合同 0.3、公开 wheel 精确 SHA、未知下载 404 和认证后的任务主页均通过，完整后检返回 `postflight_status=ok`。
- 原发布包的 postflight 仍断言旧合同版本 0.1，导致首次后检在协议版本门禁停止；生产服务本身无异常。仓库已把断言修正为 0.3 并增加回归测试，随后以同一发布物和修正后的断言重跑全部后检成功。

## 发布规则

从明确提交生成单一 Workbench 上传包，不直接打包脏工作区。发布顺序固定为：

1. `scripts/aliyun/prepare-release.sh`
2. 上传单文件到 `/home/admin`
3. 执行发布物提供的 staging 命令
4. `scripts/aliyun/switch-release.sh`
5. `scripts/aliyun/postflight.sh`

发布前备份 PostgreSQL、附件、环境、systemd、Nginx 和 current 指针；正常切换只重启 AgentPost 并 reload
Nginx。公网 health/ready、wheel SHA、未知下载 404、schema、数据量与登录主流程全部通过后，也只能标记为
`deployed_https_verified`，真实用户验收前不是 `production_accepted`。
