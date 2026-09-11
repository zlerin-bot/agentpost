# 020 Webhook 与连接状态反馈修复

本地实现，未部署；飞书 Aily 直连仍暂未开放，测试任务定时检查仍暂停。

## 已确认的问题与修复

- Webhook 业务失败后，测试接口把审计 outcome 写成 `failed`，违反数据库只允许 `success/denied/failure` 的约束，再次抛出 IntegrityError 并返回 500。本地接口级回归已复现，修正为 `failure`。生产那次异常是否同因仍需核对日志。
- 原发送器仅支持 Bearer，无法使用 020 提供的 X-Webhook HMAC 协议。新增明确的 `bearer/hmac_sha256` 配置；历史配置迁移为 Bearer，不猜测或静默改变签名方式。新表单默认 HMAC，密钥仍使用原加密列存储，不回显。
- HMAC 按 timestamp、nonce、POST、URL path、实际发送字节的 SHA256 五行签名；发送 X-Webhook-Id/Timestamp/Nonce/Signature/Event-Type 与 event_id/event_type/event_time/source/data。不会将内部协议字段发给工作流。
- 测试不再复用全零 UUID；每次明确测试创建新事件，投递重试仍使用既有 Delivery ID。成功、业务拒绝、重复事件与异常响应分开判断，不把 HTTP 200 当成功；拒绝畸形 code，避免未处理 TypeError。`dispatched=false, skipReason=already_processed` 只表示对方已处理该事件，不代表 Human 收到或 Agent 执行。
- 测试接口成功与失败都返回 request_id，实际发起的测试还返回 event_id；限频阻止时没有新的 event_id。保留 delivered 兼容字段（指工作流接受），新增 accepted；界面明确要求核对实际收件结果。

## 额度保护

- Human 发送测试前主动勾选额度确认；每次发送后清除选择。真实费用和余量由飞书决定，AgentPost 不虚构余额。
- Human 通知通道用数据库条件更新预占一分钟发送间隔，测试与后台通知共用；网络请求之前提交，超时不允许立即再次触发。
- 保存通知配置不补发历史 Run，取消该通道旧 pending 提醒；测试成功后才为新 Run 创建通知。未发送或已取消的提醒不改变任务和 Run。
- Human 通知失败不自动重试，通道暂停；发送进程中断两分钟后标记结果不明并暂停，而不是盲目重放。修正配置或核对飞书记录后，可以测试恢复。
- Worker 在外发前原子认领投递，重试不创建新的事件 ID。停用入口保留。
- 本轮未实现按日金额预算、通知合并或飞书计费接口；一分钟限频不是额度总上限。Aily 历史自动唤醒适配器的退避策略保持独立，不能据此称为 Aily 接入成功。

## 连接状态与界面

连接管理和 Agent 详情统一使用 Human 状态文案；红色只对应明确连接异常。当前连接状态取 connection_state，历史 health 上报放进详情并说明不代表当前在线。区分从未上线与曾连接后超时；版本建议只描述版本兼容，不再说“当前连接仍可使用”。

表单支持桌面两列、390px 单列；新增协议选择、44px 输入控件、额度说明与复选框。

## 验证与接续

- 完整非 PostgreSQL 回归及最终数量见 PROJECT_HANDOFF.md；协议模拟覆盖签名字节、事件一致性、去重响应、畸形响应、限频和失败不重试。接口回归覆盖审计失败路径及请求编号。
- SQLite 0043 迁移 upgrade/downgrade/upgrade 已验证。新字段 auth_scheme（旧值 bearer）、last_dispatch_at。8781/8782 合成演示数据库已备份并迁移，原账号和任务保留。
- Chrome 实看 1470px 与 390px，页面无横向溢出，保存合成配置成功；未勾选时阻止测试，控制台无 error/warn。合成配置最后已停用，无实际外部 Webhook 请求。
- PostgreSQL 并发专项、真实飞书通知、跨设备 Human 收件验收、生产日志核对和部署后检待完成。此次不部署、不发送生产消息、不恢复定时任务。
