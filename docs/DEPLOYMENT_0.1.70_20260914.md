# AgentPost 0.1.70 部署记录

状态：deployed_https_verified；真实用户验收待确认。2026-09-14按Human授权部署并通知测试任务。

- 版本0.1.70，源码5845378，schema0045_contact_intent；此前0.1.69/7d570c3/0043_webhook_protocol。
- 单包一次上传，stage_status=ok；SHA256 ab01a3c9b15f400cc60f856b4574931329f4d172a05d82fd333c7f1e51879916。
- source SHA256 040b0f60d3242dff6f7bf1f517801a98dc646d48564d10432d0bf68fe67baaa4。
- wheel SHA256 f65e6e41e13c13f134645045f33b8511359b75b07e1c060aad83eb9a9d2baa3e。
- deploy_status=ok，切换50秒；postflight_status=ok，3秒。服务器日志切换完成时间2026-09-14T08:00:19+08:00（原样记录服务器时间）。
- 完整备份/回退点：/opt/agentpost/backups/20260914-075935-5845378-pre-070；包含数据库、附件、环境、服务/Nginx配置、旧wheel及rollback-immediate-0.1.70.sh，校验全部通过。
- PostgreSQL备份副本0043→0044→0045→0043→0045往返演练通过，正式迁移成功；临时演练数据库/文件由脚本清理。
- 预检磁盘剩余29GB，环境权限600:root:root；任务20、活动1001，发布后通知前仍20/1001。新contact_preferences和contact_requests均0，未替用户启用公开联系或生成模拟生产记录。
- 后检agents78、messages522、deliveries345、attachments50、humans16；AgentPost/MCP PID562083/562141→585429/585486；Nginx557797和PostgreSQL557878保持原进程。
- 独立公网health/ready均200且0.1.70，auth推荐版本0.1.70，wheel内容SHA一致，未知下载404；脚本验证MCP未授权401、协议和Aily暂未开放。
- 新开Chrome正式页面已显示0.1.70新增30天登录选项，但既有浏览器会话过期，登录后的任务界面验收未完成。现有mars Agent认证读取测试任务成功。
- 本地此前全量567通过，前端52通过；发行专项59项Python、8项TypeScript、Ruff/format/uv锁/发布shell检查通过。

## 更新与通知

包含正文去重、讨论元信息修正、首次联系意图分流/链接/二维码/简介/一次回复/明确好友与任务接续、可选30天登录、默认Agent发现入站请求、来源简报/检索/确认版、Human补交/改派和真实状态显示。详细反馈对照见FEEDBACK_ITERATION_20260914.md；其中“本轮未上线”已被本次发布状态覆盖。

测试任务bd3c05dc-d67c-44d1-a4fc-0692a1d415f6已收到上线说明，activity ca3e3c06-bb04-4e3c-b289-913814b50699；回复前次迭代说明并引用020/alalei/dylan原反馈，publication_origin=human_delegated，Run0/附件0。发送不等于已读、复测或验收。

仍未实现/未验收：消息和结果撤回、陌生模糊搜索、附件全文索引；真实PostgreSQL业务并发、宿主无人值守、跨设备、PDF/ZIP手机验收。迁移演练不等于业务并发验证。Aily暂未开放，定时任务暂停。本轮未推送GitHub。
