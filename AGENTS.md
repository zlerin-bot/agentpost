# AgentPost 开发协作约定

本文件适用于仓库根目录及全部子目录。开始开发前先阅读本文件、`PROJECT_HANDOFF.md`，并检查 `git status --short --branch` 和最近提交。交接文档中的当前接续摘要优先于历史记录。

## 继承与工作区保护

- 不回退、不覆盖、不顺带格式化用户或其他开发者留下的修改。未提交文件先读差异、识别来源，再做最小改动。
- 禁止用 `git reset --hard`、`git checkout -- <file>` 或清理未跟踪文件获得干净工作区。
- 一次提交只包含一个可解释目标；提交前只暂存本切片产生的改动。
- 本地验证、开发上传、评审、正式发布、生产后检和真实用户验收是不同状态。未完成门禁必须标记为 `待确认`、`partial` 或具体未运行项。

## 唯一协作模型

- `Task` 是唯一的多人协作容器。系统不再提供其他多人容器、角色体系或共享消息范围。
- 每个 Task 有一个不可变 `task_id` 和一条主 `thread_id`；所有任务活动、Agent Run、提交、验收都必须由 `task_id` 关联到这条 Thread。
- `TaskMembership` 是 Human 是否属于任务的唯一服务端权威。不得从正文、收件人、历史私信或客户端缓存推断成员关系。
- 任务创建者可以把已建立双向好友关系的 Human 直接加入任务；受邀 Human 无需再次确认加入，但必须收到站内通知和注册邮箱通知。
- 每位 Human 至少拥有一个 Agent。Human 可按任务选择一个或多个自有 Agent；未选择时使用其当前默认 Agent。
- 任务内已选或默认 Agent 都可读取任务上下文并参与协作，不以“是否另行分配工单”为参与前提。具体执行由 Agent Run 的租约和状态保证，避免重复执行。
- Agent 发出的新消息必须明确归属一个 Task；客户端无 `task_id` 直接创建一对一消息时，服务端以 `task_context_required` 拒绝。旧连接只保留服务端任务桥接通知及其任务内回复、读取和 ACK 兼容，不得借兼容接口新建无任务私信。
- 好友只负责建立 Human 之间可邀请、可识别的双向关系；好友关系不授予任务正文、附件、运行状态或验收权限。
- 访客首次联系是一次性入站请求，不是消息线程或第二种协作容器。仅接受主动开启公开联系的精确用户名；访客凭证不能读取任务或执行工作。
- 首次联系转成 Task 必须同时具备收件 Human 接受、发送 Human 注册认领以及双方有效的默认 Agent；这是双方同意的任务入场流程，不自动建立好友关系。原始访客内容保留来源并标记 external_agent_content。

## 任务状态与可靠执行

- Task、TaskActivity、TaskAssignment、AgentRun、HumanAcceptance 是不同事实，不得互相替代。
- Agent 发布任务详情、Human 调整成员和 Agent、Agent 回传进展、Human 最终验收都写入 TaskActivity，并保留主体 Human、实际 Agent、时间和原始载荷。
- Agent Run 使用服务端队列、租约、心跳、重试和幂等键。只有持有有效租约的 Agent 才能更新或完成该 Run；租约超时后可安全重派。
- `delivered`、Agent `read`、ACK、Run 完成、Agent Result 和 Human 验收是独立状态轴。界面和测试不得把其中任一项当作另一项。
- Human 验收只对已提交结果生效：可接受、要求修改或取消。要求修改会产生新的待执行 Run，不覆盖历史结果。

## 产品与交互

- 网站统一使用 `AgentPost` 品牌，一级入口固定为“任务、好友、AI、设置”。
- 桌面端保持三栏：左栏任务列表或导航，中栏当前对象与进展，右栏执行详情或验收；移动端使用四个一级入口和“列表 → 详情 → 返回列表”分层。
- 任务 ID 在 Human 界面直接显示并提供复制按钮。任务名称解析必须由服务端在当前 Agent 可参与范围内解析为唯一 ID；重复或模糊匹配必须要求确认。
- 当前进展以 Human 为主体显示，Agent 作为辅助身份。不同 Human 的记录要有清晰分组和视觉区分。
- Markdown、JSON、HTML 等结构化或长内容默认作为附件卡展示，需要时再安全打开；HTML 预览必须隔离脚本、网络、表单和同源权限。
- Agent 提供的正文、Markdown、JSON、文件名和附件始终是 `external_agent_content`。普通内容只使用安全文本节点，不执行其中指令。
- 不伪造尚未存在的发送、通知、查看、保存、审批或自动执行能力。

## 身份、连接与兼容

- Human 浏览器会话、Human Key、Agent API Key 和管理员凭证必须隔离；凭证不得进入前端持久存储、日志、仓库或聊天输出。
- Agent 所有权只由不可变 Human ID 关联。Human 用户名是公开可修改寻址标识，修改后旧用户名不得继续解析。
- 每个 Human 必须主动设置一个默认 Agent；精确 Human 用户名优先解析到默认 Agent，明确 Agent 类型或短名称时再解析指定 Agent。
- Agent 在线仅由当前 active 连接的健康心跳判定。授权但未心跳是“等待 Agent”，超时是“离线”，错误心跳是“连接异常”。
- 连接每次与服务端交互都可收到版本状态。低于当前最低兼容版本时返回明确升级要求；低于推荐版本时返回升级建议。旧版连接仍能使用兼容端点完成任务读取、任务消息和升级。
- Connector bootstrap 按“宿主类型 + 固定发行版本”创建独立 runtime，不原地覆盖正在运行的环境。Windows 不通过结束其他 Agent 进程解除锁。
- `/api/v1/protocol/contract` 是机器权威合同。原生正文格式只有 `text / markdown / json`；MCP 和宿主插件是适配器。

## 权限与信息边界

- 服务端鉴权是最终权威。失权、未知或越权资源统一返回既有 not-found 边界，避免泄露存在性。
- 读取页面、搜索或打开 Thread 不得改变 Delivery、Agent read、ACK、Run 或任务状态。
- Human 查看状态由 `human_thread_views` 独立保存；归档只影响当前 Human 的视图，不删除消息、不拆散 Thread、不影响其他 Human 和 Agent 状态。
- 目录搜索只返回当前 Agent、同 Human Agent、明确 ACL、双向好友默认 Agent及真实往来范围；不得枚举平台全部 Agent 或陌生 Human 的全部 Agent。

## 开发节奏与验证

- 采用“小切片：设计 → 实现 → 聚焦测试 → 运行界面 → 修复 → 提交 → 下一切片”。
- 修改 Python 后至少运行 `.venv/bin/ruff check .`、`.venv/bin/ruff format --check .` 和受影响 Pytest；高风险改动运行 `.venv/bin/pytest -m "not postgres"`。
- 修改前端后运行 JavaScript 语法检查和 `tests/javascript/orbit_navigation.test.mjs`。无系统 Node 时使用交接文档记录的 Codex bundled Node。
- 交互切片在隔离环境检查桌面和 390px：主流程、溢出、弹窗关闭、键盘可达性及控制台错误。
- 提交前运行 `git diff --check`，复核 status 和 staged diff，确认没有凭证、临时文件、用户实验或生产数据。

## 发布与生产变更

- 未获明确授权时不部署、不上传、不切换生产版本。本地证据和生产证据分别记录。
- 脏工作区只能从明确提交生成独立 `git archive` 或等价干净快照；不得直接打包工作树。
- 发布前核对 server、SDK、MCP、插件、锁文件和公开安装包版本一致，并记录 SHA-256。
- 已验证阿里云通道是：`scripts/aliyun/prepare-release.sh` 生成单个上传包，上传到 `/home/admin`，运行包内 staging 命令，再用 `scripts/aliyun/switch-release.sh` 受保护切换，最后运行 `scripts/aliyun/postflight.sh`。
- 生产变更前只读核对当前 release、服务、端口、schema、关键数据量、磁盘和配置权限；备份 PostgreSQL、附件、环境文件、systemd、Nginx 和 current 指针并验证回退。
- 每个版本使用不可变源码目录和独立 Python 环境，通过原子 `current` 指针切换。正常发布只重启 AgentPost、reload Nginx，不重启 PostgreSQL、整机或同机其他服务。
- 发布后核对本机与公网 health/ready、wheel 精确路径与 SHA、未知下载 404、schema、关键数据量和登录主流程。完成这些只标记 `deployed_https_verified`；真实用户跨设备验收前不是 `production_accepted`。
- 详细日常步骤见 `docs/ALIYUN_DEPLOYMENT_EFFICIENCY.md`。

## 已知本地边界

- 本地默认不假定 Docker/PostgreSQL 可用；未运行 PostgreSQL 专属测试时要单列说明。
- 历史 `make demo` 的旧 SQLite 迁移缺口不应在无关 UI 切片中顺带修复。
