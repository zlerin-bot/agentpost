# AgentPost 项目交接文档

## 当前接续摘要

- 0.1.53 发布候选：已获 Human 部署授权；包含下述 Human 任务界面切片，server/SDK/MCP/TypeScript/OpenClaw/插件/锁文件同步到 0.1.53，schema 保持 0037_task_activity_relations。本地发布回归 463 Python passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；63 JavaScript/Connector/OpenClaw passed；Ruff check/format、JS syntax、TypeScript build、diff check 通过。生产切换及后检待记录。

- 2026-09-05 本地未发布 Human 任务界面切片：从 0.1.52 冻结点继续，未改 server/SDK/schema/包版本。任务切换整块隐藏并 inert 旧详情，按请求序号隔离迟到响应，404 不再递归重载；选择任务写入 task 深链接，支持后退/前进和手机直接进入详情，创建任务不会被旧 URL 拉回原任务。
- Human 首屏前置待处理、近期更新及任务进展；成员/AI 选择、派工和最终提交默认折叠。工作显示归属与 ID，已完成及同对象同要求的较早工作折叠但不合并状态；历史不确定回复建议放入负责人专用筛选，确认前可对照候选原文。
- 正文卡展示主题和摘要，区分正文与真实附件；Markdown/长文本使用只创建文本节点及标题、列表、强调等安全元素的阅读视图，不执行 HTML、脚本、图片或链接，原始正文仍可查看。Human 回复显示发言身份和引用，草稿只保存在当前页面内存；未知发送结果用同一内容及幂等键重试，退出/页面离开清除草稿。主要写操作防重复点击，迟到写响应不覆盖别的任务。
- 修复参与准备阶段 waiting_human 被业务进展过滤、导致 Human 无法回答的问题；只有真实问题进入待处理，普通参与仍不冒充业务工作。提交阻塞按全部未结束 Assignment 列示，与现有服务端规则一致；本轮没有放宽提交门禁、取消历史工作或新增持续任务周期模型。
- 本地验证：51 项 JavaScript 测试通过（包括 36 项 Orbit 导航、任务竞态/失权/幂等重试/安全阅读等）；JS syntax、diff check 通过。隔离 Chrome 桌面 1470px 和移动 390px 的 scrollWidth 等于 viewport；任务切换与后退、草稿恢复、Human 回复保存、安全正文阅读、参与准备问题回答后重新入队、手机深链接/返回列表/弹窗 Escape 关闭实测通过，控制台无 warning/error。仅使用临时 SQLite 演示数据，未发送生产消息；未改 Python，未重跑 Python/PostgreSQL 或跨宿主真实 Agent 验收。
- 下一切片仍需独立设计验证：持续任务的周期交付/验收、参与准备是否阻塞最终提交、相近工作重复创建的源头与归属、汇编内容按主题和证据筛选。当前新增证据属于本地界面验证，生产仍是下列 0.1.52 状态；未部署，不是 production_accepted。

- 已建立 0.1.52 本地阶段冻结点：详细交接见 `docs/AgentPost阶段版本0.1.52交接_20260905.md`，机器可读清单见 `docs/stages/agentpost-0.1.52-local-stage.yaml`，恢复标签为 `stage-v0.1.52-20260905`。阶段包含完整重新检查证据和明确未验收项，不改变当前生产状态。
- 0.1.52 已于 2026-09-05 17:20 +08:00 完成生产后检：`bf5d0ee / 0037_task_activity_relations / deployed_https_verified`。本版新增任务讨论关系和 Human 进展投影：旧 Connector 回复通过原桥接消息确定性还原；其余无明确关系的 Agent 消息只提示任务负责人确认，确认结果写入 `task_activity_relations`，不改写原始 TaskActivity。任务页将明确工作、近期协作更新和可展开的 AI 执行状态分开；`participant_start` 不再伪装成业务进展，重复参与 Run 按 Human+Agent 归并。任务记录默认分为讨论、工作与结果、系统记录、全部，并支持逐步加载最多 2000 条及自动补齐截断范围外的回复根节点。
- 0.1.52 发布证据：单上传包及内部文件 SHA 全通过，`stage_status=ok`、`deploy_status=ok`（40 秒）、`postflight_status=ok`（2 秒）。PostgreSQL `0036 → 0037 → 0036 → 0037` 演练和正式迁移通过；备份 `/opt/agentpost/backups/20260905-171930-bf5d0ee-pre-052`，即时回退脚本和备份校验通过。
- 公网 health/ready/OpenAPI 均为 0.1.52；公开 wheel SHA-256 `4f026d63b7298ba1dc6269d38cf99a406bf748787e9bf48a52cdf1c917d312e6` 与发布物一致，未知 wheel 返回 404。后检 agents=67、messages=630、deliveries=606、attachments=51、humans=16，关键计数未减少。AgentPost PID 从 423665 更新为 437151；Nginx=362620、PostgreSQL=365086 保持原进程。
- 0.1.52 本地验证：Alembic 单 head `0037_task_activity_relations`；463 Python passed、1 沙箱 skip、5 PostgreSQL deselected；36 项前端导航测试、TypeScript Connector 8 项、OpenClaw 4 项、JS syntax、TypeScript build、Ruff check/format 和 diff check 通过。隔离认证页面桌面与 390px 无横向溢出，任务进展、讨论筛选和 AI 执行状态可读，控制台无 warning/error。刷新生产页面后既有 Human 会话已过期，公开登录页视觉正常；登录后真实任务页仍待用户验收。
- 0.1.51 已于 2026-09-04 18:19 +08:00 完成生产后检：`2a6b464 / 0036_cancel_auto_ack_runs / deployed_https_verified`。下列“待发布”条目为本次发布前记录，现已随 0.1.51 上线；历史消息未补写回复关联。
- 发布证据：单上传包和内部文件 SHA 全通过，`stage_status=ok`、`deploy_status=ok`（39 秒）、`postflight_status=ok`（3 秒）。备份 `/opt/agentpost/backups/20260904-181757-2a6b464-pre-051`，已验证 `rollback-immediate-0.1.51.sh` 与 0.1.50 回退资料。
- 公网 health/ready/OpenAPI 均为 0.1.51，公开 wheel SHA-256 `41b236f5a6dcb0e2bc464e82769f6a9df09e57814b581b2a48111ec0e4571008`；后检 agents=65、messages=606、deliveries=588、attachments=51、humans=16，关键计数未减少。AgentPost PID=423665，Nginx=362620、PostgreSQL=365086 保持原进程；schema 未变化。
- 已登录生产新标签页确认“测试任务”的重复标题消失、接收方折叠为“共享给 N 人”、回复入口与讨论/时间切换可见，控制台无 error/warn。未发送生产测试消息；跨设备真实回复验收仍待确认，不标记 `production_accepted`。本次发布回归：462 Python passed、1 沙箱 skip、5 PostgreSQL deselected；52 JavaScript/Connector/OpenClaw passed，TypeScript 编译/Ruff/format/JS syntax/diff check 通过。
- 0.1.51 发布候选：整合任务页标题/接收方降噪与显式回复串；server/SDK/MCP/OpenClaw/插件/锁文件版本已同步。schema 保持 `0036_cancel_auto_ack_runs`。已获部署授权，按单上传包 Workbench 流程执行，生产切换与后检结果待记录。
- 本地待发布回复关联切片：Task 消息支持 `reply_to_activity_id`、`referenced_activity_ids`，服务端验证同任务并生成 `discussion_root_activity_id`；无回复参数的旧连接与既有幂等哈希保持兼容，不推断历史关联。Python SDK/MCP/OpenClaw/机器合同同步新增可选参数。Human 可在任务记录直接回复，使用 Human 会话、CSRF、幂等键与真实 Human 身份，写入共享 TaskActivity，不代替 Run/Human 验收；该入口不产生旧 Inbox 投递或唤醒工单，Agent 通过 Task API 读取。页面默认按讨论折叠、可切换时间视图，支持原文定位；附加引用目前由 Agent API 提供，网站回复入口只选择一条直接回复对象。462 项非 PostgreSQL 测试通过、1 沙箱 skip、5 PostgreSQL deselected；35 项导航测试通过，Ruff/format/JS syntax 通过。隔离 Chrome 实测两级 Human 回复、讨论/时间切换、原文定位、390px 无横向溢出与控制台错误。未部署、未修改历史生产消息。
- 本地待发布 UI 小切片：任务记录接收范围默认折叠为“共享给 N 人”，按 Human ID 去重；展开后查看 Human/AI 与简短状态，兼容投递及未知状态在摘要提示。只调整展示，不改变投递、已读或 Run 状态。前端导航测试 34 项、JS 语法及 diff check 通过；隔离浏览器因本地 Chrome 沙箱启动失败，桌面/390px 交互验证待确认；未部署。
- 交接阶段：`0.1.52-deployed-https-verified`
- 本地与生产：`bf5d0ee / 0.1.52 / 0037_task_activity_relations`；保留完整 0.1.51 即时回退点。
- 当前生产：`bf5d0ee / 0.1.52 / 0037_task_activity_relations / deployed_https_verified`（2026-09-05 17:20 +08:00 完成后检）。
- 生产接受状态：不是 `production_accepted`
- 本切片：修复旧 Thread 列表/详情混入无 Delivery 的 Task 源消息导致 500；保留当前 Agent 的实际投递视图，并要求 TaskMembership 与 Agent 参与资格均有效。共享完整上下文继续使用 Task API，不恢复无任务私信。
- OpenAPI 版本使用实际包版本；意外异常返回安全 JSON 和 request_id，不输出异常正文或凭据。心跳显式返回 version_status、原因、推荐与最低版本，未上报保持 unknown；Python SDK 兼容旧响应缺少这些字段。
- 测试任务反馈口径：无 Task bridge 的历史私信回复被拒绝是预期行为。完成状态以服务端 Run/Result 为准；正文的“尚未提交”保留为原始 Agent 内容，不能自动改写历史状态，更不能据此推断 Task 已提交或 Human 已验收。
- 本切片已部署，未手动修改生产任务或好友关系，也未发送协同消息。登录入口正常；Chrome 重启后 Human 会话已退出，生产登录后好友页、移动端及跨设备真实用户验收仍待完成。

### 0.1.50 发布证据（2026-09-04）

- 已发布好友入口待确认数量、可点击待处理提示、“待你确认/已发申请”分离，以及旧 Thread 投递视图隔离、运行版本诊断修复。
- 发布提交 `2ae66a3e1218dc36e80d2614ce302ece33d49e07`；固定 Workbench 上传/暂存/切换/后检流程，`stage_status=ok`、`deploy_status=ok`（39 秒）、`postflight_status=ok`（3 秒）。
- 备份 `/opt/agentpost/backups/20260904-100915-2ae66a3-pre-050`；回退脚本 `rollback-immediate-0.1.50.sh`，dump/附件/配置/旧 wheel 校验通过。
- 公网及本机 health/ready 均正常，公网 OpenAPI 版本 0.1.50；wheel SHA-256 `239c59bcf3b36ca2e1ea2266f0ad5b36891f7ff186466b1f2fd668f4ffb62724` 与发布物一致，未知 wheel 404。
- 后检数据量：agents=63、messages=581、deliveries=572、attachments=50、humans=16；脚本确认关键计数未减少。AgentPost PID=417472，Nginx PID=362620、PostgreSQL PID=365086 保持原进程。
- 本地回归证据见发布候选记录；生产真实用户验收仍为 pending，不标记 `production_accepted`。

## 当前产品模型

AgentPost 的多人协作只发生在 Task 内。每个 Task 有一个稳定 `task_id` 和一条主 `thread_id`；Human 是否能
进入任务只由 `TaskMembership` 决定。Human 为任务选择自有 Agent，未选择时使用默认 Agent。任务内 Agent
均可读取上下文并参与，具体执行通过 Agent Run 的队列、租约、心跳和幂等完成机制协调。Human 验收与消息
送达、Agent read、ACK、Run 完成和 Agent Result 分别保存。

好友是双向 Human 关系，只用于识别和任务邀请。Agent 新消息必须明确归属 Task；服务端拒绝无任务的一对一
新消息。旧 Connector 只保留服务端任务桥接通知及其读取、ACK、任务内回复。任何后续协作能力必须扩展
Task，不能再建立平行容器、另一套成员角色或共享通信规则。

权威设计见 `docs/TASK_CORE_MODEL.md`；未来开发约束见 `AGENTS.md`。

## 本切片已经完成

- Agent 的 waiting_human checkpoint 进入 Human 任务详情和完整记录；任务负责人或该工作责任 Human 可直接回复。回复会使旧租约失效，并在同一 Assignment 下创建 successor Run，Human 回复通过 checkpoint 交给 Agent。
- 空白回复返回校验错误、重复回复返回状态冲突、旧租约不能继续写入；pending preview 和 claim 均携带 successor checkpoint。
- 进展卡分别显示状态变化时间和当前执行尝试的心跳；等待 Human 不再错误显示“尚未反馈”，回复后明确显示“等待 AI 重新领取”。
- Task 状态轴彻底排除历史 `task_message` / `result_sync` Assignment；“mixed”改为“部分执行单元已有结果”，不再暗示 Agent 结论冲突。
- 任务内 AI 统一使用 Agent display name；同一 Assignment 的执行生命周期折叠为一组，旧自动协同折叠到“0.1.47 前的历史自动协同”。
- 长进展提供“查看完整任务记录”链接，自动展开并定位对应记录；新建工作和 Agent Result 的完整正文写入并显示在任务记录中。
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

- 0.1.50 发布候选：非 PostgreSQL 回归 461 passed、1 loopback sandbox skip、5 PostgreSQL deselected；JavaScript/TypeScript/OpenClaw 共 50 passed；TypeScript 构建、Ruff、format、diff check 通过。server/SDK/MCP/插件/TypeScript/OpenClaw/uv.lock 版本统一，新增版本一致性门禁。部署授权已取得，生产结果待后检记录。
- 2026-09-04 好友待确认提示：一级“好友”入口显示 incoming 数量，好友页提供可点击待处理提示、分离“待你确认/已发申请”，首次加载优先展示收到的申请，处理后清除计数；待确认时不再误报 0 个 Agent。38 项前端测试、JS syntax 与 diff check 通过；隔离测试账户桌面/390px 读取与接受申请通过，手机接受后回到列表，计数 2→1→0，控制台无 error/warn。本轮不发送邮件、不修改生产好友关系，尚未部署。
- 2026-09-04 Thread 兼容修复：完整非 PostgreSQL 回归 460 passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；真实 Task 源消息/桥接消息混合、撤销参与资格、跨收件人隔离、读取无状态副作用、异常 JSON 脱敏和 OpenAPI 版本一致性均有回归覆盖。Ruff check / format check / diff check 通过。本轮未改前端、未运行浏览器验收、未部署。
- 0.1.49 `.venv/bin/pytest -m "not postgres"`：457 passed、1 expected skip、5 deselected；浏览器 JavaScript 37 passed、TypeScript Connector 8 passed并完成编译、OpenClaw adapter 4 passed；Ruff、format、JavaScript syntax、wheel 构建和 `git diff --check` 通过；本地 wheel SHA-256 为 `5acf653829825e23abc83d1fc970110eb29a9b621dcb98987a66d59ff6b2fd3c`。
- 0.1.48 `.venv/bin/pytest -m "not postgres"`：456 passed、1 expected skip、5 deselected；全部 JavaScript 37 passed、TypeScript Connector 8 passed并完成编译；Ruff、format、JavaScript syntax 通过；本地 wheel SHA-256 为 `cc80b8816b808e9dd963c6dc0065d05f1d52eb7a4bd639265b8b6d04e3d1d211`。
- 0.1.48 隔离认证浏览器闭环通过：waiting_human 问题可见，Human 回复后同 Assignment 变为待领取，页面显示回复内容；桌面和 390px 无横向溢出。
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

1. 登录生产 Human 页面，用真实“小孔成像”数据确认 Zoe 旧版桥接回复能确定性归入 Mars 原讨论；不直接修改生产活动。
2. 在真实 Agent 上完成 waiting_human 回复后的重新领取、执行和结果回写跨设备验收。
3. 完成真实任务附件卡、连接详情和任务讨论关系的认证视觉验收。
4. 完成真实用户跨设备验收；此前不得标记为 `production_accepted`。
5. 不要纳入两个无关的未跟踪管理汇报文件。

## 0.1.49 生产发布证据

- 从提交 `770fcac` 生成 0.1.49 单一发布包；上传包 SHA-256 为 `4874feddf155771591d622a965a45f4c0dc9b00af1a8d07902ff287fb96b3f49`，包内清单、源码、wheel、manifest 和发布脚本哈希全部通过。
- Workbench 当前 `/home/admin` 由 root 持有且登录用户不可写，因此先创建仅供发布上传、归 admin 所有的 `/home/admin/agentpost-upload`，未改变既有发布目录权限；随后完成脚本语法检查和受保护原子切换。
- 受保护切换返回 `deploy_status=ok release=0.1.49 commit=770fcac`；独立后检返回 `postflight_status=ok`，AgentPost、Nginx、PostgreSQL 正常，schema 为 `0036_cancel_auto_ack_runs`，备份和关键数据量检查通过。
- 开发机独立公网核对 health/ready 均为 0.1.49，协议合同为 0.4，Connector 推荐版本为 0.1.49、最低兼容版本为 0.1.34；公开 wheel SHA-256 为 `5acf653829825e23abc83d1fc970110eb29a9b621dcb98987a66d59ff6b2fd3c`，未知 wheel 返回 404。
- 当前状态为 `deployed_https_verified`；尚未完成真实用户跨设备验收，因此不是 `production_accepted`。

## 0.1.48 生产发布证据

- 从提交 `36855ff` 生成并上传单一发布包；staging 的外层和内部六个文件哈希、切换与后检脚本语法全部通过。
- 受保护切换从 0.1.47 创建完整备份，完成同 schema PostgreSQL 迁移往返演练、原子 current 切换和本机健康检查，返回 `deploy_status=ok`；只重启 AgentPost 并 reload Nginx。
- 独立后检返回 `postflight_status=ok`；AgentPost、Nginx、PostgreSQL 正常，schema 为 `0036_cancel_auto_ack_runs`，关键数据量未下降，备份哈希和即时回退脚本通过。
- 开发机独立公网核对 health/ready、连接升级配置均为 0.1.48；公开 wheel SHA-256 为 `cc80b8816b808e9dd963c6dc0065d05f1d52eb7a4bd639265b8b6d04e3d1d211`，未知 wheel 返回 404。
- 登录态生产“测试任务”确认 waiting_human 问题和 Human 回复入口可见；长进展的“查看完整任务记录”链接可自动展开分组、更新 URL 锚点并定位到完整记录，控制台无 warning/error。

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
