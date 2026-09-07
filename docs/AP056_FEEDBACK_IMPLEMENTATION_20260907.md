# AP056 反馈迭代实现记录（2026-09-07）

本轮是本地开发，不部署、不恢复已暂停的测试任务定时检查。生产记录仍为 0.1.56/e5bef3a。已有多 AI 批量派工提交 20603bb 保留。

## 已实现

1. 任务读取：`GET /api/v1/agent/handshake` 返回认证身份、服务版本、当前连接报告和最多 50 个有权参与的任务摘要（截断显式标注）。`get_task(include_history=false)` 可跳过历史；SDK 保留 activity_total、activities_truncated 和排序说明。
2. `GET /api/v1/agent/tasks/{task_id}/activities` 使用 `(created_at,id)` 升序键集分页，最多 100 条；next_cursor 是最后一个主窗口活动 ID，空页保留原 cursor。精确活动接口独立读取父记录，不把回填父记录塞进分页。旧详情回填后按时间与 ID 稳定倒序。分页读取不装载全部 Assignment/Run。
3. SDK/Python、TypeScript 和 MCP 增加握手、增量与精确读取入口；机器合同同步入口信息。旧 Thread 兼容接口未删除。
4. MCP `agentpost_send_task_text` 使用显式 string/array 参数，复用原任务发送服务；包含附件、回复、引用和幂等。参数 schema 和真实 MCP 调用链已回归；真实豆包原生复测仍待进行。
5. Manus 文件夹适配器增加 resolve/get/activities/pending/精确 claim/heartbeat/complete。保留 JSON stdin、原身份和 checkpoint 省略语义；只允许带 task_id 和 assignment_id 精确领取。既有已安装文件夹尚需按原身份更新，未自动修改外部宿主。
6. runtime_status 提供实际适配器版本、进程存活时长、已加载工具、schema SHA、后台发行检查时间及脱敏原因。发行检查前清除过期 target，避免沿用旧升级目标。仍需宿主重连才能采用已准备环境；不声称工具缓存自动热刷新。
7. 附件元数据接口复用相同权限边界；MCP 下载不提供 SHA 时先读权威元数据，再校验下载，始终禁止覆盖。已有目标、权限、SHA 不匹配等返回稳定错误码。
8. Run heartbeat 返回真实 status。结果提交支持 `Prefer: return=representation`，返回最终状态、checkpoint、result_activity_id、replayed；旧 204 语义保留。Python/MCP 使用新回执，旧服务器回执缺失明确标注。
9. Human 负责人可取消 queued 工作，CSRF 和服务端成员/负责人校验，重复取消不重复活动。已领取/执行工作返回冲突，不强杀宿主。修复 Human 与 Agent 同时存在时丢失实际 Agent 名称的投影。
10. 网页附件下载显示获取中、失败、交由浏览器保存，不声称已落盘；检查大小及可用 SHA。取消活动归入工作记录。
11. `TaskPoller` 提供宿主管理的有限页轮询、按任务持久化 cursor、断线指数退避及可中止循环。处理成功后原子保存游标；失败保留旧游标。消费者须以 activity_id 幂等，崩溃恢复可能重放；不声称 exactly-once。

## 验证

- 全量非 PostgreSQL：478 passed、1 loopback 沙箱 skip、5 PostgreSQL deselected（最终仅新增轮询退避测试另行通过）。
- 真实 MCP 协议测试 9 passed；轮询恢复/身份隔离/指数退避 2 passed。
- 前端与 TypeScript 测试共 60 passed，其中 Orbit 导航 37；TypeScript build、JS syntax、Ruff check/format、git diff --check 通过。
- IAB 隔离预览验证：登录、实际附件请求及保存提示、代发署名、勾选派工、排队取消后未结束数下降、390px 返回列表、键盘 Space、1470px/390px 无横向溢出。控制台无 warning/error（曾因重建隔离数据访问旧 task 深链接出现正常 404，切换新任务后正常）。
- 测试账号和附件是临时合成数据；未发送生产任务消息。

## 未完成门禁与剩余开发

- 本轮不是四阶段全部交付。没有真实豆包、Manus 原生安装迁移/升级/调用验收，没有 PostgreSQL 并发验证，没有生产部署或跨 Human/真实手机验收。
- 第四步只有通用轮询基础：各宿主 Gateway 的实际唤醒、会话映射、租约执行、系统休眠与整机重启续做尚未接入并验证；自动能力继续显示未验证。不得恢复本任务已暂停的定时检查代替产品机制。
- 键集游标覆盖已提交的稳定时间顺序；迟提交且 created_at 早于游标的并发事务仍需 PostgreSQL 专项设计验证，不能据 SQLite 测试承诺并发无漏读。
- 大任务摘要仍包含成员和 Assignment 状态；进一步压缩工作摘要、任务列表分页和跨任务批量订阅仍需后续切片。
- 实际运行/已安装/宿主缓存版本尚未全部汇聚到 Human AI 页面；runtime 诊断提供本地证据，不冒充服务端已上报工具清单。
- 多 AI 独立派工已有本地切片，结果比较视图、运行中工作安全取消需独立设计。当前只取消未执行 queued 工作。
- 未删除旧连接。旧 Thread 标注/迁移、旧入口迁移覆盖统计、宿主授权确认与配置收敛仍需独立切片；不把尚未实现的清理建议写成完成。

## 后续复测建议

优先豆包纯文本/附件/回复/幂等四项与 Manus 官方文件夹任务闭环，再对实际 Human 页面检查排队取消与附件。既有附件 SHA 和恢复证据可复用。以活动 ID、运行版本及原始错误核对，不把数量差异直接当漏读比例，也不把本机 MCP 上传失败归因于所有宿主。
