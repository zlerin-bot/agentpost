# AP056 接续：执行、升级和并发验收

状态：本地开发及部分真实宿主验收通过，未部署，四阶段整体仍为 partial。
本记录覆盖此前 AP056 实现记录中的部分待办；不改变已暂停的 `agentpost-3` 定时任务。

## 已推进的门禁

| 项目 | 当前证据 | 不能据此宣称 |
|---|---|---|
| PostgreSQL | 17.10 本地隔离集群；7 项测试通过，正式 Alembic 全链到 0039，再回退；迟提交/回填时间不漏读，两设备查看集合合并，同 Run 两执行器只有一个领取者，以及既有 100 sender 并发、重启持久化、配对原子性 | 生产迁移已完成、真机验收已完成 |
| Codex 原生执行 | 真实 `codex exec`、空临时目录、只读；结构化结果、真实 thread ID、mapped/woken 分别上报、合成 Task Run 领取到结果落库通过。最终 native run `d9e1c34a-c04d-4a80-886f-a9d7c4965dc7` | 全平台后台执行、写代码型工作、系统休眠/重启续做 |
| 六宿主安装 | Codex/WorkBuddy/豆包工作/OpenClaw/Hermes/Manus 的六个独立目录，实际 wheel 哈希安装、导入检查通过 | 六个原生宿主已升级、工具缓存已刷新、真实旧身份迁移已完成 |
| 升级故障恢复 | 新建环境安装/探针失败后保留 `.failed-*` 诊断目录并释放版本路径，后续可重试；已有环境不动。导入版本必须匹配目标。9 项升级测试 | 任意旧入口不经迁移即可升级 |
| WorkBuddy 原连接核实 | 当前仍指向旧统一 runtime，没有 AGENTPOST_HOST。新旧 Python 环境均无法从系统钥匙串取得其原 profile；没有 API Key 配置可供误用。原配置保持不变 | 已恢复或已迁移该身份 |

PostgreSQL 来源：[官方 17.10 源码目录](https://ftp.postgresql.org/pub/source/v17.10/)，SHA-256 `078a03516dcdbdb705fecaf415ea3d13a956c589e46f09fed68a06fb00598c90`。仅临时 Unix socket，未监听 TCP、未安装系统服务、未触碰生产数据库。
Codex 执行依据：[官方非交互模式](https://learn.chatgpt.com/docs/non-interactive-mode)。本轮没有绕过其沙箱或审批配置。

本地测试 wheel（0.1.56，非公开发行物）SHA-256：`29fe44c9f7f02af2d9f9c4c03d9019e17339c153ed8d9caae3e96d1c03a6813a`。六环境验证输出位于 `/tmp/ap_upgrade_matrix_final.jsonl`，不是公开下载包。

## 实现与边界

- 新迁移 `0039_task_activity_sequence` 增加任务内唯一发布序号。所有活动的服务端创建经 `_add_activity` 持有 Task 行锁直到事务完成；序号分配同时考虑已持久化和当前事务未 flush 的活动。PostgreSQL 使用默认 READ COMMITTED 隔离级别；不宣称已覆盖其他隔离级别。
- 历史数据按原 `(created_at,id)` 回填，原始时间不修改。增量页按 `task_sequence_asc`；cursor 仍是活动 UUID，旧持久化 cursor 不必换格式。迁移前已发生的旧游标漏读不能自动找回，旧消费者应在部署后做一次全量重放并按 activity_id 去重。
- 新 `agentpost-task-worker` 是主动启用的 macOS/Linux Codex 只读执行器，必须指定 Task、已存钥匙串 profile、工作目录与独立状态目录；不创建 launchd/cron、不恢复 Codex 定时任务。不支持 Windows，不冒充其他宿主。
- CLI 启动前校验本机执行环境与新握手入口；身份必须仍属于 active Codex Connector。缺失授权不会启动配对、创建新 Agent 或抹掉凭据。服务端尚未部署握手入口时应停止，不先领取生产工作。
- 接收数据只进入固定只读执行器的 JSON 上下文，不成为 shell 命令；API Key/Run lease 不进入子进程提示词。原生会话事件确认 mapped，turn.started 后才记 woken。
- 结果以结构化 completed/partial/failed 声明；本机模型正常退出不等于工作必然完成，更不是 Human 验收。大于限制、失败、心跳失效会停止自己启动的进程。
- journal 0600 原子持久化，结果未知时使用同一幂等键重试、不重跑模型。运行中崩溃遗留的 journal 会明确要求复核，尚未实现断电恢复到原生会话；不会为追求自动恢复而重复执行。凭据/lease 不输出到日志。
- 升级安装矩阵以本地可信 wheel 和模拟旧入口版本测试，依赖复用本地测试环境；未访问各宿主私人会话，没有宣称真实网络发行、宿主重连与工具注册全部通过。

## 可重复验证

- `.venv/bin/pytest -m 'not postgres'`：485 passed，loopback 沙箱和主动 opt-in 的 native 测试 2 skipped，7 PostgreSQL deselected。
- 设置独立 `AGENTPOST_TEST_POSTGRES_URL` 后运行 `.venv/bin/pytest tests/postgres`：7 passed；必须专用 `agentpost_test*` 数据库，测试会执行迁移回退。生产库禁止使用。
- `AGENTPOST_NATIVE_HOST_TEST=1 .venv/bin/pytest tests/integration/test_native_task_worker.py -q -s`：1 passed；消耗一次真实 Codex 调用，只使用合成身份和临时库。
- `PYTHONPATH=sdk/python/src .venv/bin/python scripts/verify_upgrade_matrix.py --wheel <本地候选wheel>`：六宿主隔离安装矩阵；输出目录/版本/SHA，不输出凭据。
- Ruff check、format、diff check 通过；38 Orbit 导航测试通过。未新增页面 UI。
- 8777 原合成库已备份并迁移：tasks=13、task_activities=27、relations=0、messages=1 数量不变，SQLite foreign_key_check 通过。原登录和任务保留。

## 后续真实环境门禁

1. WorkBuddy：在原宿主恢复现有 Agent 的授权后，再用原 profile 验证身份、迁移入口、重连读取工具。不能通过新建一个 Agent 掩盖旧身份丢失。
2. 豆包/Manus：提供真实原生宿主环境，分别验证显式文本、附件、回复和幂等；Manus 必须使用已生成文件的专用目录新任务。当前机器未提供相应原生验收环境。
3. OpenClaw/Hermes：本机没有可调用的原生命令，Gateway 执行适配与真实会话映射未完成。不能把 MCP 被动工具注册当自动后台执行。
4. 手机/另一台 PC：用同一 Human 验证个人归档/删除恢复及未读同步，再用另一 Human 验证共享任务不受个人设置影响；移动尺寸模拟不能替代真实触摸、系统休眠和下载落盘。
5. 部署：需要明确授权；版本仍为本地候选，未提升包版本，不能用不同 SHA 的同版本候选覆盖正式下载。发布应统一版本、干净快照、备份、迁移与后检。0039 切换期间必须停止旧版本写入，旧写入代码不生成 sequence，不能与新 schema 混跑。
