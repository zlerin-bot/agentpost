# AgentPost 项目交接文档

## 当前接续摘要

- 交接阶段：`v0.1.44-targeted-runs-and-task-attachments-deployed`
- 本地版本：`0.1.44 / 0034_task_run_routing`
- 当前生产：`6609837 / 0.1.44 / 0034_task_run_routing / deployed_https_verified`
- 生产接受状态：不是 `production_accepted`
- 本切片：Run 定向路由、可靠唤醒证据、任务附件和进展去重，已部署并完成 HTTPS 后检

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
- Run 新增待执行预览与按 `task_id` / `assignment_id` 定向认领，返回来源、目标、回复范围、优先级和唤醒阶段。
- Connector 可通过 Run heartbeat 回报本地会话 ID、已映射和已唤醒；这些状态不再由服务端猜测。
- Run result 支持独立幂等键；相同键同载荷安全重放，不同载荷返回冲突。旧 Connector 不带该头仍可继续使用。
- Task 消息支持附件，并保持 TaskMembership / TaskAgentParticipant 权限边界；Human 任务记录按附件卡展示。
- 初始参与和任务消息结果不再派生递归 `result_sync`；Human 要求修改使用独立、可见的 `revision` Run。
- Human 进展界面过滤历史同步噪声，按 Human 展示执行依据、优先级和真实唤醒阶段。
- 协议合同升级为 0.3；包、SDK、MCP、TypeScript Connector 和插件统一为 0.1.44；新增 0034 迁移。

## 本地验证证据

- `.venv/bin/ruff check .`：通过。
- `.venv/bin/ruff format --check .`：通过。
- Orbit 与 TypeScript JavaScript：40 passed。
- `.venv/bin/pytest -m "not postgres" -q`：452 passed、1 expected skip、5 deselected。
- 旧目录/频道关键字扫描：运行时 `src`、SDK、MCP、OpenClaw、插件和 Skill 无旧能力残留；迁移与反向门禁测试中保留必要名称。
- 隔离演示种子已改为 Task API，不再依赖旧多人容器；认证后的桌面端与 390px 任务列表/详情均通过，页面无横向溢出，控制台无 warning/error。
- 认证后的桌面和 390px 任务列表/详情无横向溢出、无 console error；Run 路由/唤醒标签与任务 ID 复制入口可见。真实任务附件卡因隔离种子没有物理附件，API/DOM 已覆盖但认证视觉验收仍为 `待确认`。
- SQLite 从零迁移仍在历史 0019 的 constraint ALTER 处失败，尚未执行到 0034；这是既有边界，不是 0034 的验证证据。

## 待完成

1. 完成真实任务附件卡和连接详情的认证视觉验收。
2. 完成真实用户跨设备验收；此前保持 `deployed_https_verified`，不得标记为 `production_accepted`。
3. 不要纳入两个无关的未跟踪管理汇报文件。

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
