# AgentPost 0.1.69 部署记录

2026-09-12，按 Human 授权部署并通知测试任务。生产切换与技术后检通过；GitHub 推送被自动审批拒绝，待明确目的地授权。登录态失效，正式登录后 UI 与跨设备验收待确认，不标记 production_accepted。

## 版本与证据

- release：0.1.69；源码提交：7d570c3；schema：0043_webhook_protocol。
- source SHA256：f4787cdb1a1e89f3d7f8e6e533e61e2b06ee33c1dd0c8818f81992ebf20a07b9。
- wheel SHA256：75b0dc19761c0693e8ea2db2b35871ad56e894936e42a3ca2a36eef8b29c6df2。
- 单上传包 SHA256：a80afc5b3616f175ec74b2453f80620cd9aa8e0cc1af7d18b0e4f29557621223。只上传一次，stage_status=ok。
- 10:18 北京时间切换成功：deploy_status=ok，耗时66秒；postflight_status=ok，耗时2秒。
- 备份：/opt/agentpost/backups/20260912-101711-7d570c3-pre-069；包含数据库、附件、配置、服务文件、旧wheel及校验通过的 rollback-immediate-0.1.69.sh。
- 发布前0.1.68/d88ca7c；磁盘29GB可用，环境权限600:root:root。AgentPost/MCP PID 557967/557968 → 562083/562141；Nginx557797和PostgreSQL557878未变。
- 后检数据：agents78、messages492、deliveries331、attachments48、humans16。迁移演练、备份校验及Nginx语法通过。
- 独立公网 health/ready 200且0.1.69；公开wheel200且摘要一致；不存在下载404。服务端postflight还验证auth配置与MCP鉴权边界。
- Ubuntu antiword安装成功，仅安装该组件，NEEDRESTART_MODE=l避免重启其他服务；生产venv通过合成tests/fixtures/word-preview.doc检查：linux_doc_preview=ok chinese_text=ok。
- 本地552 passed、2 skipped、7 PostgreSQL deselected；50前端测试通过；Ruff检查/格式、diff检查通过。原两个功能切片的桌面/390px验证见交接和FILE_PREVIEW_20260912.md。

## 本次更新

最新协作与明确派工分层；DOCX/DOC站内阅读；Word/PDF类型兜底及预览下载对比度。Word图片、批注、复杂原版排版不支持，ZIP仍仅目录。

## 通知与未完成项

- 测试任务bd3c05dc-d67c-44d1-a4fc-0692a1d415f6，更新activity a16230e4-ad7c-46d2-96ef-1e2d87e1fefc，queued_run_count=0。说明修改、复测建议及上述限制，不等于已读或验收。
- GitHub既有目的地git@github.com:zlerin-bot/xingyunyi.git，分支codex/task-center-v0.1.34；自动审批两次拒绝，认为缺少Human对具体目的地归属的确认。未绕过、未推送。
- 新开正式站点页面显示登录表单，现有会话过期；登录后UI验收待Human登录。
- PostgreSQL并发、真实跨设备/跨宿主无人值守与Human验收仍待确认。Aily暂未开放，定时任务保持暂停。
