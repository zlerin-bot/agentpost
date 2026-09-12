# AgentPost 项目交接文档

## 当前接续摘要

- 2026-09-12 **0.1.69 / 7d570c3 已部署，技术后检通过**：最新协作分层与Word直接阅读已上线，deploy/postflight=ok；Linux中文DOC真实合成文件解析通过。GitHub同步被自动审批拒绝，待Human明确确认既有仓库/分支；正式浏览器会话过期，登录后UI与跨设备验收待确认。测试任务已发送activity `a16230e4-ad7c-46d2-96ef-1e2d87e1fefc`，未创建Run。详细SHA、备份与进程证据见 `docs/DEPLOYMENT_0.1.69_20260912.md`。下文两个“未部署”为历史记录；定时任务保持暂停。

- 2026-09-12 **主流文件站内阅读 local_verified，未部署**：新增DOCX正文/标题/表格与DOC文字预览；文件目录和讨论区均支持查看，PDF/DOC/DOCX增加后缀兜底，DOCX ZIP MIME按Word识别。预览窗口改用阅读提示、修正下载链接对比度。DOCX图片/批注/复杂排版、旧DOC原版排版不支持，界面明确说明。Linux生产DOC需要antiword，已纳入Docker/授权发布安装与后检；当前只验证macOS textutil真实DOC，Linux待部署验收。完整非PG551 passed、2 skipped、7 deselected；增加体积边界后聚焦37 passed，50前端测试通过。独立8783演示及权限/解析限制详见 `docs/FILE_PREVIEW_20260912.md`。产品原则：用户点击直接阅读、尽量减少操作，下载作为可选；已按用户要求记录偏好。生产仍0.1.68，自动任务暂停。

- 2026-09-12 **任务首页信息分层 local_verified，未部署**：新增最近5条讨论/回复/结果原文摘录“最新协作”，明确Human及辅助Agent身份，支持定位原文；“工作与结果”改为“已安排的工作”。已完成或连续7天无进展的派工默认收进“历史及未结工作”，等待Human或正在执行的不收起，业务状态不变。状态时间选最新关联活动，缺失时使用assignment.updated_at。需要我处理继续仅显示可操作事项，无事项隐藏。49项前端测试、语法、diff检查通过，桌面1470px与390px原文定位/历史展开/弹窗Escape实测；无横向溢出、无JS异常，唯一最终资源错误是登录前正常session401。合成新增记录仅浏览器响应替换，未写入任务数据。8782预览已生效；生产仍0.1.68，自动任务暂停。

- 2026-09-11 **0.1.68 / d88ca7c / 0043_webhook_protocol 已部署，deployed_https_verified**：17:03 北京时间完成受保护切换，deploy_status=ok；独立 postflight 两次通过，公网 health/ready、auth 推荐版本、wheel SHA、未知下载 404 和现有 Human 登录态打开测试任务通过。覆盖下述 Webhook/状态、密码、附件及协作接续切片，早先“未部署”记录为历史状态。真实飞书端到端、PostgreSQL 并发和跨设备 Human 验收仍待确认；Aily 暂未开放，定时任务保持暂停。
- 已在 020 最新 Webhook 反馈 activity `0fbd99bf-17f2-43fb-bdaa-1d96c4571aa9` 下逐项回复；新 activity `c83e28ef-cbd1-40d8-b0a6-65752f4b7572`，身份复用 mars agent，未创建 Run。部署证据及本次发现的回退脚本生成修复见 `docs/DEPLOYMENT_0.1.68_20260911.md`。

- 2026-09-11 **020 Webhook/额度/连接状态反馈修复 local_verified，未部署**：本地接口级复现测试失败后 audit outcome=`failed` 违反数据库 `failure` 约束导致 500，已修正；错误响应补 request_id/event_id，畸形外部 code 不再抛出 TypeError。新增明确 HMAC-SHA256/X-Webhook 与 Bearer 协议选择，按实际 UTF-8 发送字节签名，测试改为唯一事件 ID，区分接受、业务拒绝及 already_processed；旧配置迁移保留 Bearer，未静默更改生产密钥或协议。
- Human 飞书通知增加测试额度确认、跨测试/后台共享的数据库一分钟发送间隔；保存不补发历史工作，测试成功才启用新工作提醒，失败停止重试并暂停，中断发送标记结果不明而不重放。提醒仍不等于 Human 收到、Agent 启动或 Run 执行；本轮不包含日金额预算、通知合并或真实飞书计费查询。连接管理统一 Human 状态文案，区分从未上线与曾上线后超时；历史健康上报和版本兼容性不再冒充当前在线。
- 验证：最终完整非 PostgreSQL **548 passed、2 skipped、7 deselected**，Orbit **47 passed**，Ruff check/format、JS syntax、diff check 通过；SQLite 0043 迁移往返通过。Chrome 1470px/390px 表单实看无横向溢出，合成配置保存、未勾选阻止测试及停用通过，console error/warn=0；没有调用真实飞书 Webhook。8781/8782 演示保留数据库和 demo@example.com / 123456，备份为各演示目录 orbit-demo.pre0043.db，已迁移并重启。生产仍 0.1.67/6b40ebb/schema0042；本地候选新 schema 0043_webhook_protocol，未来部署前须迁移。PostgreSQL 并发、生产异常日志核对、真实飞书通知和跨设备 Human 收件验收待确认。飞书 Aily 直连仍暂未开放，定时任务保持暂停。详情见 `docs/WEBHOOK_FEEDBACK_FIX_20260911.md`。

- 2026-09-11 **密码规则修正 local_verified，未部署**：登录表单移除最低长度限制，仅验证已有密码；注册/找回密码前后端统一最低 8 位、最高 256 位，保留原哈希验证、限流和 MFA。修复之前本地后端允许 `123456` 但 HTML minlength=12 阻止提交的遗漏。两个本地演示（8781/8782）账号现统一 `demo@example.com`，密码 `123456`；仅这些合成账号使用六位密码。已通过浏览器实际登录 8782；Python 9 项与 Orbit 46 项通过，Ruff/format/diff check 通过。两服务已保留原数据库重载，新启动命令为 `PYTHONPATH=src:sdk/python/src:integrations/mcp/src .venv/bin/python /private/tmp/ap_existing_preview.py 8781`（或 8782）；不要重新运行旧 seed 脚本重建账号。生产密码规则待部署后生效。

- 2026-09-11 **附件预览修复 local_verified，未部署**：前后端统一使用受限扩展名兜底识别，修复 `application/octet-stream` / `text/plain` 上传的 `.md` 被归为“其他”且缺少“查看内容”。文件目录筛选、讨论附件卡与预览弹窗均一致，既有附件无需修改数据库或重新上传。保留已识别的 PDF/HTML/JSON 等类型，不将 `.md.exe` 当 Markdown。
- 新增 ZIP“查看目录”，只读取归档元数据，显示文件名、未压缩大小和加密标记，最多展示 200 项；不解压、不执行、不读取包内正文。目录名安全转义并沿用 sandbox CSP、Human 鉴权与只读状态边界；损坏 ZIP 给出可理解提示。RAR/7z 和包内文件正文预览未实现。
- 本轮完整非 PostgreSQL 535 passed、2 skipped、7 deselected；聚焦 Python 25 passed、前端 45 passed，Ruff/format、JS syntax、diff check 通过。Chrome 合成上传（ZIP 与 MD 均用通用 MIME）实际验证文件目录及讨论区的入口、Markdown 标题列表、ZIP 目录、Escape 关闭；390px 弹窗无横向溢出，控制台无 error/warn。隔离演示 `http://127.0.0.1:8782/orbit?module=projects&view=board&task=788a3450-0502-42f2-883c-94613498af43`；合成账号同 8781，脚本 `/private/tmp/ap_attachment_demo.py`。生产未变更。

- 2026-09-11 **协作接续切片 local_verified，未部署**：新增 `/api/v1/agent/tasks/{task_id}/briefing`，按当前 Agent 的活跃任务资格返回目标、预期输出、角色、自己的未完成工作及有来源的活动摘要；首次只读最近记录，后续活动游标增量，工作独立分页，每轮重新开始工作分页。来源文本带截断标记，必须读取完整要求并 claim 后才执行；不修改已读、ACK、租约或任务状态。Python SDK/标准 MCP 新增 `task_briefing`，补齐 `get_task(include_assignments=false)`，机器合同和握手补充接续入口，保留旧握手 next_steps。
- 同一切片将 Human“需要我处理”收敛为本人可回答的问题和负责人验收，显示事项、具体问题与直接操作；普通队列不再冒充 Human 待办。复用既有回答后旧租约失效与 successor Run 入队规则。Chrome 合成数据实测回答后提示消失并重新入队，1470px/390px 均无横向溢出，键盘定位正常，控制台 error/warn=0；移动端 flex 换行造成的新卡溢出已当场修正复核。
- 证据：完整非 PostgreSQL `531 passed、2 skipped、7 deselected`（随后补充的工作隔离测试另测）；最终受影响 Task/SDK/MCP 回归 **80 passed**、Orbit **44 passed**；Ruff check/format、JS syntax、diff check 通过。PostgreSQL、真实无人值守跨 Human/跨宿主执行、Human 验收未运行。本轮未部署、未发生产通知、未恢复定时任务、未修改宿主连接。
- 本地演示 `http://127.0.0.1:8781/orbit?module=projects&view=board&task=b61803ed-4307-48a8-9aba-b5f56310bbbc`；合成账号 `resume-reviewer@example.com`，密码 `correct horse battery staple`，启动脚本 `/private/tmp/ap_resume_demo.py`，仅本机测试使用。详细实现及下一步真实双 Human/双 Agent 验收方案见 `docs/COLLABORATION_RESUMPTION_20260911.md`。任务结论确认、Human 接管/重派、自动对话预算及所有宿主无人值守闭环仍为后续切片，不能称为全部完成。

- 2026-09-11 当前生产 **0.1.67 / 6b40ebb / 0042_feishu_human_notifications / deployed_https_verified**：按 Human 决定暂停飞书 Aily 直连路线。“连接新的 Agent”仍保留“飞书 aily 智能体”卡片用于说明产品边界，但卡片禁用并明确显示“暂未开放”，不会生成接入码；前端同时核对固定宿主能力与服务端配置，避免旧配置把入口重新放开。生产 `AGENTPOST_FEISHU_AILY_REMOTE_MCP_ENABLED=false`，公开配置返回 `host_setup_platforms.feishu_aily=[]`、`host_connection_modes.feishu_aily=unavailable`，postflight 将这两项作为强制门禁。通用 Remote MCP/OAuth 适配基础和 Human 飞书通知保留，未继续提供 Aily 长期 Token 或含凭证 URL 等绕过方案。
- 0.1.67 同时包含 0.1.66 的 Agent 身份连续性修复，以及 Agent 状态与连接设置界面修复：通用异常不再显示红色“需要处理”，详情页“危险操作”改为“连接设置”，CSS `hidden` 冲突已修复。单包 SHA-256 `51b7eeda694ea2b382e9178f479b0ed02ec4dbf34d8d6f117ba6d14133826887`；stage、deploy、postflight 均为 ok，切换 51 秒，备份 `/opt/agentpost/backups/20260911-091840-6b40ebb-pre-067`。公网 health/ready 返回 0.1.67，公开 wheel SHA-256 `5884f2dc94f0239d239ba4b53168933d7bb5010fcfadd8d8345cc3fad4e050e1`，精确下载 200、未知下载 404。后检 agents=78、messages=449、deliveries=301、attachments=45、humans=16；AgentPost PID=542761、MCP PID=542817，Nginx PID=362620、PostgreSQL PID=365086 保持原进程。
- 0.1.67 生产页面刷新后实看：Agent 列表显示“暂不可接任务”，详情页显示“连接设置”；新建连接窗口的“飞书 aily 智能体”卡片为禁用态“暂未开放”。本地完整非 PostgreSQL 回归 `530 passed、2 skipped、7 deselected`，Python 聚焦 67 项和 JavaScript/TypeScript 51 项通过，Ruff、JS syntax、shell syntax、diff check 通过。真实跨设备和 Human 验收仍待确认，因此不是 `production_accepted`。
- 已向“测试任务”发送 0.1.67 上线说明及针对性复测清单，activity `4320a0f1-573e-4ec1-835d-75eeb206de96`；消息已写入 Task，未创建额外 Run。发送成功不等于成员已读、ACK、复测完成或 Human 验收。
- 2026-09-11 **Agent 状态表达与连接设置界面 local_verified，未部署**：中栏 Agent 列表及详情页不再把通用 `needs_attention` 显示成红色“需要处理”，改为金色状态“暂不可接任务”；只有服务端明确返回 `connection_error` 时才显示红色“连接异常”。状态徽标补充实际原因提示，不再呈现成待点击的处理入口。详情页“危险操作”改为“连接设置”，并把重连/断开与软删除拆成“连接设置”“Agent 管理”两块；同时修复 CSS 覆盖原生 `hidden` 规则导致所有者操作与“只读”说明同时出现的问题。桌面隔离预览已实看；43 项 Orbit JavaScript、23 项 Human control plane、JS syntax 和 diff check 通过，390px 真实视觉复核、发布包重建、生产部署及 Human 验收待确认。
- 同日用飞书“**Mars的智能伙伴**”执行真实 AgentPost Remote MCP 接入：Aily 沙箱可访问 `agentpost.me`，目标 MCP 返回标准 `401` 与 `WWW-Authenticate resource_metadata`，受保护资源元数据和 OAuth authorization-server 元数据均返回 `200`，公开了动态注册、authorization code、device code、PKCE S256 和 `agentpost.messaging`。但 `aily-mcp install-remote` 在保存前探测收到首次 `401` 后没有继续 OAuth discovery，以 `221404 / test mcp server failed / mcp.hub.upsert_custom_server` 退出；AgentPost 未安装、没有工具、没有读取“测试任务”。这已排除网络、URL 和 AgentPost OAuth 元数据缺失，当前阻点是 Aily Remote MCP 安装器的 OAuth 客户端兼容能力。禁止用长期 Bearer/API Key 或含凭证 URL 绕过；后续须取得 Aily 可配置的跨应用 OAuth 参数或由 Aily 修复标准 discovery 后再继续，当前状态为 `blocked_by_aily_oauth_client`，不得称为已接入。
- 2026-09-11 **0.1.66 Agent 身份连续性候选 local_verified，未部署**：修复同一宿主升级或恢复时因 profile 漂移、旧凭证失效而误建 `codex2`、`codex3` 等重复 Agent。Skill bootstrap 在安装或联网前必须从当前 Codex、WorkBuddy、OpenClaw、Hermes 注册中恢复精确 `AGENTPOST_PROFILE`，无法恢复即以 `current_profile_unavailable` 停止，绝不进入新配对。Python SDK 将不可变 `agent_id` 与凭证一起保存在系统钥匙串；旧凭证首次健康心跳自动补齐，凭证失效后只允许定向重连原 Agent，旧凭证缺少身份时保留原记录并要求从原 Agent 卡片恢复。Human 配对页检测到已有 Agent 时默认选择原 Agent，并把“这是另一个新的 AI”作为明确选项；只有账号尚无 Agent 时才自动进入首次创建。
- 0.1.66 证据：完整非 PostgreSQL 回归 `530 passed、2 skipped、7 deselected`；Python 聚焦 90 项、JavaScript/TypeScript 51 项通过；Ruff check/format、JS syntax、TypeScript build、两份 Skill bootstrap 一致性及 diff check 通过。最终 wheel SHA-256 `4fc0405fbc9caefed4f69e5a0002c22aa39d86900c0c68ba75999abac2ab7509`，wheel 内 bootstrap 与源码 SHA-256 均为 `270c775864b902da0b70b97d37423db4f23493b227889315db63b3dc58868d37`；Codex、WorkBuddy、豆包工作、OpenClaw、Hermes、Manus 六宿主隔离安装并导入 0.1.66 通过。PostgreSQL 专项、真实各宿主失效凭证恢复、生产部署和跨设备 Human 验收待确认。
- 2026-09-11 当前生产 **0.1.65 / 06b5066 / 0042_feishu_human_notifications / deployed_https_verified**：单包 stage、切换和 postflight 已通过；公网 health/ready 返回 0.1.65，公开配置发布 wheel SHA-256 `448a92a0d0bab8f098c1a89b43eb979700f3964957abd4739b37f821ede865e4`，Remote MCP 未授权请求返回 401 并声明 OAuth resource metadata。发布时发现配置预检以 `agentpost` 用户读取 root-only 环境文件而失败，自动回退保持 0.1.64 在线；修正发布脚本并重新校验 stage 清单后切换成功。该线上脚本修正和首轮 Codex profile 复用修复见提交 `9404e0d`。测试任务更新 activity `501686ab-2049-43aa-bd31-315a44a8af49` 由原 `mars agent`（Agent ID `91d935c3-1410-4c85-8b56-0b42f4df2da1`）发送；误触发的 codex3 配对已取消且未获批准。真实飞书 aily OAuth/读写闭环、跨设备和 Human 验收仍待确认，因此不是 `production_accepted`。
- 2026-09-10 当前生产 **0.1.64 / a2f04ef / 0042_feishu_human_notifications / deployed_https_verified**：把“飞书 aily 自动执行”和“Human 的飞书消息提醒”拆成两类真实能力。飞书 aily Agent 仍配置自动唤醒；Human 可为自己拥有的 Codex、WorkBuddy、豆包工作等非 aily Agent 配置飞书 Webhook 提醒。提醒载荷只含 task/assignment/run/event/agent ID，明确不代表目标 Agent 已启动、已执行或正在监听；测试成功也不会伪造目标 Agent 的监听与自动唤醒状态。通知通道可不绑定 Connector，原 aily 通道约束保持不变。
- 同一候选修复 020 指出的界面问题：`hidden` 的唤醒表单现在具有最高显示优先级，选择 Codex 不再出现 aily 表单或静默提交；未开放的宿主卡立即禁用并标注“暂未开放”。连接详情将服务端最近收到的监听上报与本地进程事实分开表达。任务文件筛选显示“匹配 N / 共 N”并支持一键清空全部筛选；Markdown 以转义后的安全标题、列表、表格与代码块直接阅读，原始 HTML、脚本和网络内容不会执行。
- 0.1.64 本地证据：514 个非 PostgreSQL 测试通过、2 skipped、7 PostgreSQL deselected；43 项 Orbit JavaScript、8 项 TypeScript Connector、16 项 MCP、4 项 OpenClaw 测试通过；Ruff check/format、JS syntax、TypeScript build 和 diff check 通过。隔离 `http://127.0.0.1:8780` 已实看桌面与 390px：Codex 只显示飞书消息提醒、保存结果有明确反馈，文件匹配/清空和 Markdown 安全阅读通过，页面无横向溢出且控制台 error/warning=0。0.1.64 wheel SHA-256 为 `2c72770354cacedb8b9860dd69ba5a8c3857b9c7fb9f59c92babcc4fac750d3f`。
- 0.1.64 单包 stage、deploy、postflight 均为 ok；切换 44 秒、后检 1 秒，备份 `/opt/agentpost/backups/20260910-144250-a2f04ef-pre-064`。公网 health/ready 返回 0.1.64，公开 wheel SHA-256 与本地发布物一致，未知 wheel 返回 404。后检 agents=77、messages=399、deliveries=265、attachments=45、humans=16；AgentPost PID=526726，Nginx=362620、PostgreSQL=365086 保持原进程。已登录生产任务页刷新后正常加载。
- 针对 020、Dylan、张子良反馈的更新与复测清单已回复到“测试任务”中 020 的飞书 Aily 反馈讨论，activity `26b5f29a-bc16-581c-864e-ca2cfab5378f`。发送成功不等于其他成员已读、ACK、完成 Run 或通过 Human 验收。真实飞书 Webhook 通知、真实 aily OAuth/唤醒、跨设备和 Human 验收仍待确认，因此本版不是 `production_accepted`。
- 2026-09-09 当前生产 **0.1.63 / a874bd7 / 0041_feishu_aily_wake_channels / deployed_https_verified**：单包 stage、deploy、postflight 均为 ok；切换 42 秒、后检 2 秒，备份 `/opt/agentpost/backups/20260909-083408-a874bd7-pre-063`。公网 health/ready 返回 0.1.63，公开 wheel SHA-256 `ac4d8e3ddc33b4e4b72fbdf1d5531355326131f2287cb9c87452b9dea69747f2` 与本地制品一致，未知 wheel 返回 404。后检 agents=76、messages=367、deliveries=243、attachments=37、humans=16；AgentPost PID=503547，Nginx=362620、PostgreSQL=365086 保持原进程。刷新已登录生产页面后，“AI”页可见“飞书 aily 智能体”入口并正常加载。
- 生产尚未取得真实飞书 aily 工作流地址及其获批域名，因此 `host_setup_platforms.feishu_aily=[]`、`host_connection_modes.feishu_aily=unavailable`、协议 `push_wakeup_available=false`；未启用真实 OAuth/webhook 自动唤醒。真实飞书连接、跨设备及 Human 验收仍待确认，本版不是 `production_accepted`。
- 2026-09-09 **0.1.63 飞书 aily 接入候选实现与本地证据**：新增独立“飞书 aily 智能体”入口，以宿主绑定的 Remote MCP OAuth 建立 Agent 身份；Human 在 Agent“当前连接”中配置加密的 HTTPS 唤醒地址与 Bearer Token，页面只回显域名。每个新 Agent Run 与业务事务同时写入 durable wake outbox，后台按租约互斥发送、退避重试并在停用后取消待发；唤醒载荷只含 task/assignment/run/event ID，任务正文仍由 aily 使用 OAuth MCP 读取。Connector 状态区分 MCP 连接、手动可用、自动唤醒测试成功和异常，协议合同仅在飞书功能与 dispatcher 同时启用时声明 push wake。生产启用时强制 HTTPS、加密密钥和工作流域名 allowlist。schema 为 `0041_feishu_aily_wake_channels`；server、Python SDK、MCP、TypeScript Connector、OpenClaw、Codex 插件、锁文件和部署示例已统一为 0.1.63。
- 本切片当前证据：508 个非 PostgreSQL测试通过、2 skipped、7 PostgreSQL deselected；69 项 JavaScript/TypeScript/OpenClaw 测试、16 项 MCP 测试、Ruff check/format、JS syntax 和 diff check 通过。0041 已独立完成 SQLite upgrade/downgrade/upgrade；从空 SQLite 运行全历史迁移仍在旧 0019 约束 ALTER 处失败，属于已知历史 demo 缺口。隔离 `http://127.0.0.1:8779` 已实看 390px：连接详情、两项密钥输入、全宽保存/测试/停用按钮无横向溢出，保存后输入清空且只显示 endpoint host。生产发布状态见上方记录；真实飞书 aily OAuth、真实工作流 webhook、PostgreSQL 并发、桌面与跨设备验收均待确认，仍不得标记 `production_accepted`。
- 2026-09-08 文件与交付桌面布局修复 **local_verified，未部署**：针对生产截图中“工作与结果”左侧空白、文件目录被挤在右侧窄栏的问题，桌面改为工作与结果、文件与交付上下整行排列；文件筛选在宽屏使用四列，文件卡按至少 300px 自动多列排列，列表保留独立滚动。中等宽度筛选为两列，手机仍为单列；文件卡使用等高纵向布局，操作区贴底对齐。本地 Chrome 桌面与 390px 实看通过，41 项 Orbit 导航测试、JS syntax 和 diff check 通过。
- 2026-09-08 当前生产 **0.1.62 / a1f110b / 0040_connector_task_listener_truth / deployed_https_verified**：任务信息分层、全任务文件目录、`get_task(include_assignments=false)`、附件预览对比度与手机文件操作区对齐已上线；版本已同步到 server、Python SDK、MCP、TypeScript Connector、OpenClaw、Codex 插件、锁文件和部署配置。发布包 SHA-256 为 `6b8f8be8a51f31c7e5fc8e7c8816e7fb49c48f7981ab3c3185be8e978702b1a9`，wheel SHA-256 为 `719e73a6bfd806b49d865dce0b43c3b488410bc2330629b2209a2a7cc5e31b3e`。
- 0.1.62 单包 stage、deploy、postflight 均为 ok；切换 41 秒、后检 2 秒，备份 `/opt/agentpost/backups/20260908-214610-a1f110b-pre-062`。公网 health/ready 返回 0.1.62，公开 wheel 哈希一致，未知 wheel 返回 404。后检 agents=76、messages=348、deliveries=227、attachments=37、humans=16；AgentPost PID=495025，Nginx=362620、PostgreSQL=365086 保持原进程。
- 登录后的生产“测试任务”已抽查：“我的 AI”口径、工作与结果/文件与交付/讨论三条主线，以及 10 个任务级附件目录均正常加载。针对 020、张子良、dylan 的逐项说明已发送，activity `b1455067-0980-43de-a1d4-7cf87a217032`；发送成功不等于已读、ACK 或复测通过。真实跨设备、无人值守自动唤醒、重启续做和租约超时重派仍待新证据，因此不是 `production_accepted`。
- 本切片验证：492 个非 PostgreSQL 测试通过、2 skipped、7 PostgreSQL deselected；56 项 JavaScript 测试、Ruff check/format、JS syntax 和 diff check 通过；TypeScript Connector build 与 8 项测试、OpenClaw 4 项现有测试通过。隔离 8778 演示的 1280px/390px 无横向溢出，文件筛选、隔离预览、来源聚焦和筛选状态保留通过，控制台 warning/error=0。OpenClaw TypeScript 完整构建因本机缺少 OpenClaw/typebox 开发依赖未运行成功，本版未改其运行源代码。
- 2026-09-07 当前生产 **0.1.61 / 1138e50 / 0040_connector_task_listener_truth / deployed_https_verified**。0.1.60 后检后用真实 macOS 系统 Python 3.9 运行 bootstrap，复现新版隔离 runtime 因 AgentPost 要求 Python 3.11+ 而安装失败；0.1.61 改为已有 Agent 升级时优先复用当前受支持 runtime 的 Python 创建新环境。本机以系统 Python 启动 bootstrap 后成功安装 Python 3.12.13 / AgentPost 0.1.61 / MCP 2.1.1，并把 Codex MCP 命令切换到 0.1.61；当前对话重启后加载新工具。
- 0.1.61 单包 stage/deploy/postflight 均为 ok，切换 39 秒、后检 2 秒；备份 `/opt/agentpost/backups/20260907-203117-1138e50-pre-061`。公网 health/ready 和发行元数据均为 0.1.61，公开 wheel SHA-256 `1e738f95c032d75ff44b69b3d66352846eb0c50de0c8346e4a76d9b7bf9cc831` 与本地制品一致，未知下载 404。后检 agents=72、messages=293、deliveries=205、attachments=23、humans=16；AgentPost PID=478385，Nginx=362620、PostgreSQL=365086 保持原进程。真实跨设备、其他宿主和 Human 验收仍待确认，因此不是 `production_accepted`。
- “测试任务”已收到今日完整改动与复测清单 activity `a68a8caa-b646-4620-a0e6-8caade3aa182`，并收到最终版本 0.1.61 更正 activity `9cff3290-f57c-4e8a-b28c-b08f5cd04bf5`；发送成功不等于对方已读、ACK 或完成复测。GitHub 远端为 `git@github.com:zlerin-bot/xingyunyi.git`，当前分支 `codex/task-center-v0.1.34`；自动审批拒绝在缺少明确仓库/分支授权时推送整个分支历史，待 Human 明确确认后执行，禁止绕过。
- 0.1.60 过程记录：0.1.59 生产视觉验收发现关闭状态的“任务选项”仍显示内部“暂停任务”按钮。根因是作者样式 `.task-personal-actions { display: grid; }` 覆盖浏览器对关闭 `<details>` 内容的默认隐藏规则；0.1.60 增加显式关闭态隐藏并补回归断言，完成生产切换及后检后被 0.1.61 覆盖。线上 CSS 已确认命中关闭菜单隐藏规则。
- 0.1.59 过程记录：因 0.1.58 已存在较早 SHA 的发布物，本次整合今日 P0、任务讨论与附件预览、未读红点、任务个人管理、好友/成员权限、任务选项视口修复后提升版本，禁止用同版本不同制品覆盖。目标 schema `0040_connector_task_listener_truth`。491 非 PostgreSQL passed、2 skipped、7 PostgreSQL deselected；67 项 JavaScript/TypeScript/OpenClaw 测试、Ruff check/format、TypeScript build 和 diff check 通过。0.1.59 已短暂上线并被 0.1.60、0.1.61 覆盖。
- 2026-09-07 任务头部与恢复入口修复 **local_verified，未部署**：任务头部只保留状态、邀请好友和“任务选项”三个同高控件，暂停/继续任务移入选项；移除浏览器默认黑色 disclosure 三角。选项浮层改用视口坐标动态定位，可用高度不足时向上展开，并限制宽高、提供内部滚动，避免越过屏幕。说明明确为“任务列表顶部 → 已删除”，并新增“打开‘已删除’列表”直达按钮。执行个人删除后自动进入“已删除”并保留当前任务详情，可立即点击“恢复到任务列表”；归档采用同样路径。隔离 Chrome 桌面展开实看通过，筛选直达从“进行中”切换到“已删除”；50 项相关前端测试、1 项页面集成测试、Ruff/format/JS syntax/diff check 通过。生产仍未更新。
- 2026-09-07 0.1.58 P0 反馈切片 **local_verified，未部署**：修复 Dylan 指出的“连接心跳正常但任务长期排队”状态失真。Connector 新增独立任务监听心跳、监听会话和唤醒能力，Human 主界面只显示“可接任务、正在工作、恢复中、需要处理”；连接、监听、唤醒等原始证据放入详情。`agentpost-task-worker` 启动、轮询、停止和异常时上报监听事实；普通连接心跳不会伪造或清除监听状态。当前 Codex worker 的唤醒能力仍为 manual，其他宿主未上报监听前会如实显示“需要处理”。新 schema 为 `0040_connector_task_listener_truth`。
- 同一切片处理 020 的成员和好友反馈：任一 active Task 成员都可把自己已接受的好友直接加入任务，服务端仍以成员关系和发起人的好友关系校验；好友支持按 Human 用户名/ID、Agent 地址/短名称/ID 精确查找。任务页新增“最新动态”直达入口；旧 Thread 页面保持只读且无发送框；任务讨论三层关系、手机扁平布局、分层底纹，以及 Markdown/JSON/HTML 一次点击安全预览也纳入本候选。张子良本轮已读取内容只有安全处理确认，没有可复现的新产品缺陷。
- 验证：491 非 PostgreSQL passed、2 skipped、7 PostgreSQL deselected；67 项 JavaScript/TypeScript/OpenClaw 测试、Ruff check/format、TypeScript compile 和 diff check 通过。新 0040 迁移已在隔离 SQLite upgrade/downgrade 验证。当前机器没有 PostgreSQL CLI/测试 URL，本轮 PostgreSQL 专项待确认。隔离 Chrome 8778 桌面预览无横向溢出；390px 新状态区真机/浏览器尺寸复核待确认。生产仍是 0.1.57 partial，定时任务保持 PAUSED。
- 2026-09-07 0.1.58 导航红点热修复候选：任务未读红点不再作为一级导航网格的第三个子项，而是附着在“任务”标题内；桌面侧栏与手机底栏均不再被红点新增行或撑高。红点仍保留，任务列表内的行内红点语义不变。JS syntax、39 项 Orbit 导航测试及 diff check 通过；生产仍为 0.1.57，待生成不可变发布包并切换。
- 2026-09-07 当前生产 **0.1.57 / 24a3b9a / 0039_task_activity_sequence / partial**：公网 health、ready、auth config、协议合同 0.4、公开 wheel 精确 SHA 与未知下载 404 通过；测试任务更新 activity `7b909c4a-909e-4955-8ba5-389dc6655c52`。首次云端发布命令在完成切换后返回 1，尚未取得服务器进程、备份、日志和关键数据计数的完整 postflight 成功回执，因此不得标记 `deployed_https_verified` 或 `production_accepted`。

- 2026-09-07 0.1.57 发布候选：整合多 AI 派工、AP056 反馈、手机交互、独立 Human 视图、任务活动顺序及可选 Codex worker。用户已授权部署及测试任务更新；正式切换/后检待执行。发布脚本新增迁移/回退前停写与停写后备份；脚本也从指定 commit 快照提取。server/SDK/MCP/插件/锁文件同步 0.1.57，schema0039。486 非 PG passed、2 skipped、7 deselected，46 Orbit/TS tests、Ruff/format/JS syntax 通过。原生及跨设备验收边界继续见 AP056_REMAINING_ACCEPTANCE，定时任务保持 PAUSED。

- 2026-09-07 AP056 继续：新增 `0039_task_activity_sequence`，Task 行锁串行分配发布序号，增量仍使用活动 UUID cursor，按 task_sequence_asc 读取，原始时间不改。原 PostgreSQL 迟提交缺口已在本地 PostgreSQL 17.10 专项验证；历史漏读仍需旧消费者全量重放。未部署，生产仍是 0.1.56/schema0037；切换新 schema 前须停止旧写入。
- 新主动启用的 `agentpost-task-worker` 支持 macOS/Linux Codex 只读 Task 执行，固定指定任务/目录、沿用钥匙串、先握手再领取，真实会话 mapped/woken、结构化结果和幂等回执。真实合成 Task Run 闭环通过，不安装计划、不恢复定时任务；崩溃中断保留 journal 待复核，不能声称整机重启自动续做。其他宿主原生后台执行仍未完成。
- 自动升级：新安装失败目录保留诊断并允许重试，探针核验真实导入版本。六宿主独立环境的真实 wheel 安装/导入通过，但不是六宿主原生升级验收。WorkBuddy 当前旧 profile 在新旧 runtime 均无法从钥匙串读取，原配置未改、未重新配对，原身份迁移待恢复授权。
- 验证：485 非 PostgreSQL passed、2 skipped、7 PostgreSQL deselected；独立 PG 7 passed，真实 native Codex 1 passed；38 Orbit tests、Ruff/format/diff 通过。原 8777 合成库已备份迁移，13 Task/27 Activity/1 Message 不减少，登录保留。详细矩阵、可复现命令及剩余原生/真机/重启门禁见 `docs/AP056_REMAINING_ACCEPTANCE_20260907.md`。四阶段整体仍 partial；agentpost-3 已只读核实 PAUSED。

- 2026-09-07 手机列表与个人任务管理切片 **local_verified，未部署**：取消手机任务/好友列表固定最大高度，使用整页滚动；手机长页提供回到顶部。新增 Task 消息/执行结果红点，前台每 30 秒仅刷新指示，GET 不写已读，实际打开的活动快照用独立 Human 记录标记，迟到消息仍未读。
- 任务选项新增个人归档、从自己列表删除和恢复（不修改共享状态，不停用 AI）；普通成员可退出，撤销本人及所选 AI 权限、取消未结束 Run 并清除租约，负责人禁止直接退出。保留历史署名，支持退出后负责人重新邀请；成员终止复用 declined 状态，以 member_left 活动区分主动退出。按用户最后指示，免打扰功能已全部取消。
- 新 schema `0038_human_task_preferences`，服务端保存按 Human+Task 的个人列表状态与已查看活动 ID。未上线；生产仍为 0.1.56/schema0037，后续部署须迁移。已查看集合逐条累计，超长任务的存储增长与 PostgreSQL 并发性能尚待实测。
- 验证：481 非 PostgreSQL passed、1 loopback skip、5 PostgreSQL deselected；38 Orbit 导航 tests、Ruff/format/JS syntax/diff check 通过；SQLite 新迁移 upgrade/downgrade/upgrade 通过。隔离浏览器 390px 下 13 个任务整页展开、无横向溢出，回顶 scrollY=0，归档/删除/恢复实测；1280px 桌面无溢出，读取后列表/导航红点消除，console warning/error=0。好友使用相同滚动容器修复，真实多好友/真机触屏、跨设备与 PostgreSQL 验收仍待确认。预览保留合成数据库，后台进程由 `/tmp/ap_preview_resume.py` 启动；未部署，定时任务仍 PAUSED。

- 2026-09-07 AP056 反馈开发切片：新增认证握手、Task 历史分页/精确活动读取、可跳过历史的上下文、SDK 截断信息、豆包显式文本工具、Manus Task 操作、附件元数据及自动 SHA、可选 Run 最终回执、负责人取消 queued 工作、代发署名与下载反馈、持久化轮询基础。当前是本地验证，未部署、未更新外部宿主；四阶段尚未全部完成，详见 `docs/AP056_FEEDBACK_IMPLEMENTATION_20260907.md`。
- 本轮验证：478 非 PostgreSQL passed、1 loopback skip、5 PostgreSQL deselected；真实 MCP 9 passed，轮询专项 2 passed；60 JavaScript/TypeScript tests，Ruff/format/JS syntax/TypeScript build/diff check 通过。隔离 IAB 1470px/390px 验证下载反馈、署名、派工、取消、返回列表，无横向溢出；原 8777 服务停止后已重建合成数据，旧预览 task 深链接不再适用。
- 待继续：各宿主真实自动唤醒/升级迁移、PostgreSQL 迟提交与游标并发、Human AI 页完整能力视图、旧入口迁移收敛、结果比较视图；真实豆包/Manus与手机/跨 Human验收待确认。测试任务定时检查仍 PAUSED，不得当作产品监听恢复。

- 2026-09-06 **多选派工切片 local_verified，未部署**：在“安排一项明确工作”按 Human 分组显示复选框，可勾选 1–64 个参与 AI；每个所选 AI 收到同一工作要求，分别建立独立 Assignment/Run/来源活动，进展与结果继续各自追踪。分工由 Human 在要求中写明，不宣称系统自动拆解。
- 新 Human API `POST /api/v1/tasks/{task_id}/assignments/batch` 要求 CSRF 与 Idempotency-Key：校验整批有效成员/所选 AI 后一次事务创建；批次回执绑定 Task、Human、幂等键及规范化请求哈希。相同请求（含顺序变化）不重复创建，更改正文同键 409；保留旧单选 API。未新增 schema。
- 前端草稿仅保存在当前页面内存，按 Task 隔离；空选择/空要求拒绝，提交期间禁改防重入，网络结果未知时保留原内容和幂等键供重试；迟到响应不覆盖另一个任务。手机触控区域至少 44px、复选框 18px，支持键盘勾选与清晰焦点。
- 验证：473 Python passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；最终新增跨 Human/非负责人权限覆盖后 Task 集成测试 10 passed；前端共 52 tests（含 Orbit 导航 37）通过，Ruff check/format、JS syntax、diff check 通过。隔离预览 `http://127.0.0.1:8777/orbit` 已实测桌面 1470px 与手机 390px 双 AI 提交、独立工作记录、返回列表、Tab/Space/Escape、弹窗关闭；无横向溢出或 warning/error。生产仍为下述 0.1.56，不把本地批量派工视为已上线；PostgreSQL 并发和真实 Agent 执行仍待确认。

- 2026-09-06 当前生产 **0.1.56 / e5bef3a / 0037_task_activity_relations / deployed_https_verified**。下方 0.1.56“本地未部署”是历史准备记录，已由本条覆盖。单包 stage/deploy/postflight 全部 ok，切换 38 秒。备份 `/opt/agentpost/backups/20260906-095824-e5bef3a-pre-056`，数据库、附件、配置、旧 wheel、即时回退脚本验证通过。公开 wheel SHA-256 `f6215482b6f14314f3a465d445bf73c53288d2c63a36836d38c8a733d9190fe4` 与本地已测制品一致。
- 后检 agents=67、messages=662、deliveries=626、attachments=57、humans=16，关键数据未减少；AgentPost PID=452464，Nginx=362620、PostgreSQL=365086 保持原进程。schema 未变，副本迁移演练通过；公网/本机 health、ready、制品与下载 404 门禁通过。生产 Chrome 已认证 mars lee 并正常载入测试任务；WorkBuddy 附件下载事件已触发，但未确认落盘文件/SHA。六宿主升级、豆包原生、跨 Human 与 Safari 附件复测仍待确认，非 production_accepted。
- 按 Human 授权已在“测试任务”发布修复及复测说明，activity `9d509bfb-9aac-48bd-936b-e754067e9782`；共享记录已写入、兼容投递 1、未创建额外 Run。已发送不代表 ACK 或复测完成。多选派工不包含在此次生产提交中。

- 2026-09-06 本地候选 **0.1.56 / local_verified（未部署）**：依据 020 AP055 反馈，修复 Task 附件 Human 成员鉴权、Agent 成员失权边界、兼容消息绑定附件前 flush、Run checkpoint 省略保留/显式清空及结果重试哈希；Python/TypeScript SDK 同步省略语义。新增旧连接带附件、Human 下载/陌生人/失权 404 回归。
- MCP 正文去除递归空 schema，心跳附加字段使用明确对象/字符串 schema；stdio 新增附件上传、SHA 校验下载（禁止覆盖）及实际 runtime 查询，远程 MCP 不暴露服务器本地文件工具。CLI --idempotency-key 配合非敏感上传回执复用附件 ID。
- 六宿主配置写入 AGENTPOST_HOST；新版 MCP 启动后后台检查发行（此后每小时），官方 wheel SHA 校验、独立目录、OS 安装锁、导入预检后原子发布版本指针，下次宿主连接自动选用。失败继续旧入口；已有会话不被强杀。每 30 秒报告实际 runtime 心跳。旧版入口首次迁移、宿主工具缓存刷新、自建发行源及独立 TypeScript 插件升级不能假称已自动覆盖，详见 `docs/CONNECTION_SIMPLIFICATION_20260906.md`。
- 本机 Codex 配置已从 0.1.48 迁移到 `/Users/mars113/.agentpost/runtimes/codex/0.1.56-local-f6215482b6f1/bin/agentpost-mcp`，原 profile/凭据与其他配置保留，原配置已在 Codex home 做 0600 备份。新 stdio 进程复用原身份实际握手成功，runtime_status=0.1.56、工具 16 项、get_task 成功读取“测试任务”。当前长期 Codex 对话仍缓存旧工具，下次重连生效；未配对、未发生产消息、未改任务状态。
- 0.1.56 验证：472 Python passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；另 8 项真实 MCP adapter 协议测试通过；63 JavaScript/Connector/OpenClaw tests 通过，TypeScript 编译、Ruff check/format、diff check 通过。候选 wheel SHA-256 `f6215482b6f14314f3a465d445bf73c53288d2c63a36836d38c8a733d9190fe4`，本地制品 `/tmp/agentpost-0.1.56-verified/agentpost-0.1.56-py3-none-any.whl`。schema 不变；未部署、未做 PostgreSQL/六宿主真实升级/豆包原生重连/生产附件复测，仍不是 production_accepted。


- 当前生产：**0.1.55 / a7470ba / 0037_task_activity_relations / deployed_https_verified**（2026-09-05 22:08 +08:00）。字号统一切片已发布，下方“本地待发布”是历史过程记录；仍不是 production_accepted。
- 单包 stage/deploy/postflight 全部 ok，切换 40 秒、后检 2 秒。备份 `/opt/agentpost/backups/20260905-220720-a7470ba-pre-055`；数据库、附件、配置、旧 wheel 和即时回退脚本校验通过。公开 wheel SHA-256 `69ae709df1feccf8036de2591fc1ae4cffb1d9d3bac38ee72da38d1a9677a665`；公网及本机 health/ready、OpenAPI、机器合同、安装合同、未知下载 404 与公开 CSS 字节一致性通过。
- 后检 agents=67、messages=641、deliveries=617、attachments=51、humans=16，关键计数未减少；AgentPost PID=444735，Nginx=362620、PostgreSQL=365086 保持原进程。schema 无变化，副本 upgrade/downgrade/upgrade 保持 0037。
- 发布回归 463 Python passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；63 JavaScript/Connector/OpenClaw passed；Ruff check/format、TypeScript build、diff check 通过。生产新认证 Chrome 实测 PC 1470px/手机 390px 无横向溢出；页面标题 28/24px、板块标题 18px、正文 15px、辅助信息 13px 与设计一致，真实 Markdown/长 SHA 展开仍可读，控制台无 warning/error。未发送生产消息，真实跨设备 Agent 执行及 Human 验收仍待确认。

- 本地待发布字号统一切片（0.1.54 之后）：用共享 rem 字号变量替换历史小数散值；PC/手机页面标题 28/24px，板块 18px、内容标题 16px、正文 15px、操作 14px、辅助信息 13px，状态标签/任务 ID 12px；输入控件 16px。任务、好友、AI、设置与弹窗共用层级，任务进展/记录/折叠板块标题一致，普通正文/进展/阅读卡摘要不再混用 10–16px。长正文卡标题换行、图标顶部对齐，手机卡片缩小头像占位以保留阅读宽度。
- 字号切片验证：51 JavaScript tests、JS syntax、diff check 通过；本地真实计算字号与上述层级一致，桌面 1470px 与手机 390px 无横向溢出；手机任务/好友/AI/设置、创建窗口 Tab/Escape、16px 输入、合成长主机名/64 位哈希/JSON 换行实测通过，控制台无 warning/error。本轮只改 CSS，未重跑 Python/PostgreSQL；未部署此字号切片，当前生产仍是下述 0.1.54。

- 当前生产已更新为 **0.1.54 / 354d82e / 0037_task_activity_relations / deployed_https_verified**（2026-09-05 21:46 +08:00）。本轮 Human 任务导航、进展与讨论阅读改进，以及真实长 AI 名称/SHA/JSON 的手机换行补丁均已上线。下列“本地未发布/发布候选”均为过程记录，已被本条最终状态覆盖；仍不是 production_accepted。
- 0.1.54 单包 stage/deploy/postflight 全部 ok，切换 38 秒、后检 2 秒；备份 `/opt/agentpost/backups/20260905-214549-354d82e-pre-054`，即时回退脚本及数据库/附件/配置/旧 wheel 校验通过。0.1.52 和 0.1.53 恢复资料仍保留。
- 公网及本机 health/ready 正常，公网 OpenAPI 版本 0.1.54；wheel SHA-256 `02ffa6c33a75a75274edb3276d5bf4a801e58f14debfa4589f89e34d19ca3019`，未知下载 404；公开 JS/CSS 与本地提交字节完全一致。后检 agents=67、messages=638、deliveries=614、attachments=51、humans=16，关键计数未减少。AgentPost PID=442441；Nginx=362620、PostgreSQL=365086 保持原进程。
- 最终回归：463 Python passed、1 loopback 沙箱 skip、5 PostgreSQL deselected；63 JavaScript/Connector/OpenClaw passed；Ruff check/format、TypeScript build、JS syntax、diff check 通过。本次 schema 无变化，生产副本执行 upgrade/downgrade/upgrade 均保持 0037；不是新增迁移覆盖。生产新认证页面实看“测试任务”“小孔成像”，桌面 1470px/手机 390px 均无横向溢出，Markdown 展开、真实附件卡、任务切换、手机深链接及返回列表可用，控制台无 warning/error。未发送生产测试消息；跨设备真实 Agent 执行和 Human 最终验收仍待确认。

- 0.1.53 发布过程记录（2026-09-05 21:37 +08:00）：`bd1655f / 0037_task_activity_relations`；stage/deploy/postflight 全部 ok（切换 38 秒、后检 2 秒）。备份 `/opt/agentpost/backups/20260905-213706-bd1655f-pre-053`；wheel SHA `7993c32d611eeab1e7c961c8fffe0cf3455bc86266501fadfbcab2bb8ba582ca`。agents=67、messages=634、deliveries=610、attachments=51、humans=16，关键计数未减少；AgentPost=441013、Nginx=362620、PostgreSQL=365086。公网 health/ready/OpenAPI 与 JS/CSS 字节验证通过；新 Chrome 会话成功进入任务并显示新功能。生产手机实看暴露长内容溢出，由 0.1.54 补丁修复，真实跨设备验收仍待确认。

- 0.1.54 发布候选：0.1.53 已完成部署后检，但生产 390px 实看发现长 AI 主机名及 SHA/JSON 摘要撑宽网格；补充可收缩网格列与任意长文本换行。合成长主机名、64 位哈希及 JSON 窄屏验证 scrollWidth=390，正在复核后发布补丁。

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
- 交接阶段：`0.1.67-deployed-https-verified-feishu-aily-paused`
- 当前本地候选：协作接续切片（2026-09-11），未部署；生产仍为 0.1.67。
- 当前生产：`6b40ebb / 0.1.67 / 0042_feishu_human_notifications / deployed_https_verified`（2026-09-11 完成后检）；保留历史版本即时回退点。
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
