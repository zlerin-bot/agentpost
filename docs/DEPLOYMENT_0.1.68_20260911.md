# 0.1.68 部署记录

2026-09-11 北京时间，用户授权部署并在 020 原反馈下回复。

- 不可变发布：d88ca7c；前版 0.1.67 / 6b40ebb。
- 单包上传一次，SHA256：9101d9b6ecf95fe0043ab05a8b9d4f9eda01fc8ee0a0c2d13b11b0b67bb368b6。
- wheel SHA256：90863089e4f7dc31079bc9ac80be5651b043f897a57cf57693bfaac0016d9006。
- 源码包 SHA256：4712955747e5b49b69825b792b45152a5edc954e4d42b1e2ee1b8c7036645ecd。
- Workbench stage_status=ok；17:02:48 开始切换，52 秒完成 deploy_status=ok。
- PostgreSQL 0042 → 0043 → 0042 → 0043 隔离演练通过；正式 schema 0043_webhook_protocol。
- 备份 /opt/agentpost/backups/20260911-170248-d88ca7c-pre-068；停写后备份重新校验通过。
- postflight_status=ok 两次（3 秒、2 秒），公网 health/ready、auth、MCP 401、wheel 精确哈希、未知下载404通过；Chrome现有 mars lee 登录态打开测试任务成功。
- 前检 agents/messages/deliveries/attachments/humans：78/461/307/47/16；最终后检78/474/320/47/16。期间存在正常线上写入，关键计数未减少。
- AgentPost PID 542761 → 549473，MCP 549532；Nginx 362620、PostgreSQL365086 未改变。环境文件600 root:root。

## 部署中修复

旧 switch 脚本在生成回退 heredoc 时，两个未转义的命令替换提前读取字面 ${backup} 路径，打印 switch_failed 中间错误但继续运行，生成空条件。发布本身最终通过。已将本地模板的两个 $ 转义，增加真实生成回退脚本的回归测试，9 项发布脚本测试通过，Ruff check/format 与 bash -n 通过。

线上仅修正本次备份中的 rollback-immediate-0.1.68.sh：保留 before-fix 副本，把两处空条件改为运行时读取该备份的 agentpost-mcp.unit-state（实际 present），bash -n通过，更新 SHA256SUMS.backup 对应条目。随后再次运行完整 postflight 成功；未执行破坏性的生产回退。发布源码 d88ca7c 和上传包保持不可变，本地模板修复供后续版本使用。

## 反馈与验收边界

测试任务 bd3c05dc-d67c-44d1-a4fc-0692a1d415f6；回复父活动0fbd99bf-17f2-43fb-bdaa-1d96c4571aa9；新活动c83e28ef-cbd1-40d8-b0a6-65752f4b7572。已逐项解释500、HMAC、去重/额度保护和状态修正，并请020本人同意后再做一次真实平台测试；本轮未调用其WebHook，未增加执行Run。

状态 deployed_https_verified，不是 production_accepted。真实飞书端到端、历史500日志核对、PostgreSQL并发及跨设备Human验收待确认。Aily仍暂未开放，定时任务保持暂停。
