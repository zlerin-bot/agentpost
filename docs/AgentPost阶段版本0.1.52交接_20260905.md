# AgentPost 阶段版本 0.1.52 交接文档

- 冻结日期：2026-09-05
- 本地阶段标签：`stage-v0.1.52-20260905`
- 功能基线：`bf5d0ee379ef959b2e470e7dd6808cb04d545143`
- 部署证据基线：`f9014bdb94722de48435fe2ee5e7b290de82086b`
- 软件版本：`0.1.52`
- 数据库版本：`0037_task_activity_relations`
- 当前生产状态：`deployed_https_verified`
- 真实用户验收：`待确认`，不是 `production_accepted`

## 1. 阶段结论

0.1.52 已完成代码实现、本地完整非 PostgreSQL 回归、生产 PostgreSQL 迁移往返演练、阿里云受保护切换和独立后检，可以作为下一阶段开发的本地恢复起点。

本阶段解决的核心问题，是在“Task 为唯一多人协作容器”的前提下，把任务讨论、明确工作、AI 执行状态和完整审计记录分开表达，并为回复关系提供明确、可追溯且不改写原始活动的模型。当前证据支持 `deployed_https_verified`；真实 Agent 跨设备闭环和登录后生产体验尚未完成，不得写成生产验收通过。

## 2. 当前唯一产品模型

1. `Task` 是唯一的多人协作容器；每个 Task 只有一个不可变 `task_id` 和一条主 `thread_id`。
2. `TaskMembership` 是 Human 是否属于任务的唯一服务端权威；好友关系只决定是否可识别和邀请，不授予任务内容权限。
3. 每位 Human 至少拥有一个 Agent；Human 可按任务选择一个或多个自有 Agent，并指定主要 Agent，未显式选择时使用默认 Agent。
4. Task 内已选或默认 Agent 可以读取共享上下文并参与协作；需要可靠执行时创建明确 Assignment/Run，由队列、租约、心跳、重试和幂等控制。
5. 新 Agent 消息必须携带任务上下文。无 `task_id` 的客户端一对一新消息由服务端以 `task_context_required` 拒绝；旧连接只保留 Task bridge 的读取、回复和 ACK 兼容。
6. Delivery、Agent read、ACK、Run、Agent Result、Task submission 和 Human acceptance 是独立事实，不能互相替代。

权威规则见 `AGENTS.md` 和 `docs/TASK_CORE_MODEL.md`。

## 3. 0.1.52 完成内容

### 3.1 讨论关系

- 新增 `task_activity_relations`，用 Human 确认的关系描述历史活动之间的回复关联，不修改原始 `TaskActivity`。
- 新版 Task 消息继续使用显式 `reply_to_activity_id` 和引用关系。
- 旧 Connector 回复通过经过验证的 Task bridge 元数据确定性还原；不能确定的历史 Agent 消息只向任务负责人提供确认或排除建议，不按正文、发送者或时间邻近猜测。
- 服务端验证父子活动属于同一 Task、父活动不晚于子活动、子活动类型有效，并保留确认 Human 和审计记录。

### 3.2 Human 当前进展

- “AI 当前进展”只承载明确工作、结果摘要和近期协作更新；租约、领取、唤醒、心跳等执行技术状态单独折叠展示。
- 当前进展以 Human 为主体，Agent 为辅助身份；发起 Human、责任 Human、执行 Agent 分开显示。
- `participant_start` 不再伪装成业务成果；同一 Human、同一 Agent 的重复参与 Run 合并展示。
- 长内容和 Markdown、JSON、HTML 等结构化内容继续以安全附件或完整任务记录承载。

### 3.3 任务记录

- 默认提供“讨论”“工作与结果”“系统记录”“全部”四类视图，避免所有事件混成一条长流。
- 支持按需加载最多 2,000 条活动，并自动补齐当前窗口之外的回复根节点。
- 回复串只根据明确关系组织；历史不确定关系不会被静默改写。

## 4. 代码检查结论

本次重新检查 `bf5d0ee` 功能提交和 `f9014bd` 部署证据提交，未发现阻断建立阶段版本的问题。

- 权限：Task 读取继续以有效 `TaskMembership` 和 Agent 参与关系为边界；Human 确认回复关系仅限任务负责人。
- 数据完整性：关系表保留父、子活动和确认 Human 外键，原始 TaskActivity 不被覆盖；生产迁移可往返。
- 兼容性：旧 Task bridge 回复可以还原，新客户端字段保持可选；无任务私信没有被兼容逻辑重新放开。
- 前端安全：外部 Agent 内容继续按安全文本或附件卡处理，未新增 HTML 执行路径。
- 性能边界：任务列表不加载活动；任务详情默认 200 条、最大 2,000 条，并只补取实际引用到的根活动。
- 版本一致性：server、Python SDK、MCP、TypeScript Connector、OpenClaw、插件基础版本、锁文件和生产配置均指向 0.1.52。
- 敏感信息：已跟踪文件的私钥和常见云访问密钥签名扫描未发现命中；真实凭证仍不得进入仓库和交接文档。

## 5. 本次重新验证

| 门禁 | 结果 |
|---|---|
| Ruff check | 通过 |
| Ruff format check | 260 files 通过 |
| Python non-PostgreSQL suite | 463 passed，1 个 loopback 沙箱 skip，5 个 PostgreSQL deselected |
| Orbit JavaScript | 36 passed |
| TypeScript Connector | 8 passed |
| TypeScript compile | 通过 |
| OpenClaw adapter | 4 passed |
| Alembic graph | 单 head：`0037_task_activity_relations` |
| `git diff --check` | 通过 |
| 已跟踪敏感签名扫描 | 通过 |
| PostgreSQL 0036→0037→0036→0037 | 生产发布保护流程中通过 |

本地没有重新运行 PostgreSQL 专项测试；对应 schema 的 PostgreSQL 往返演练和正式迁移已经在 0.1.52 受保护发布流程中通过。历史 SQLite 从零迁移仍受 0019 constraint ALTER 缺口影响，这不是 0037 新增回归。

## 6. 构件与生产证据

- 源码包 SHA-256：`987b68b10a2fc5323a76ae84c26e65d85bf054fb6bba39e229fb7b693d23f064`
- Connector wheel SHA-256：`4f026d63b7298ba1dc6269d38cf99a406bf748787e9bf48a52cdf1c917d312e6`
- Workbench 单上传包 SHA-256：`a07ab15b3ee593eedd2ce1cdf23b0344180061149de112dd5692fcabc584850e`
- 生产备份：`/opt/agentpost/backups/20260905-171930-bf5d0ee-pre-052`
- 发布结果：`stage_status=ok`、`deploy_status=ok`、`postflight_status=ok`
- 公网 health、ready、OpenAPI：0.1.52
- 未知 wheel：HTTP 404
- 生产后检计数：67 Agents、630 Messages、606 Deliveries、51 Attachments、16 Humans；关键计数未减少。

上述信息是部署后检证据，不等同于真实用户跨设备验收。

## 7. 未完成与下一阶段优先级

### P0：真实链路验收

1. 登录生产 Human 页面，使用“小孔成像”中的真实历史数据确认旧版 Zoe 回复能够归入正确讨论；不得直接修改原始生产活动。
2. 验证 Human 回答 `waiting_human` 后，目标 Agent 能重新领取同一 Assignment 的后继 Run、继续执行并回写结果。
3. 验证普通 Inbox 为空时，Task Run 仍能被 Connector 发现、映射并唤醒唯一任务会话。
4. 验证任务内多 Human、多 Agent、重连、幂等重放和租约超时场景不会重复执行或重复提交。

### P1：真实界面验收

1. 登录后检查讨论串、关系确认、“AI 当前进展”和“任务记录”在桌面与 390px 下的实际显示。
2. 检查真实 Markdown、JSON、HTML 和普通文件附件卡的打开、下载及安全隔离。
3. 检查 Connector 已安装版本、配置目标、实际加载版本和重连提示的一致性。

完成上述真实跨设备门禁前，阶段状态保持 `deployed_https_verified / production_accepted=false`。

## 8. 本地恢复方式

```bash
git switch -c codex/recovery-v0.1.52 stage-v0.1.52-20260905
```

标签指向包含本交接文档和阶段清单的本地冻结提交。若只需核对生产功能源码，可直接查看 `bf5d0ee`；若需核对发布证据，可查看 `f9014bd`。

## 9. 工作区保护

建立阶段版本时，下列既有未跟踪文件不属于 AgentPost 0.1.52 阶段，不删除、不修改、不暂存：

- `docs/xingyunyi-management-summary-20260828-20260831.html`
- `docs/星云驿管理工作汇报汇总.md`

后续开发应继续采用小切片提交，不在阶段标签上直接改写历史；需要新功能时从该标签创建恢复或开发分支。
