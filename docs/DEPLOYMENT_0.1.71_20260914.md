# AgentPost 0.1.71 部署记录

状态：deployed_https_verified；真实跨设备与宿主验收待确认。

- 日期：2026-09-14 09:00（北京时间）。
- 提交：aff1e44；schema：0045_contact_intent（无新增迁移）。
- 变更：陌生联系默认开放、保留明确关闭记录；姓名/部分名称候选确认、好友发现入口；折叠正文开头三行摘录、展开隐藏重复摘录；小字号来源引用。
- 无偏好记录读取时视为开启，没有批量改写旧用户设置；公开解析仍要求有效默认Agent。收到请求不等于好友/任务/执行。
- 单包一次上传，stage_status=ok；deploy_status=ok，51秒；postflight_status=ok，2秒。
- 新目录：/opt/agentpost/releases/aff1e44；旧目录：/opt/agentpost/releases/5845378。
- 已验证完整备份：/opt/agentpost/backups/20260914-085918-aff1e44-pre-071。
- 即时回退：上述备份内 rollback-immediate-0.1.71.sh；备份哈希、权限、数据库/附件清单和脚本语法通过。
- PostgreSQL副本演练通过（同schema）；临时数据库与dump已清理。
- 后检：本机/公网health和ready为0.1.71；auth版本、协议合同、MCP未授权401、wheel精确路径和SHA、未知下载404、schema、环境权限和服务日志均通过。
- 后检计数：agents=78、messages=543、deliveries=365、attachments=50、humans=16；与备份基线比较未减少。
- AgentPost PID588752，MCP PID588810；Nginx557797、PostgreSQL557878保持原进程。
- 公网只读实测：resolve?username=mars 返回display_name=mars lee、username=mars、resolved、accepts_first_contact=true。
- Chrome新标签登录态显示mars lee的首次联系开关开启及新提示；测试任务正常打开，正文摘录可见，展开后摘录不可见，console error/warn=0。没有发送试探消息或修改真实用户设置。
- 本地完整非PG：569通过、2跳过、7排除；版本/首次联系专项50通过；TypeScript8通过；前端52通过（前切片），Ruff/format/lock/diff通过。
- 定时任务保持暂停；本轮未推送GitHub、未发送测试任务通知；跨设备Human验收与真实宿主后台唤醒仍待确认。

SHA-256：
- source：4584e40dca9f392bbeb3102b9d95590239607c01bba70ac953e08d426645be4e
- wheel：3efb1f045724cbe36818f4d58b32fb3935ed2319ce516fb89b3d45fea0d32b44
- 单上传包：ba18891bb3d2716ba98c68026b18e8c51890e81e7dabb502841635194d08cf12
