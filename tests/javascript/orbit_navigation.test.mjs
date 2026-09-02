import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const [html, script, stylesheet] = await Promise.all([
  readFile(resolve(repositoryRoot, "src/agentpost/orbit_ui/index.html"), "utf8"),
  readFile(resolve(repositoryRoot, "src/agentpost/orbit_ui/app.js"), "utf8"),
  readFile(resolve(repositoryRoot, "src/agentpost/orbit_ui/styles.css"), "utf8"),
]);

test("AgentPost exposes exactly task, friends, AI, and settings", () => {
  const primaryNavigation = html.slice(
    html.indexOf('id="primary-navigation"'),
    html.indexOf("</nav>", html.indexOf('id="primary-navigation"')),
  );
  const modules = [...primaryNavigation.matchAll(/data-module="([^"]+)"/g)]
    .map((match) => match[1]);

  assert.deepEqual(modules, ["projects", "friends", "relay", "settings"]);
  assert.match(primaryNavigation, />任务</);
  assert.match(primaryNavigation, />好友</);
  assert.match(primaryNavigation, />AI</);
  assert.match(primaryNavigation, />设置</);
  assert.match(primaryNavigation, /Human 与 AI 协作/);
  assert.match(primaryNavigation, /联系人与协作邀请/);
  assert.match(primaryNavigation, /身份与连接/);
  assert.match(primaryNavigation, /账户与平台/);
});

test("tasks and formal friends are separate API-backed collaboration modules", () => {
  assert.match(html, /data-module="projects" data-section="board"/);
  assert.match(html, /data-module="friends" data-section="directory"/);
  assert.match(script, /一个任务对应一条 Thread/);
  assert.match(script, /好友必须双向确认/);
  assert.match(script, /\/api\/v1\/tasks/);
  assert.match(script, /\/api\/v1\/friends/);
  assert.match(script, /\/api\/v1\/friend-requests/);
  assert.match(script, /initializeCollaborationModules\(\)/);
  assert.match(script, /human_user_ids: selected/);
  assert.match(script, /input\.type = "checkbox"/);
  assert.match(script, /createProject/);
  assert.match(script, /activateRoute\("projects", "board"/);
  assert.match(script, /activateRoute\("friends", "directory"/);
  assert.doesNotMatch(`${html}\n${script}`, /本地体验|本地演示|交互原型|不连接生产|演示项目/);
  assert.doesNotMatch(html, /id="project-create-friend"|首位协作好友/);
  assert.match(html, /Human 协作状态/);
  assert.match(html, /AI 当前进展/);
  assert.match(html, /完整过程/);
  assert.match(html, /任务记录/);
  assert.match(html, /选择参与的 AI（至少一个）/);
  assert.doesNotMatch(script, /DEMO_FRIENDS|demoProjects|confirmDemoAcceptance|inviteDemoFriend/);
  assert.doesNotMatch(`${html}\n${script}`, /李月|张冠群|崔孝林|胡曦元|zhangziliang|panyongtong/);
});

test("task progress is Human-first and structured content stays collapsed as a safe attachment", () => {
  assert.match(script, /assignment\.responsible_human_display_name/);
  assert.match(script, /使用 AI：/);
  assert.match(script, /activity\.actor_display_name/);
  assert.match(script, /通过 AI：/);
  assert.match(script, /createTaskActivityAttachment/);
  assert.match(script, /\["markdown", "json", "html"\]\.includes\(format\)/);
  assert.match(script, /document\.createElement\("details"\)/);
  assert.match(script, /preview\.textContent/);
  assert.doesNotMatch(script, /task-activity-attachment-preview[\s\S]{0,500}innerHTML/);
  assert.match(stylesheet, /\.task-activity-attachment/);
  assert.match(stylesheet, /\.project-activity-avatar/);
});

test("friends use one clear hierarchy and explicit relationship states", () => {
  const friendNavigation = html.match(/<div data-context-module="friends" hidden>([\s\S]*?)<\/div>/)?.[1] || "";
  assert.doesNotMatch(friendNavigation, /我的好友/);
  assert.doesNotMatch(html, /个人通讯录|协作好友/);
  assert.match(html, /data-friend-filter="accepted"[^>]*>好友</);
  assert.match(html, /data-friend-filter="pending"[^>]*>待确认</);
  assert.match(html, /data-friend-filter="suggested"[^>]*>联系过的人</);
  assert.match(script, /accepted: "已成为好友"/);
  assert.match(script, /pending_incoming: "待你确认"/);
  assert.match(script, /badge: friendRelationLabel\(friend\)/);
  assert.doesNotMatch(script, /badge: dateOnlyText\(friend\.last_contact_at\)/);
});

test("connection management separates first pairing from reported runtime version", () => {
  assert.match(script, /\["实际运行版本", connector\.runtime_version \|\| "未上报"\]/);
  assert.match(script, /\["首次接入版本", connector\.client_version\]/);
  assert.match(script, /\["已安装版本", connector\.installed_version\]/);
  assert.match(script, /\["配置目标版本", connector\.configured_version\]/);
  assert.match(script, /\["当前会话启动", dateText\(connector\.runtime_session_started_at\)\]/);
  assert.match(script, /\["实际加载能力", \(connector\.runtime_capabilities \|\| \[\]\)\.join\("、"\) \|\| "未上报"\]/);
  assert.match(script, /connector\.reconnect_required/);
  assert.match(script, /\["最低完整协作版本", connector\.minimum_supported_version\]/);
  assert.match(script, /update_required: "需要升级"/);
  assert.match(script, /navigator\.clipboard\.writeText\(connector\.upgrade_prompt\)/);
  assert.match(script, /查看安全升级方法/);
  assert.match(script, /复制升级指令/);
});

test("task workspace removes duplicate shortcuts and separates assignment, submission, and review", () => {
  assert.doesNotMatch(html, /class="sidebar-quick"/);
  assert.doesNotMatch(html, /id="approval-quick-count"|id="task-quick-count"/);
  const projectNavigation = html.match(/<div data-context-module="projects" hidden>([\s\S]*?)<\/div>/)?.[1] || "";
  assert.doesNotMatch(projectNavigation, /任务中心/);
  assert.match(html, /data-project-filter="awaiting_acceptance"[^>]*>待验收</);
  assert.match(html, /data-project-filter="completed"[^>]*>已完成</);
  assert.match(html, /让 AI 做什么/);
  assert.match(html, /单独设置本次交付要求（可选）/);
  assert.match(html, /id="task-assignment-output"[^>]*placeholder="仅在这次执行需要不同格式或内容时填写"[^>]*><\/textarea>/);
  assert.match(html, /id="task-submission-controls"/);
  assert.match(html, /id="task-review-controls"/);
  assert.match(html, /id="task-completed-result"/);
  assert.match(script, /expected_output: elements\.taskAssignmentOutput\.value\.trim\(\) \|\| null/);
  assert.match(script, /decision === "request_changes" && !note/);
  assert.match(script, /还有 \$\{unfinishedAssignments\} 个 AI 执行单元未完成/);
  assert.match(script, /elements\.taskSubmitFinal\.disabled = unfinishedAssignments > 0/);
});

test("task detail exposes its stable ID, automatic Agent participation, and Human progress", () => {
  assert.match(html, /id="project-task-id"/);
  assert.match(html, /id="project-task-id-copy"[^>]*>复制</);
  assert.match(script, /navigator\.clipboard\.writeText\(taskId\)/);
  assert.match(html, /id="task-my-agent-form"/);
  assert.match(html, /未手动选择时，任务自动使用你的默认 Agent/);
  assert.match(script, /\/my-agents/);
  assert.match(html, /任务成员中的 AI 已经自动参与协同/);
  assert.match(html, /id="project-collaboration-list"/);
  assert.match(script, /等待 Agent 上线/);
  assert.match(script, /邮件通知已安排发送/);
  assert.match(script, /invited_member_count/);
  assert.match(script, /task_message: "发布了任务协作消息"/);
  assert.match(script, /activity\.metadata\?\.body/);
});

test("module and selected view survive navigation and browser history", () => {
  assert.match(script, /searchParams\.set\("module", module\)/);
  assert.match(script, /searchParams\.set\("view", section\)/);
  assert.match(script, /history\.pushState/);
  assert.match(script, /window\.addEventListener\("popstate"/);
  assert.match(script, /elements\.moduleViews\.forEach/);
});

test("Star Orbit opens directly on conversations without a duplicate overview", () => {
  assert.doesNotMatch(html, /data-section="overview"/);
  assert.doesNotMatch(html, /协作总览/);
  assert.match(script, /defaultSection: "communications"/);
  assert.match(script, /orbit: "communications"/);
});

test("header uses the AgentPost brand without centre navigation", () => {
  const header = html.match(/<header class="topbar">[\s\S]*?<\/header>/)?.[0] || "";
  assert.match(html, /class="brand-mark"/);
  assert.match(html, /id="brand-mark-gradient"/);
  assert.match(html, /M11 25c6-13 13-14 18-7/);
  assert.match(html, /<strong>AgentPost<\/strong>/);
  assert.match(html, /<small id="brand-section">任务<\/small>/);
  assert.match(script, /elements\.brandSection\.textContent = definition\.label/);
  assert.doesNotMatch(header, /plane-switch/);
  assert.doesNotMatch(header, /星轨看协作/);
  assert.doesNotMatch(header, /云驿管 Agent/);
  assert.doesNotMatch(header, /设置管账户/);
  assert.match(stylesheet, /\.topbar \{[\s\S]*?min-height: 78px;/);
  assert.match(stylesheet, /\.brand-mark \{[\s\S]*?width: 40px;[\s\S]*?height: 40px;/);
  assert.match(stylesheet, /\.brand-copy strong \{[\s\S]*?font-size: 1\.375rem;/);
  assert.match(stylesheet, /\.connection \{[\s\S]*?min-width: 235px;/);
  assert.match(stylesheet, /"Google Sans"/);
});

test("footer exposes the official ICP filing record on every view", () => {
  assert.match(html, /京ICP备2026049737号/);
  assert.match(html, /href="https:\/\/beian\.miit\.gov\.cn\/"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(stylesheet, /\.filing-record/);
});

test("mobile navigation remains a four-entry bottom bar", () => {
  assert.match(stylesheet, /@media \(max-width: 860px\)/);
  assert.match(stylesheet, /\.workspace-sidebar \{[\s\S]*?position: fixed;[\s\S]*?inset: auto 0 0;/);
  assert.match(stylesheet, /\.primary-navigation \{[\s\S]*?display: flex;/);
  assert.match(stylesheet, /\.primary-nav-item \{[\s\S]*?grid-template-columns: 1fr;/);
  assert.match(script, /window\.scrollTo\(\{ top: 0, left: 0, behavior: "auto" \}\)/);
});

test("mobile Star Orbit keeps only processing and tasks as compact shortcuts", () => {
  assert.match(html, /id="orbit-mobile-shortcuts"/);
  assert.match(html, /class="context-nav-item orbit-mobile-shortcut"[^>]*data-section="approvals"/);
  assert.match(html, /class="context-nav-item orbit-mobile-shortcut"[^>]*data-section="tasks"/);
  assert.match(script, /mobileShortcutIsActive/);
  assert.match(script, /mobileShortcutIsActive \? "communications" : item\.dataset\.section/);
  assert.doesNotMatch(html, /class="orbit-mobile-shortcut"[^>]*data-thread-filter="archived"/);
  assert.match(stylesheet, /\.orbit-mobile-shortcuts:not\(\[hidden\]\) \{[\s\S]*?grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(stylesheet, /\.context-navigation > div\[data-context-module="orbit"\] \{\s*display: none;/);
  assert.match(stylesheet, /\.orbit-mobile-shortcut > span\.orbit-mobile-shortcut-count \{[\s\S]*?display: inline-grid;/);
  assert.match(stylesheet, /\.thread-list-item \{[\s\S]*?min-width: 0;/);
});

test("mobile connection status stays on one line and reports heartbeat-backed online Agents", () => {
  assert.match(html, /connection-label-full/);
  assert.match(html, /connection-label-compact/);
  assert.match(script, /`\$\{connectedAgentCount\} 个 Agent`/);
  assert.match(script, /`\$\{connectedAgentCount\} 个 Agent 在线`/);
  assert.match(script, /connectedAgentCount > 0 \? "success" : ""/);
  assert.match(stylesheet, /\.connection-label-compact \{\s*display: none;/);
  assert.match(stylesheet, /@media \(max-width: 580px\)[\s\S]*?\.connection \{[\s\S]*?white-space: nowrap;/);
  assert.match(stylesheet, /\.connection-label-full \{\s*display: none;/);
  assert.match(stylesheet, /\.connection-label-compact \{\s*display: inline;/);
});

test("opening a conversation remains read-only for Agent state", () => {
  assert.match(html, /放心查看，不会影响 Agent 的处理进度/);
  assert.match(html, /不会替 Agent 标记已读、确认收到或完成任务/);
  assert.match(script, /delivered: "已送达"/);
  assert.match(script, /read: "Agent 已读取"/);
  assert.match(script, /acked: "Agent 已确认收到"/);
  assert.match(script, /\/api\/v1\/orbit\/threads\/\$\{encodeURIComponent\(threadId\)\}\/viewed/);
  assert.match(script, /human_view_state = "viewed"/);
  const communicationStart = html.indexOf('id="communications"');
  const communicationEnd = html.indexOf("</section>", communicationStart);
  const communicationPanel = html.slice(communicationStart, communicationEnd);
  assert.doesNotMatch(communicationPanel, /chat-composer|message-input|<textarea|type="submit"/);
});

test("Orbit conversations are Thread-based, searchable, and deep-linkable", () => {
  assert.match(script, /按每个对话查看 Agent 之间的全部往来/);
  assert.match(html, /主题、Agent、正文或附件名/);
  assert.doesNotMatch(html, /新动态 · 待接入|待我处理 · 待接入/);
  assert.match(script, /\/api\/v1\/orbit\/threads\?/);
  assert.match(script, /\/api\/v1\/orbit\/threads\/\$\{encodeURIComponent\(threadId\)\}/);
  assert.match(script, /thread: state\.selectedThreadId/);
  assert.doesNotMatch(script, /threadOrganization/);
});

test("conversation parent expands complete loops and shows Human unread dots", () => {
  assert.match(html, /id="thread-parent-toggle"/);
  assert.match(html, /aria-controls="thread-browser"/);
  assert.match(html, /aria-expanded="true"/);
  assert.match(html, /id="thread-unread-count"/);
  assert.match(script, /threadBrowserExpanded/);
  assert.match(script, /thread\.human_view_state === "unread"/);
  assert.match(script, /thread-unread-dot/);
  assert.match(script, /\$\{thread\.message_count\} 条往来/);
  assert.match(stylesheet, /\.thread-parent-toggle/);
  assert.match(stylesheet, /\.thread-unread-dot/);
});

test("confirmed header and timeline match the approved three-column mockup", () => {
  assert.match(html, /id="top-human-avatar"/);
  assert.match(html, /id="top-human-name"/);
  assert.match(html, /id="thread-detail-count"/);
  assert.match(html, /id="thread-detail-route"/);
  assert.match(html, /id="thread-detail-state"/);
  assert.match(script, /完整对话 · \$\{messages\.length\} 条往来/);
  assert.match(script, /发送自：\$\{agentConversationLabel\(firstMessage\.sender\)\}/);
  assert.match(script, /card\.classList\.toggle\("from-current-human"/);
  assert.match(script, /elements\.topHumanAvatar\.textContent = "我"/);
  assert.match(stylesheet, /\.top-human-avatar/);
  assert.match(stylesheet, /\.thread-message\.from-current-human/);
});

test("Thread timeline keeps communication, work, replies, and system events distinct", () => {
  assert.match(script, /const messages = \[\.\.\.chronologicalMessages\]\.sort/);
  assert.match(script, /new Date\(right\.created_at\)\.getTime\(\) - new Date\(left\.created_at\)\.getTime\(\)/);
  assert.match(script, /最新内容排在最上面/);
  assert.match(script, /messageList\.firstElementChild\?\.scrollIntoView\(\{ behavior: "smooth", block: "start" \}\)/);
  assert.match(script, /document\.createTextNode\("送达情况"\)/);
  assert.match(script, /document\.createTextNode\("任务进度"\)/);
  assert.match(script, /replied: "已回复"/);
  assert.match(script, /thread-reply-reference/);
  assert.match(script, /scrollIntoView/);
  assert.match(script, /\["event", "system", "error"\]/);
  assert.match(script, /message\.task_expected_output/);
  assert.match(script, /message\.requires_ack \? "是" : "否"/);
  assert.match(script, /由 Agent 提供 · 已按安全方式展示/);
  assert.match(script, /Agent 提供的结构化信息/);
  assert.match(script, /key === "status"/);
  assert.match(script, /查看 Agent 数据与技术信息（JSON）/);
  assert.match(script, /这些信息用于 Agent 协作和问题排查，不代表任务已经完成/);
  assert.match(script, /raw\.textContent = safeText\(message\.content_body, "null"\)/);
  assert.match(script, /summary\.addEventListener\("keydown"/);
  assert.match(script, /details\.open = !details\.open/);
  assert.match(script, /footer\.append\(trust\)/);
  assert.match(stylesheet, /\.thread-structured-summary/);
  assert.match(stylesheet, /\.thread-agent-data/);
});

test("conversation identity and attachments expose clear safe actions", () => {
  assert.match(script, /发送自：\$\{agentConversationLabel\(message\.sender\)\}/);
  assert.match(script, /发送给：\$\{agentConversationLabel\(message\.recipient, \{ currentAsMe: true \}\)\}/);
  assert.match(script, /agent\?\.owner_display_name/);
  assert.match(script, /agent\?\.owned_by_current_human/);
  assert.match(script, /打开 PDF/);
  assert.match(script, /安全预览/);
  assert.match(script, /\/api\/v1\/orbit\/attachments\/\$\{attachmentId\}/);
  assert.match(html, /id="attachment-preview-frame"[^>]*sandbox=""/);
  assert.match(stylesheet, /\.attachment-preview-dialog iframe/);
  assert.match(stylesheet, /\.thread-attachment-action/);
});

test("archived conversations move to Settings and hide from owned Agents without deleting messages", () => {
  assert.doesNotMatch(html, /id="thread-archive-library"/);
  assert.match(html, /data-module="settings" data-section="archives"/);
  assert.match(html, /id="settings-archive-list"/);
  assert.match(html, /id="thread-archive"[^>]*>从我的对话删除</);
  assert.match(html, /你和你名下的 AI 都不会再从 AgentPost 看到这条完整对话/);
  assert.match(html, /设置 → 已归档对话/);
  assert.match(script, /parameters\.set\("archived", "true"\)/);
  assert.match(script, /loadArchivedThreadsForSettings/);
  assert.match(script, /method: "PUT"/);
  assert.match(script, /method: "DELETE"/);
  assert.match(script, /openThreadArchiveDialog\(state\.selectedThread\)/);
  assert.doesNotMatch(script, /thread-list-archive-action/);
});

test("Orbit shortcuts and blank workspace can return to all conversations", () => {
  assert.match(script, /async function returnToAllConversations\(\)/);
  assert.match(script, /module === "orbit"[\s\S]*?await returnToAllConversations\(\)/);
  assert.match(script, /item === elements\.threadParentToggle[\s\S]*?await returnToAllConversations\(\)/);
  assert.match(script, /document\.addEventListener\("click"[\s\S]*?await returnToAllConversations\(\)/);
});

test("mobile Thread list and detail are separate layers", () => {
  assert.match(stylesheet, /thread-workspace-mode:not\(\.thread-detail-open\).*?\.workspace-content/s);
  assert.match(stylesheet, /thread-workspace-mode\.thread-detail-open \.context-sidebar/);
  assert.match(html, /返回对话列表/);
});

test("Relay groups Agents and derives five explicit connection states", () => {
  assert.match(html, /Agent 与连接/);
  assert.match(html, /全部 Agent/);
  assert.match(html, /正常连接/);
  assert.match(html, /等待 Agent/);
  assert.match(html, /离线/);
  assert.match(html, /连接异常/);
  assert.match(script, /connection_state/);
  assert.match(script, /current_connector_last_heartbeat_at/);
  assert.match(script, /你已完成授权，正在等待 Agent/);
  assert.match(script, /曾经连接，但最近连接已超时/);
  assert.match(script, /初始连接时间/);
  assert.match(script, /最近连接时间/);
});

test("new Agent guide offers six host-specific paths in the product order", () => {
  const pickerStart = html.indexOf('class="pairing-host-picker"');
  const pickerEnd = html.indexOf("</fieldset>", pickerStart);
  const picker = html.slice(pickerStart, pickerEnd);
  const hosts = [...picker.matchAll(/data-connector-type="([^"]+)"/g)]
    .map((match) => match[1]);

  assert.deepEqual(hosts, ["workbuddy", "doubao_work", "openclaw", "hermes", "codex", "manus"]);
  assert.match(script, /doubao_work: \{ name: "豆包工作", code: "AP-DOUBAO-WORK-V1", defaultHandle: "doubao", connectionMode: "local_bootstrap" \}/);
  assert.match(script, /manus: \{ name: "Manus", code: "AP-MANUS-V1", defaultHandle: "manus", connectionMode: "local_bootstrap" \}/);
  assert.match(
    script,
    /const connectionMode = selected\.connectionMode \|\| state\.authConfig\?\.host_connection_modes\?\.\[host\]/,
  );
  assert.match(script, /Custom MCP 连接和 AgentPost 网页授权直接完成接入/);
  assert.match(script, /hermes: \{ name: "Hermes", code: "AP-HERMES-V1", defaultHandle: "hermes" \}/);
  assert.match(script, /使用 \$\{selected\.name\} 内置的 Custom MCP 连接/);
  assert.match(script, /不能改用长期密钥或假装已连接/);
  assert.match(html, /<strong>Manus<\/strong>\s*<span>本地文件夹<\/span>/);
  assert.match(script, /文件生成后必须新建 Manus 任务/);
  assert.match(script, /\.\/xingyunyi status/);
  assert.match(script, /不要改用 Custom MCP 或 Remote MCP/);
  assert.match(stylesheet, /\.pairing-host-picker\s*\{[^}]*repeat\(3, minmax\(0, 1fr\)\)/s);
  assert.match(stylesheet, /@media \(max-width: 580px\)[\s\S]*\.pairing-host-picker\s*\{\s*grid-template-columns: 1fr/);
});

test("new Agent approval suggests a platform handle and explains each invalid shape", () => {
  const approvalStart = html.indexOf('id="pairing-approval"');
  const approvalEnd = html.indexOf("</section>", approvalStart);
  const approval = html.slice(approvalStart, approvalEnd);

  assert.match(script, /codex: \{ name: "Codex", code: "AP-CODEX-V1", defaultHandle: "codex" \}/);
  assert.match(script, /workbuddy: \{ name: "WorkBuddy", code: "AP-WORKBUDDY-V1", defaultHandle: "workbuddy" \}/);
  assert.match(script, /const candidate = `\$\{base\}-\$\{suffix\}`/);
  assert.match(html, /1–32 个中文、英文字母或数字/);
  assert.match(script, /\^\[\\p\{L\}\\p\{N\}-\]\+\$\/u/);
  assert.match(script, /不能使用空格、下划线或其他符号/);
  assert.match(script, /连字符不能放在开头或结尾，也不能连续使用/);
  assert.match(script, /是系统保留名称/);
  assert.match(approval, /id="pairing-handle-help"/);
  assert.doesNotMatch(approval, /pairing-mfa|双重验证验证码或恢复码/);
});

test("Agent detail keeps current connection, history, access and actions distinct", () => {
  for (const tab of ["summary", "connection", "capabilities", "access", "history", "threads", "danger"]) {
    assert.match(html, new RegExp(`data-agent-tab="${tab}"`));
  }
  assert.match(html, /重新连接这个 Agent/);
  assert.match(html, /历史连接/);
  assert.match(html, /删除采用软删除/);
  assert.match(script, /connector\.is_current && connector\.status === "active"/);
  assert.match(script, /agent\.role === "owner"/);
  assert.match(script, /可执行的操作以你的实际权限为准/);
  assert.match(script, /\/api\/v1\/orbit\/threads\?limit=200&agent_id=/);
});

test("Agent owners can find the short-name action in the detail heading", () => {
  const headingStart = html.indexOf('class="agent-detail-heading-actions"');
  const headingEnd = html.indexOf("</div>", headingStart);
  const headingActions = html.slice(headingStart, headingEnd);
  const dangerStart = html.indexOf('id="agent-owner-actions"');
  const dangerEnd = html.indexOf("</div>", dangerStart);
  const dangerActions = html.slice(dangerStart, dangerEnd);

  assert.match(headingActions, /id="agent-rename"/);
  assert.match(headingActions, /id="agent-set-default"/);
  assert.doesNotMatch(dangerActions, /id="agent-rename"/);
  assert.match(script, /elements\.agentRename\.hidden = !owner/);
  assert.match(script, /elements\.agentSetDefault\.hidden = !owner/);
  assert.match(script, /agent\.is_default \? "默认 Agent" : "设为默认 Agent"/);
});

test("Agent selection and tab survive deep links and browser history", () => {
  assert.match(script, /parameters\.get\("agent"\)/);
  assert.match(script, /parameters\.get\("agentTab"\)/);
  assert.match(script, /agent: state\.selectedAgentId/);
  assert.match(script, /agentTab: state\.agentTab/);
  assert.match(script, /applyAgentRouteParameters\(parameters\)/);
  assert.match(script, /returnThread/);
});

test("mobile Agent list and detail are separate layers", () => {
  assert.match(stylesheet, /agent-workspace-mode:not\(\.agent-detail-open\).*?\.workspace-content/s);
  assert.match(stylesheet, /agent-workspace-mode\.agent-detail-open \.context-sidebar/);
  assert.match(html, /返回 Agent 列表/);
});

test("profile username is editable while unavailable settings stay explanatory", () => {
  assert.match(html, /id="profile-username"/);
  assert.match(html, /id="profile-username-form"/);
  assert.match(html, /id="profile-username"[^>]*minlength="3"[^>]*maxlength="32"/);
  assert.match(script, /requestJson\("\/api\/v1\/orbit\/me\/username"/);
  assert.match(script, /method: "PATCH"/);
  assert.match(script, /human_username_updated|用户名已修改为/);
  assert.match(html, /id="register-username"[^>]*required/);
  assert.match(html, /用于让他人准确找到你，例如 020/);
  assert.match(script, /username: elements\.registerUsername\.value\.trim\(\)\.toLowerCase\(\)/);
  for (const section of ["notifications", "privacy", "preferences"]) {
    const start = html.indexOf(`id="${section}"`);
    const end = html.indexOf("</section>", start);
    const panel = html.slice(start, end);
    assert.notEqual(start, -1);
    assert.match(panel, /尚未接入|待确认/);
    assert.doesNotMatch(panel, /<input|<select|type="submit"/);
  }
});

test("task is the only multi-Human collaboration scope", () => {
  const combined = `${html}\n${script}\n${stylesheet}`;
  assert.match(html, /多人协作只发生在明确的任务内/);
  assert.doesNotMatch(combined, /organization|组织|群聊|oidc|SSO/i);
});
