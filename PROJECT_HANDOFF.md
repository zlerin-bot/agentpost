# AgentPost 项目交接文档

## 当前接续摘要

- 交接阶段：`v0.1.43-task-state-and-runtime-truth-local-verified`
- 本地版本：`0.1.43 / 0033_connector_runtime_truth`
- 当前生产：`422c5cc / 0.1.40 / 0030_task_messages / deployed_https_verified`
- 生产接受状态：不是 `production_accepted`
- 本切片：P0 状态语义、Connector 运行真相和协议参数一致性，尚未部署

## 当前产品模型

AgentPost 的多人协作只发生在 Task 内。每个 Task 有一个稳定 `task_id` 和一条主 `thread_id`；Human 是否能
进入任务只由 `TaskMembership` 决定。Human 为任务选择自有 Agent，未选择时使用默认 Agent。任务内 Agent
均可读取上下文并参与，具体执行通过 Agent Run 的队列、租约、心跳和幂等完成机制协调。Human 验收与消息
送达、Agent read、ACK、Run 完成和 Agent Result 分别保存。

好友是双向 Human 关系，只用于识别和任务邀请。私信是一对一传输与旧 Connector 兼容能力，不是共享协作
范围。任何后续多人能力必须扩展 Task，不能再建立平行容器、另一套成员角色或共享通信规则。

权威设计见 `docs/TASK_CORE_MODEL.md`；未来开发约束见 `AGENTS.md`。

## 本切片已经完成

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

## 本地验证证据

- `.venv/bin/ruff check .`：通过。
- `.venv/bin/ruff format --check .`：通过。
- Orbit 与 TypeScript JavaScript：39 passed。
- `.venv/bin/pytest -m "not postgres" -q`：451 passed、1 expected skip、5 deselected。
- 旧目录/频道关键字扫描：运行时 `src`、SDK、MCP、OpenClaw、插件和 Skill 无旧能力残留；迁移与反向门禁测试中保留必要名称。
- 隔离演示种子已改为 Task API，不再依赖旧多人容器；认证后的桌面端与 390px 任务列表/详情均通过，页面无横向溢出，控制台无 warning/error。
- 公共桌面和 390px 页面壳层无横向溢出、无 console error；认证后的新状态条和连接详情视觉验收仍为 `待确认`，API/DOM 合同测试已通过。
- SQLite 从零迁移仍在历史 0019 的 constraint ALTER 处失败，尚未执行到 0033；这是既有边界，不是 0033 的验证证据。

## 待完成

1. 在隔离 PostgreSQL 上验证 0031 → 0032 → 0033 → 0032 → 0033，确认 0033 可逆且不改变既有关系。
2. 检查迁移前后 Task、TaskMembership、Friendship、Agent、Connector、Message、Attachment 的数量与关键关系。
3. 完成认证后的桌面与 390px 新状态条、连接详情视觉验收。
4. 复核 diff、提交当前切片；不要纳入两个无关的未跟踪管理汇报文件。
5. 只有用户明确要求部署后，才按 `docs/ALIYUN_DEPLOYMENT_EFFICIENCY.md` 执行发布。

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
