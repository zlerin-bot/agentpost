"use strict";

const FALLBACK_CONNECTOR_RELEASE = Object.freeze({
  version: "0.1.0",
  wheel_url: "https://agentpost.me/downloads/agentpost-0.1.0-py3-none-any.whl",
  wheel_sha256: "1fc3f42e8c1141ce65481778587544fc9bf441438c852c0332594ab24a75fdf7",
});
const LOCAL_AGENT_ID_PATTERN = /^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$/;
const RESERVED_AGENT_HANDLES = new Set([
  "admin", "agentpost", "api", "app", "connect", "directory", "help", "inbox",
  "login", "logout", "mcp", "orbit", "root", "security", "settings", "signup",
  "support", "system", "www",
]);

const state = {
  dashboard: null,
  csrfToken: "",
  pairingRequestSignature: "",
  pairingIdempotencyKey: "",
  requestedPairingOpened: false,
  authConfig: null,
  registerChallengeId: "",
  recoveryChallengeId: "",
  mfaSetupStarted: false,
  pairingTargetResolution: "pending",
  pairingCreateNewAutomatically: false,
  selectedPairingHost: "",
  pairingTargetAgent: null,
  pairingNewAgentIntent: "",
  pairingSuggestedHandle: "",
  pairingConnectorType: "",
  connectors: [],
  threads: [],
  archivedThreads: [],
  selectedThread: null,
  selectedThreadId: "",
  threadFilter: "all",
  threadQuery: "",
  threadSearchTimer: null,
  threadBrowserExpanded: true,
  selectedAgentId: "",
  selectedAgent: null,
  agentTab: "summary",
  agentQuery: "",
  agentRelatedThreads: [],
  projects: [],
  selectedProject: null,
  selectedProjectId: "",
  projectInvitationCandidates: [],
  projectsLoaded: false,
  projectQuery: "",
  projectFilter: "active",
  taskRecordFilter: "discussion",
  taskActivityLimit: 200,
  taskFiles: [],
  taskFileQuery: "",
  taskFileUploader: "",
  taskFileType: "",
  taskFileMine: false,
  taskRequestSequence: 0,
  taskLoadError: "",
  taskReplyDrafts: new Map(),
  taskAssignmentDrafts: new Map(),
  friends: [],
  friendsLoaded: false,
  selectedFriendId: "",
  friendQuery: "",
  friendSearchTimer: null,
  friendFilter: "accepted",
  activeModule: "projects",
  activeSection: "board",
  lastSectionByModule: {
    orbit: "communications",
    relay: "agents",
    projects: "board",
    friends: "directory",
    settings: "profile",
  },
};

const elements = {
  welcomeView: document.querySelector("#welcome-view"),
  workspaceView: document.querySelector("#workspace-view"),
  loginForm: document.querySelector("#login-form"),
  loginEmail: document.querySelector("#login-email"),
  loginPassword: document.querySelector("#login-password"),
  loginMfa: document.querySelector("#login-mfa"),
  openRegister: document.querySelector("#open-register"),
  openRecovery: document.querySelector("#open-recovery"),
  accessResult: document.querySelector("#access-result"),
  connectionState: document.querySelector("#connection-state"),
  brandSection: document.querySelector("#brand-section"),
  topHumanName: document.querySelector("#top-human-name"),
  topHumanAvatar: document.querySelector("#top-human-avatar"),
  refresh: document.querySelector("#refresh-dashboard"),
  signOut: document.querySelector("#sign-out"),
  profileRefresh: document.querySelector("#profile-refresh"),
  profileSignOut: document.querySelector("#profile-sign-out"),
  humanName: document.querySelector("#human-name"),
  humanEmail: document.querySelector("#human-email"),
  humanAvatar: document.querySelector("#human-avatar"),
  approvalMobileCount: document.querySelector("#approval-mobile-count"),
  taskMobileCount: document.querySelector("#task-mobile-count"),
  profileName: document.querySelector("#profile-name"),
  profileUsernameForm: document.querySelector("#profile-username-form"),
  profileUsernameInput: document.querySelector("#profile-username"),
  profileUsernameSave: document.querySelector("#profile-username-save"),
  profileUsernameResult: document.querySelector("#profile-username-result"),
  profileEmail: document.querySelector("#profile-email"),
  profileTimezone: document.querySelector("#profile-timezone"),
  primaryNavigation: document.querySelector("#primary-navigation"),
  primaryNavigationItems: Array.from(document.querySelectorAll(".primary-nav-item")),
  contextNavigation: document.querySelector("#context-navigation"),
  orbitMobileShortcuts: document.querySelector("#orbit-mobile-shortcuts"),
  contextNavigationGroups: Array.from(document.querySelectorAll("[data-context-module]")),
  contextNavigationItems: Array.from(document.querySelectorAll(".context-nav-item")),
  moduleViews: Array.from(document.querySelectorAll(".module-view")),
  contextEyebrow: document.querySelector("#context-eyebrow"),
  contextTitle: document.querySelector("#context-title"),
  contextCopy: document.querySelector("#context-copy"),
  threadBrowser: document.querySelector("#thread-browser"),
  threadParentToggle: document.querySelector("#thread-parent-toggle"),
  threadParentSummary: document.querySelector("#thread-parent-summary"),
  threadUnreadCount: document.querySelector("#thread-unread-count"),
  threadCount: document.querySelector("#thread-count"),
  threadSearchInput: document.querySelector("#thread-search-input"),
  threadFilters: Array.from(document.querySelectorAll("[data-thread-filter]")),
  threadList: document.querySelector("#thread-list"),
  settingsArchiveList: document.querySelector("#settings-archive-list"),
  threadMobileBack: document.querySelector("#thread-mobile-back"),
  threadDetailEmpty: document.querySelector("#thread-detail-empty"),
  threadDetail: document.querySelector("#thread-detail"),
  threadDetailTopic: document.querySelector("#thread-detail-topic"),
  threadDetailCount: document.querySelector("#thread-detail-count"),
  threadDetailRoute: document.querySelector("#thread-detail-route"),
  threadDetailState: document.querySelector("#thread-detail-state"),
  threadDetailParticipants: document.querySelector("#thread-detail-participants"),
  threadArchive: document.querySelector("#thread-archive"),
  threadLatest: document.querySelector("#thread-latest"),
  threadArchiveDialog: document.querySelector("#thread-archive-dialog"),
  threadArchiveForm: document.querySelector("#thread-archive-form"),
  threadArchiveClose: document.querySelector("#thread-archive-close"),
  threadArchiveCancel: document.querySelector("#thread-archive-cancel"),
  threadArchiveSummary: document.querySelector("#thread-archive-summary"),
  threadArchiveId: document.querySelector("#thread-archive-id"),
  threadArchiveResult: document.querySelector("#thread-archive-result"),
  threadArchiveSubmit: document.querySelector("#thread-archive-submit"),
  agentBrowser: document.querySelector("#agent-browser"),
  agentBrowserCount: document.querySelector("#agent-browser-count"),
  agentSearchInput: document.querySelector("#agent-search-input"),
  agentBrowserNew: document.querySelector("#agent-browser-new"),
  agentBrowserList: document.querySelector("#agent-browser-list"),
  projectBrowser: document.querySelector("#project-browser"),
  projectBrowserCount: document.querySelector("#project-browser-count"),
  projectSearchInput: document.querySelector("#project-search-input"),
  projectFilters: Array.from(document.querySelectorAll("[data-project-filter]")),
  projectBrowserNew: document.querySelector("#project-browser-new"),
  projectBrowserList: document.querySelector("#project-browser-list"),
  projectMobileBack: document.querySelector("#project-mobile-back"),
  projectEmpty: document.querySelector("#project-empty"),
  projectEmptyNew: document.querySelector("#project-empty-new"),
  projectDetail: document.querySelector("#project-detail"),
  projectDetailType: document.querySelector("#project-detail-type"),
  projectDetailTitle: document.querySelector("#project-detail-title"),
  projectTaskId: document.querySelector("#project-task-id"),
  projectTaskIdCopy: document.querySelector("#project-task-id-copy"),
  projectDetailDescription: document.querySelector("#project-detail-description"),
  projectDetailStatus: document.querySelector("#project-detail-status"),
  projectInvitationActions: document.querySelector("#project-invitation-actions"),
  projectAccept: document.querySelector("#project-accept"),
  projectDecline: document.querySelector("#project-decline"),
  projectOwner: document.querySelector("#project-owner"),
  projectMemberCount: document.querySelector("#project-member-count"),
  projectDue: document.querySelector("#project-due"),
  projectStateAxes: document.querySelector("#project-state-axes"),
  projectActionResult: document.querySelector("#project-action-result"),
  projectMemberList: document.querySelector("#project-member-list"),
  taskMyAgentForm: document.querySelector("#task-my-agent-form"),
  taskMyAgentOptions: document.querySelector("#task-my-agent-options"),
  taskMyPrimaryAgent: document.querySelector("#task-my-primary-agent"),
  taskAddAgent: document.querySelector("#task-add-agent"),
  taskMyAgentHelp: document.querySelector("#task-my-agent-help"),
  projectInvite: document.querySelector("#project-invite"),
  projectMemberInvite: document.querySelector("#project-member-invite"),
  projectArchive: document.querySelector("#project-archive"),
  projectActivityList: document.querySelector("#project-activity-list"),
  projectCollaborationList: document.querySelector("#project-collaboration-list"),
  taskFileCount: document.querySelector("#task-file-count"),
  taskFileSearch: document.querySelector("#task-file-search"),
  taskFileUploader: document.querySelector("#task-file-uploader"),
  taskFileType: document.querySelector("#task-file-type"),
  taskFileMine: document.querySelector("#task-file-mine"),
  taskFileClear: document.querySelector("#task-file-clear"),
  taskFileList: document.querySelector("#task-file-list"),
  taskOwnerControls: document.querySelector("#task-owner-controls"),
  taskAssignmentForm: document.querySelector("#task-assignment-form"),
  taskAssignmentAgent: document.querySelector("#task-assignment-agent"),
  taskAssignmentSelection: document.querySelector("#task-assignment-selection"),
  taskAssignmentSubmit: document.querySelector("#task-assignment-submit"),
  taskAssignmentFeedback: document.querySelector("#task-assignment-feedback"),
  taskAssignmentInstruction: document.querySelector("#task-assignment-instruction"),
  taskAssignmentOutput: document.querySelector("#task-assignment-output"),
  taskAssignmentOutputInherited: document.querySelector("#task-assignment-output-inherited"),
  taskSubmissionControls: document.querySelector("#task-submission-controls"),
  taskSubmissionForm: document.querySelector("#task-submission-form"),
  taskFinalSummary: document.querySelector("#task-final-summary"),
  taskSubmissionHelp: document.querySelector("#task-submission-help"),
  taskSubmitFinal: document.querySelector("#task-submit-final"),
  taskReviewControls: document.querySelector("#task-review-controls"),
  taskReviewSummary: document.querySelector("#task-review-summary"),
  taskReviewNote: document.querySelector("#task-review-note"),
  taskRequestChanges: document.querySelector("#task-request-changes"),
  taskAcceptFinal: document.querySelector("#task-accept-final"),
  taskCompletedResult: document.querySelector("#task-completed-result"),
  taskCompletedSummary: document.querySelector("#task-completed-summary"),
  friendBrowser: document.querySelector("#friend-browser"),
  friendPendingBadge: document.querySelector("#friend-pending-badge"),
  friendPendingNotice: document.querySelector("#friend-pending-notice"),
  friendBrowserCount: document.querySelector("#friend-browser-count"),
  friendSearchInput: document.querySelector("#friend-search-input"),
  friendFilters: Array.from(document.querySelectorAll("[data-friend-filter]")),
  friendBrowserList: document.querySelector("#friend-browser-list"),
  friendMobileBack: document.querySelector("#friend-mobile-back"),
  friendEmpty: document.querySelector("#friend-empty"),
  friendDetail: document.querySelector("#friend-detail"),
  friendDetailAvatar: document.querySelector("#friend-detail-avatar"),
  friendDetailRelation: document.querySelector("#friend-detail-relation"),
  friendDetailName: document.querySelector("#friend-detail-name"),
  friendDetailRole: document.querySelector("#friend-detail-role"),
  friendDetailOnline: document.querySelector("#friend-detail-online"),
  friendStartProject: document.querySelector("#friend-start-project"),
  friendCapabilities: document.querySelector("#friend-capabilities"),
  friendDetailNote: document.querySelector("#friend-detail-note"),
  friendAgentCount: document.querySelector("#friend-agent-count"),
  friendAgentList: document.querySelector("#friend-agent-list"),
  friendProjectCount: document.querySelector("#friend-project-count"),
  friendProjectList: document.querySelector("#friend-project-list"),
  projectCreateDialog: document.querySelector("#project-create-dialog"),
  projectCreateForm: document.querySelector("#project-create-form"),
  projectCreateClose: document.querySelector("#project-create-close"),
  projectCreateCancel: document.querySelector("#project-create-cancel"),
  projectCreateName: document.querySelector("#project-create-name"),
  projectCreateGoal: document.querySelector("#project-create-goal"),
  projectCreateOutput: document.querySelector("#project-create-output"),
  projectCreateAgentOptions: document.querySelector("#project-create-agent-options"),
  projectAcceptAgentOptions: document.querySelector("#project-accept-agent-options"),
  projectCreateResult: document.querySelector("#project-create-result"),
  projectInviteDialog: document.querySelector("#project-invite-dialog"),
  projectInviteForm: document.querySelector("#project-invite-form"),
  projectInviteClose: document.querySelector("#project-invite-close"),
  projectInviteCancel: document.querySelector("#project-invite-cancel"),
  projectInviteSummary: document.querySelector("#project-invite-summary"),
  projectInviteOptions: document.querySelector("#project-invite-options"),
  projectInviteResult: document.querySelector("#project-invite-result"),
  agentMobileBack: document.querySelector("#agent-mobile-back"),
  agentOverview: document.querySelector("#agent-overview"),
  agentOverviewNew: document.querySelector("#agent-overview-new"),
  agentStatAll: document.querySelector("#agent-stat-all"),
  agentStatConnected: document.querySelector("#agent-stat-connected"),
  agentStatAwaiting: document.querySelector("#agent-stat-awaiting"),
  agentStatOffline: document.querySelector("#agent-stat-offline"),
  agentStatError: document.querySelector("#agent-stat-error"),
  agentOverviewGroups: document.querySelector("#agent-overview-groups"),
  agentDetail: document.querySelector("#agent-detail"),
  agentDetailMissing: document.querySelector("#agent-detail-missing"),
  agentDetailAvatar: document.querySelector("#agent-detail-avatar"),
  agentDetailName: document.querySelector("#agent-detail-name"),
  agentDetailSubtitle: document.querySelector("#agent-detail-subtitle"),
  agentDetailStatus: document.querySelector("#agent-detail-status"),
  agentReturnThread: document.querySelector("#agent-return-thread"),
  agentDetailTabs: Array.from(document.querySelectorAll("[data-agent-tab]")),
  agentDetailPanels: Array.from(document.querySelectorAll("[data-agent-panel]")),
  agentDetailSummary: document.querySelector("#agent-detail-summary"),
  agentCurrentConnection: document.querySelector("#agent-current-connection"),
  agentWakeAuth: document.querySelector("#agent-wake-auth"),
  agentWakeTestConsent: document.querySelector("#agent-wake-test-consent"),
  agentWakeChannel: document.querySelector("#agent-wake-channel"),
  agentWakeTag: document.querySelector("#agent-wake-tag"),
  agentWakeTitle: document.querySelector("#agent-wake-title"),
  agentWakeStatus: document.querySelector("#agent-wake-status"),
  agentWakeCopy: document.querySelector("#agent-wake-copy"),
  agentWakeForm: document.querySelector("#agent-wake-form"),
  agentWakeUrl: document.querySelector("#agent-wake-url"),
  agentWakeToken: document.querySelector("#agent-wake-token"),
  agentWakeSave: document.querySelector("#agent-wake-save"),
  agentWakeTest: document.querySelector("#agent-wake-test"),
  agentWakeDisable: document.querySelector("#agent-wake-disable"),
  agentWakeResult: document.querySelector("#agent-wake-result"),
  agentWakeSecurity: document.querySelector("#agent-wake-security"),
  agentDetailCapabilities: document.querySelector("#agent-detail-capabilities"),
  agentDetailAccess: document.querySelector("#agent-detail-access"),
  agentConnectionHistory: document.querySelector("#agent-connection-history"),
  agentRelatedThreads: document.querySelector("#agent-related-threads"),
  agentOwnerActions: document.querySelector("#agent-owner-actions"),
  agentReadonlyActions: document.querySelector("#agent-readonly-actions"),
  agentReconnect: document.querySelector("#agent-reconnect"),
  agentRename: document.querySelector("#agent-rename"),
  agentSetDefault: document.querySelector("#agent-set-default"),
  agentDisconnect: document.querySelector("#agent-disconnect"),
  agentDelete: document.querySelector("#agent-delete"),
  taskList: document.querySelector("#task-list"),
  approvalList: document.querySelector("#approval-list"),
  messageList: document.querySelector("#message-list"),
  attachmentPreviewDialog: document.querySelector("#attachment-preview-dialog"),
  attachmentPreviewTitle: document.querySelector("#attachment-preview-title"),
  attachmentPreviewMeta: document.querySelector("#attachment-preview-meta"),
  attachmentPreviewFrame: document.querySelector("#attachment-preview-frame"),
  attachmentPreviewDownload: document.querySelector("#attachment-preview-download"),
  attachmentPreviewClose: document.querySelector("#attachment-preview-close"),
  attachmentPreviewDone: document.querySelector("#attachment-preview-done"),
  connectorList: document.querySelector("#connector-list"),
  securityStatus: document.querySelector("#security-status"),
  openMfa: document.querySelector("#open-mfa"),
  openKeyRotation: document.querySelector("#open-key-rotation"),
  openPairing: document.querySelector("#open-pairing"),
  approvalDialog: document.querySelector("#approval-dialog"),
  approvalForm: document.querySelector("#approval-form"),
  approvalDialogTitle: document.querySelector("#approval-dialog-title"),
  approvalDialogSummary: document.querySelector("#approval-dialog-summary"),
  approvalId: document.querySelector("#approval-id"),
  approvalDecision: document.querySelector("#approval-decision"),
  approvalNote: document.querySelector("#approval-note"),
  approvalAccessKey: document.querySelector("#approval-access-key"),
  approvalMfa: document.querySelector("#approval-mfa"),
  approvalResult: document.querySelector("#approval-result"),
  approvalSubmit: document.querySelector("#approval-submit"),
  approvalClose: document.querySelector("#approval-close"),
  approvalCancel: document.querySelector("#approval-cancel"),
  pairingDialog: document.querySelector("#pairing-dialog"),
  pairingForm: document.querySelector("#pairing-form"),
  pairingClose: document.querySelector("#pairing-close"),
  pairingCancel: document.querySelector("#pairing-cancel"),
  pairingDeny: document.querySelector("#pairing-deny"),
  pairingSubmit: document.querySelector("#pairing-submit"),
  pairingDialogSummary: document.querySelector("#pairing-dialog-summary"),
  pairingGuide: document.querySelector("#pairing-guide"),
  pairingApproval: document.querySelector("#pairing-approval"),
  pairingHostCards: Array.from(document.querySelectorAll(".pairing-host-card")),
  pairingChatCard: document.querySelector("#pairing-chat-card"),
  pairingHostName: document.querySelector("#pairing-host-name"),
  pairingChatPrompt: document.querySelector("#pairing-chat-prompt"),
  pairingCopyPrompt: document.querySelector("#pairing-copy-prompt"),
  pairingCopyResult: document.querySelector("#pairing-copy-result"),
  pairingGuideBack: document.querySelector("#pairing-guide-back"),
  pairingGuideCancel: document.querySelector("#pairing-guide-cancel"),
  pairingId: document.querySelector("#pairing-id"),
  pairingUserCode: document.querySelector("#pairing-user-code"),
  pairingCodeFields: document.querySelector("#pairing-code-fields"),
  pairingTargetModeField: document.querySelector("#pairing-target-mode-field"),
  pairingTargetMode: document.querySelector("#pairing-target-mode"),
  pairingTargetSummary: document.querySelector("#pairing-target-summary"),
  pairingHandle: document.querySelector("#pairing-handle"),
  pairingHandleHelp: document.querySelector("#pairing-handle-help"),
  pairingExistingAgentField: document.querySelector("#pairing-existing-agent-field"),
  pairingExistingAgent: document.querySelector("#pairing-existing-agent"),
  pairingNewAgentFields: document.querySelector("#pairing-new-agent-fields"),
  pairingLocalId: document.querySelector("#pairing-local-id"),
  pairingAddressDomain: document.querySelector("#pairing-address-domain"),
  pairingDisplayName: document.querySelector("#pairing-display-name"),
  pairingCapabilities: document.querySelector("#pairing-capabilities"),
  pairingAccessKey: document.querySelector("#pairing-access-key"),
  pairingPreview: document.querySelector("#pairing-preview"),
  pairingResult: document.querySelector("#pairing-result"),
  handleDialog: document.querySelector("#handle-dialog"),
  handleForm: document.querySelector("#handle-form"),
  handleClose: document.querySelector("#handle-close"),
  handleCancel: document.querySelector("#handle-cancel"),
  handleSubmit: document.querySelector("#handle-submit"),
  handleAgentId: document.querySelector("#handle-agent-id"),
  agentHandle: document.querySelector("#agent-handle"),
  handleSummary: document.querySelector("#handle-summary"),
  handleResult: document.querySelector("#handle-result"),
  revokeDialog: document.querySelector("#revoke-dialog"),
  revokeForm: document.querySelector("#revoke-form"),
  revokeClose: document.querySelector("#revoke-close"),
  revokeCancel: document.querySelector("#revoke-cancel"),
  revokeSubmit: document.querySelector("#revoke-submit"),
  revokeConnectorId: document.querySelector("#revoke-connector-id"),
  revokeAccessKey: document.querySelector("#revoke-access-key"),
  revokeMfa: document.querySelector("#revoke-mfa"),
  revokeSummary: document.querySelector("#revoke-summary"),
  revokeResult: document.querySelector("#revoke-result"),
  deleteAgentDialog: document.querySelector("#delete-agent-dialog"),
  deleteAgentForm: document.querySelector("#delete-agent-form"),
  deleteAgentClose: document.querySelector("#delete-agent-close"),
  deleteAgentCancel: document.querySelector("#delete-agent-cancel"),
  deleteAgentSubmit: document.querySelector("#delete-agent-submit"),
  deleteAgentId: document.querySelector("#delete-agent-id"),
  deleteAgentSummary: document.querySelector("#delete-agent-summary"),
  deleteAgentResult: document.querySelector("#delete-agent-result"),
  registerDialog: document.querySelector("#register-dialog"),
  registerForm: document.querySelector("#register-form"),
  registerClose: document.querySelector("#register-close"),
  registerCancel: document.querySelector("#register-cancel"),
  registerEmail: document.querySelector("#register-email"),
  registerCode: document.querySelector("#register-code"),
  registerUsername: document.querySelector("#register-username"),
  registerName: document.querySelector("#register-name"),
  registerPassword: document.querySelector("#register-password"),
  registerSendCode: document.querySelector("#register-send-code"),
  registerResult: document.querySelector("#register-result"),
  recoveryDialog: document.querySelector("#recovery-dialog"),
  recoveryForm: document.querySelector("#recovery-form"),
  recoveryClose: document.querySelector("#recovery-close"),
  recoveryCancel: document.querySelector("#recovery-cancel"),
  recoveryEmail: document.querySelector("#recovery-email"),
  recoveryCode: document.querySelector("#recovery-code"),
  recoveryPassword: document.querySelector("#recovery-password"),
  recoveryMfa: document.querySelector("#recovery-mfa"),
  recoverySendCode: document.querySelector("#recovery-send-code"),
  recoveryResult: document.querySelector("#recovery-result"),
  mfaDialog: document.querySelector("#mfa-dialog"),
  mfaForm: document.querySelector("#mfa-form"),
  mfaClose: document.querySelector("#mfa-close"),
  mfaCancel: document.querySelector("#mfa-cancel"),
  mfaCreate: document.querySelector("#mfa-create"),
  mfaPassword: document.querySelector("#mfa-password"),
  mfaCurrentProof: document.querySelector("#mfa-current-proof"),
  mfaConfirmCode: document.querySelector("#mfa-confirm-code"),
  mfaProvisioning: document.querySelector("#mfa-provisioning"),
  mfaResult: document.querySelector("#mfa-result"),
  keyDialog: document.querySelector("#key-dialog"),
  keyForm: document.querySelector("#key-form"),
  keyClose: document.querySelector("#key-close"),
  keyCancel: document.querySelector("#key-cancel"),
  keyPassword: document.querySelector("#key-password"),
  keyMfa: document.querySelector("#key-mfa"),
  keyLabel: document.querySelector("#key-label"),
  keyOutput: document.querySelector("#key-output"),
  keyResult: document.querySelector("#key-result"),
};

const MODULE_DEFINITIONS = Object.freeze({
  orbit: Object.freeze({
    label: "AgentPost",
    title: "我的对话",
    description: "按每个对话查看 Agent 之间的全部往来。",
    defaultSection: "communications",
    sections: Object.freeze(["communications", "tasks", "approvals"]),
  }),
  relay: Object.freeze({
    label: "AI",
    title: "我的 AI",
    description: "管理 AI 身份、连接状态和任务参与能力。",
    defaultSection: "agents",
    sections: Object.freeze(["agents", "connections"]),
  }),
  projects: Object.freeze({
    label: "任务",
    title: "任务",
    description: "",
    defaultSection: "board",
    sections: Object.freeze(["board"]),
  }),
  friends: Object.freeze({
    label: "好友",
    title: "好友",
    description: "好友必须双向确认，确认后才能邀请对方加入任务。",
    defaultSection: "directory",
    sections: Object.freeze(["directory"]),
  }),
  settings: Object.freeze({
    label: "设置",
    title: "账户与平台",
    description: "管理账户安全、归档记录和平台选项。",
    defaultSection: "profile",
    sections: Object.freeze([
      "profile",
      "security",
      "archives",
      "notifications",
      "privacy",
      "preferences",
      "governance",
    ]),
  }),
});

function projectById(projectId) {
  return state.projects.find((project) => project.task_id === projectId) || null;
}

function friendById(friendId) {
  return state.friends.find((friend) => friend.human_user_id === friendId) || null;
}

function ownedTaskAgents() {
  const agents = Array.isArray(state.dashboard?.agents) ? state.dashboard.agents : [];
  return agents.filter((agent) => agent.role === "owner" && agent.status === "active");
}

function projectStatusLabel(project) {
  const labels = {
    active: "进行中",
    paused: "已暂停",
    awaiting_acceptance: "待验收",
    completed: "已完成",
    cancelled: "已取消",
    archived: "已归档",
  };
  return labels[project.status] || project.status;
}

function projectKind(project) {
  const total = project.active_member_count + project.invited_member_count;
  if (total <= 1) {
    return "个人任务";
  }
  return total === 2 ? "一对一任务" : "多人任务";
}

function dateOnlyText(value) {
  if (!value) {
    return "待确定";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return safeText(value);
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed);
}

function filteredProjects() {
  const query = state.projectQuery.trim().toLowerCase();
  return state.projects.filter((project) => {
    const personalState = project.personal_state || "active";
    if (["archived", "deleted"].includes(state.projectFilter)) {
      return personalState === state.projectFilter && (!query || (project.title + " " + project.goal).toLowerCase().includes(query));
    }
    if (personalState !== "active") return false;
    const matchesFilter = state.projectFilter === "all"
      || (state.projectFilter === "active" && ["active", "paused"].includes(project.status))
      || project.status === state.projectFilter;
    const searchable = [
      project.title,
      project.goal || "",
      project.owner_display_name,
      projectStatusLabel(project),
    ].join(" ").toLowerCase();
    return matchesFilter && (!query || searchable.includes(query));
  });
}

function setProjectFilter(filter) {
  state.projectFilter = filter;
  elements.projectFilters.forEach((button) => {
    const active = button.dataset.projectFilter === filter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function filteredFriends() {
  const query = state.friendQuery.trim().toLowerCase();
  return state.friends.filter((friend) => {
    const matchesFilter = state.friendFilter === "accepted"
      ? friend.relation_status === "accepted"
      : ["pending_incoming", "pending_outgoing"].includes(state.friendFilter)
        ? friend.relation_status === state.friendFilter
        : friend.relation_status === "suggested";
    const searchable = [
      friend.display_name,
      friend.username,
      friend.search_match || "",
      ...friend.agents.flatMap((agent) => agent.capabilities || []),
      ...friend.agents.flatMap((agent) => [agent.display_name, agent.address]),
    ].join(" ").toLowerCase();
    return matchesFilter && (!query || searchable.includes(query));
  });
}

function friendRelationLabel(friend) {
  return {
    accepted: "已成为好友",
    pending_incoming: "待你确认",
    pending_outgoing: "等待对方确认",
    suggested: "可申请好友",
  }[friend.relation_status] || "关系待确认";
}

function createCollaborationListButton({ title, meta, badge, active, avatar, onClick, unread = false }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "prototype-list-item";
  button.classList.toggle("active", active);
  if (active) {
    button.setAttribute("aria-current", "true");
  }
  const avatarNode = document.createElement("span");
  avatarNode.className = "prototype-list-avatar";
  avatarNode.textContent = avatar;
  avatarNode.setAttribute("aria-hidden", "true");
  const copy = document.createElement("span");
  copy.className = "prototype-list-copy";
  const titleNode = document.createElement("strong");
  titleNode.textContent = title;
  if (unread) {
    const dot = document.createElement("span");
    dot.className = "task-new-dot";
    dot.setAttribute("aria-label", "有新消息");
    dot.setAttribute("role", "img");
    titleNode.append(dot);
  }
  const metaNode = document.createElement("small");
  metaNode.textContent = meta;
  copy.append(titleNode, metaNode);
  const badgeNode = document.createElement("span");
  badgeNode.className = "prototype-list-badge";
  badgeNode.textContent = badge;
  button.append(avatarNode, copy, badgeNode);
  button.addEventListener("click", onClick);
  return button;
}

async function loadProjects({ preserveSelection = true } = {}) {
  if (!state.dashboard) {
    return;
  }
  const selectionAtRequest = state.selectedProjectId;
  const firstLoad = !state.projectsLoaded;
  try {
    const payload = await requestJson("/api/v1/tasks");
    if (state.selectedProjectId !== selectionAtRequest) return;
    state.projects = Array.isArray(payload?.items) ? payload.items : [];
    state.projectsLoaded = true;
    const requestedTaskId = new URL(window.location.href).searchParams.get("task") || "";
    if (requestedTaskId && preserveSelection && !state.selectedProjectId) {
      state.selectedProjectId = requestedTaskId;
    } else if (!preserveSelection || !projectById(state.selectedProjectId)) {
      state.selectedProjectId = isMobileWorkspace() ? "" : (filteredProjects()[0]?.task_id || "");
    }
    renderProjectBrowser();
    updateCollaborationWorkspaceMode();
    if (firstLoad && !window.location.hash) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    if (state.selectedProjectId) {
      await loadProjectDetail(state.selectedProjectId);
    } else {
      state.selectedProject = null;
      renderProjectDetail();
    }
    renderFriendDetail();
  } catch (error) {
    if (state.selectedProjectId !== selectionAtRequest) return;
    state.projectsLoaded = true;
    state.projects = [];
    state.selectedProject = null;
    elements.projectActionResult.textContent = error.message;
    renderProjectBrowser();
  }
}

async function loadProjectDetail(projectId) {
  const sequence = ++state.taskRequestSequence;
  state.taskLoadError = "";
  if (!projectId) {
    state.selectedProject = null;
    renderProjectDetail();
    return;
  }
  try {
    const [project, files] = await Promise.all([
      requestJson("/api/v1/tasks/" + encodeURIComponent(projectId)
        + "?activity_limit=" + encodeURIComponent(state.taskActivityLimit)),
      requestJson("/api/v1/tasks/" + encodeURIComponent(projectId) + "/files"),
    ]);
    if (state.selectedProjectId !== projectId || sequence !== state.taskRequestSequence) {
      return;
    }
    if (project.task_id !== projectId) throw new Error("任务信息不匹配，请重新读取。");
    state.selectedProject = project;
    state.taskFiles = Array.isArray(files?.items) ? files.items : [];
    renderTaskPreferences(project);
    const url = new URL(window.location.href);
    if (state.activeModule === "projects" && url.searchParams.get("task") !== projectId) {
      history.replaceState({ task: projectId }, "", taskRouteUrl(projectId) + url.hash);
    }
    renderProjectDetail();
    if (state.activeModule === "projects" && document.visibilityState === "visible") {
      void markTaskSnapshotViewed(project);
    }
  } catch (error) {
    if (state.selectedProjectId !== projectId || sequence !== state.taskRequestSequence) return;
    state.selectedProject = null;
    state.taskFiles = [];
    state.taskLoadError = error.status === 404 ? "任务不可用，或你当前没有访问权限。" : error.message;
    renderProjectDetail();
  }
}

function taskRouteUrl(taskId) {
  const url = new URL(window.location.href);
  url.searchParams.set("module", "projects");
  url.searchParams.set("view", "board");
  if (taskId) url.searchParams.set("task", taskId);
  else url.searchParams.delete("task");
  url.hash = "";
  return `${url.pathname}${url.search}`;
}

function currentTaskForAction() {
  return state.selectedProject?.task_id === state.selectedProjectId ? state.selectedProject : null;
}

function acceptTaskUpdate(taskId, updated) {
  if (state.selectedProjectId !== taskId || updated?.task_id !== taskId) return false;
  ++state.taskRequestSequence;
  state.selectedProject = updated;
  return true;
}

function bindTaskAction(element, eventName, action) {
  let pending = false;
  element.addEventListener(eventName, async (event) => {
    if (pending) { event.preventDefault(); return; }
    pending = true;
    try { await action(event); } finally { pending = false; }
  });
}

async function selectTask(taskId, { updateHistory = true } = {}) {
  state.selectedProjectId = taskId;
  state.selectedProject = null;
  state.taskLoadError = "";
  state.taskActivityLimit = 200;
  state.taskRecordFilter = "discussion";
  state.taskFiles = [];
  state.taskFileQuery = "";
  state.taskFileUploader = "";
  state.taskFileType = "";
  state.taskFileMine = false;
  elements.taskFileSearch.value = "";
  elements.taskFileMine.checked = false;
  elements.taskAssignmentForm.reset();
  elements.projectActionResult.textContent = "";
  document.querySelectorAll(".task-settings, .task-compose-panel").forEach((item) => { item.open = false; });
  if (updateHistory) history.pushState({ task: taskId }, "", taskRouteUrl(taskId));
  renderProjectBrowser();
  updateCollaborationWorkspaceMode();
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  await loadProjectDetail(taskId);
  if (state.selectedProjectId === taskId && state.selectedProject) {
    elements.projectDetailTitle.focus({ preventScroll: true });
  }
}

async function loadFriends(query = "") {
  if (!state.dashboard) {
    return;
  }
  try {
    const suffix = query.trim() ? `?query=${encodeURIComponent(query.trim())}` : "";
    const [payload, suggestions] = await Promise.all([
      requestJson(`/api/v1/friends${suffix}`),
      requestJson(`/api/v1/friends/suggestions${suffix}`),
    ]);
    const formal = (Array.isArray(payload?.items) ? payload.items : []).map(
      (friend) => ({ ...friend, search_match: query.trim() }),
    );
    const suggested = (Array.isArray(suggestions?.items) ? suggestions.items : []).map(
      (friend) => ({ ...friend, search_match: query.trim() }),
    );
    const loaded = [...formal, ...suggested.filter(
      (candidate) => !formal.some((friend) => friend.human_user_id === candidate.human_user_id),
    )];
    state.friends = query.trim()
      ? [...loaded, ...state.friends.filter(
        (friend) => !loaded.some((match) => match.human_user_id === friend.human_user_id),
      )]
      : loaded;
    if (query.trim() && !formal.length && suggested.length) {
      state.friendFilter = "suggested";
    }
    if (!state.friendsLoaded && formal.some((friend) => friend.relation_status === "pending_incoming")) {
      state.friendFilter = "pending_incoming";
    }
    state.friendsLoaded = true;
    if (!friendById(state.selectedFriendId)) {
      state.selectedFriendId = isMobileWorkspace() ? "" : (state.friends[0]?.human_user_id || "");
    }
    renderFriendBrowser();
  } catch (error) {
    renderFriendBrowser();
    elements.friendDetailNote.textContent = error.message;
  }
}

function renderProjectBrowser({ detail = true } = {}) {
  const projects = filteredProjects();
  elements.projectBrowserCount.textContent = projects.length + " 个";
  elements.projectBrowserList.replaceChildren();
  projects.forEach((project) => {
    const pending = project.membership_status === "invited" ? "待确认" : "";
    elements.projectBrowserList.append(createCollaborationListButton({
      title: project.title,
      unread: project.unread_count > 0,
      meta: project.owner_display_name + "负责 · 更新 " + dateText(project.updated_at),
      badge: pending || projectStatusLabel(project),
      active: state.selectedProjectId === project.task_id,
      avatar: projectKind(project) === "一对一任务" ? "1" : "任",
      onClick: () => selectTask(project.task_id),
    }));
  });
  updateTaskNavDot();
  if (detail) renderProjectDetail();
}

function activityText(activity) {
  const target = activity.target_display_name || "成员";
  const labels = {
    created: "创建了任务",
    task_created: "创建了任务",
    member_invited: "邀请 " + target + " 加入任务",
    member_added: "将 " + target + " 加入任务",
    member_joined: "加入了任务",
    member_declined: "拒绝了任务邀请",
    member_left: "退出了任务，其 AI 未结束工作已取消",
    assignment_created: "创建了 AI 执行单元",
    assignment_cancelled: "取消了排队工作，历史记录保留",
    agent_joined_collaboration: "参与 AI 已进入协同队列",
    member_agents_selected: "更新了参与 AI",
    member_email_sent: "已向" + target + "的注册邮箱发送任务通知",
    member_email_failed: target + "的邮件通知发送失败，任务成员关系不受影响",
    run_leased: "已领取任务并准备协同",
    run_progress: "正在协同处理任务",
    run_waiting_human: "正在等待 Human 决策",
    human_run_response: "回复了 AI 的协作问题并继续执行",
    assignment_result: "提交了协同结果",
    human_work_continued: "由 Human 接续了工作",
    context_summary: "更新了任务摘要",
    run_claimed: "开始执行",
    run_updated: "更新了执行进度",
    result_submitted: "提交了执行结果",
    final_submitted: "提交任务等待验收",
    accepted: "验收通过",
    changes_requested: "要求修改",
    paused: "暂停了任务",
    resumed: "恢复了任务",
    archived: "归档了任务",
    restored: "恢复了任务",
    task_message: "发布了任务协作消息",
  };
  if (activity.kind === "agent_delivery") {
    return "提交了交付物：" + (activity.subject || "未命名交付物");
  }
  if (activity.kind === "agent_update") {
    return "更新了任务：" + (activity.subject || "未命名更新");
  }
  return labels[activity.kind] || "任务状态已更新";
}

function plainTaskExcerpt(value, limit = 180) {
  const text = (typeof value === "string" ? value : JSON.stringify(value ?? ""))
    .replace(/<[^>]*>/g, " ")
    .replace(/^\s{0,3}(?:#{1,6}\s+|>\s?)/gm, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\*\*([^*\n]+)\*\*/g, "$1").replace(/`([^`\n]+)`/g, "$1")
    .replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit).trimEnd()}…` : text;
}

function taskContentTitle(activity) {
  const raw = activity.metadata?.subject || activity.metadata?.body
    || activity.metadata?.instruction || activity.metadata?.summary || activityText(activity);
  const title = typeof raw === "string" ? raw.split(/\r?\n/).find((line) => line.trim()) : raw;
  return plainTaskExcerpt(title, 72) || "未命名内容";
}

function appendSafeTaskInline(container, text) {
  // Deliberately no HTML, link, image or script evaluation. Only text and emphasis.
  const parts = String(text).split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g);
  parts.forEach((part) => {
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("`") && part.endsWith("`"))) {
      const bold = part.startsWith("**");
      const node = document.createElement(bold ? "strong" : "code");
      node.textContent = part.slice(bold ? 2 : 1, bold ? -2 : -1);
      container.append(node);
    } else container.append(document.createTextNode(part));
  });
}

function createSafeTaskReading(body) {
  const reading = document.createElement("div");
  reading.className = "task-readable-body";
  let list = null;
  let code = null;
  for (const line of String(body ?? "").split(/\r?\n/)) {
    if (/^\s*```/.test(line)) {
      if (code) code = null;
      else { code = document.createElement("pre"); reading.append(code); }
      list = null;
      continue;
    }
    if (code) { code.textContent += `${line}\n`; continue; }
    if (!line.trim()) { list = null; continue; }
    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.*)$/);
    const bullet = line.match(/^\s*(?:([-+*])|\d+[.)])\s+(.*)$/);
    if (bullet) {
      const tag = bullet[1] ? "UL" : "OL";
      if (!list || list.tagName !== tag) { list = document.createElement(tag.toLowerCase()); reading.append(list); }
      const item = document.createElement("li");
      appendSafeTaskInline(item, bullet[2]);
      list.append(item);
      continue;
    }
    list = null;
    const quote = line.match(/^>\s?(.*)$/);
    const node = document.createElement(heading ? `h${Math.min(heading[1].length + 2, 6)}` : quote ? "blockquote" : "p");
    appendSafeTaskInline(node, heading ? heading[2] : quote ? quote[1] : line);
    reading.append(node);
  }
  return reading;
}

function createTaskActivityAttachment(activity, format, body) {
  const details = document.createElement("details");
  details.className = `task-activity-attachment format-${format}`;
  const summary = document.createElement("summary");
  const icon = document.createElement("span");
  icon.className = "task-activity-attachment-icon";
  icon.textContent = format === "json" ? "{}" : "⌑";
  const copy = document.createElement("span");
  const name = document.createElement("strong");
  name.textContent = "说了什么";
  const hint = document.createElement("small");
  const updateReadingHint = () => {
    hint.textContent = details.open ? "收起正文" : "展开阅读";
  };
  details.addEventListener("toggle", updateReadingHint);
  updateReadingHint();
  copy.append(name, hint);
  summary.append(icon, copy);
  const preview = document.createElement("pre");
  preview.className = "task-activity-attachment-preview";
  preview.textContent = format === "json" && typeof body !== "string"
    ? JSON.stringify(body, null, 2)
    : String(body ?? "");
  const original = document.createElement("details");
  original.className = "task-original-source";
  const originalLabel = document.createElement("summary");
  originalLabel.textContent = "查看原始正文";
  original.append(originalLabel, preview);
  details.append(summary);
  if (format === "markdown" || format === "text") details.append(createSafeTaskReading(body), original);
  else details.append(preview);
  return details;
}

function operationalTaskAssignments(project) {
  const latest = new Map();
  (project.assignments || [])
    .filter((assignment) => !["result_sync", "task_message"].includes(assignment.assignment_kind))
    .filter((assignment) => assignment.cancellation_reason !== "legacy_pre_0_1_44_backlog")
    .forEach((assignment) => {
      const source = assignment.assignment_kind === "participant_start"
        ? "participant"
        : (assignment.source_activity_id || assignment.assignment_id);
      const key = [source, assignment.responsible_human_user_id, assignment.assignee_agent_id].join(":");
      const previous = latest.get(key);
      if (!previous || String(previous.created_at) < String(assignment.created_at)) {
        latest.set(key, assignment);
      }
    });
  return [...latest.values()];
}

function visibleTaskAssignments(project) {
  return operationalTaskAssignments(project).filter((assignment) => (
    (["human_directed", "revision"].includes(assignment.assignment_kind)
      || assignment.run_status === "waiting_human")
      && assignment.status !== "cancelled"
  ));
}

function humanColorTone(humanUserId) {
  return [...String(humanUserId || "")]
    .reduce((value, character) => (value * 31 + character.charCodeAt(0)) % 6, 0);
}

function taskProgressSummary(assignment) {
  const raw = String(assignment.result_summary || assignment.instruction || "").trim();
  if (raw.length <= 320) {
    return { text: raw, truncated: false };
  }
  return { text: `${raw.slice(0, 320).trimEnd()}…`, truncated: true };
}

function taskExecutionStatusLabel(status) {
  return ({
    queued: "等待领取",
    leased: "已领取",
    starting: "正在启动",
    running: "执行中",
    waiting_human: "等待 Human",
    completed: "已完成",
    partial: "部分完成",
    failed: "执行异常",
    interrupted: "执行中断",
    cancelled: "已取消",
  })[status] || status || "状态待确认";
}

function taskAssignmentStatusLabel(assignment) {
  return assignment.cancellation_reason === "human_completed" ? "Human 已补交结果" : taskExecutionStatusLabel(assignment.run_status || assignment.status);
}

function taskAgentDisplayName(agent) {
  return safeText(agent?.display_name, agent?.handle || agent?.address || "AI");
}

function assignmentStatusChangedAt(project, assignment) {
  const statusKinds = new Set([
    "run_leased", "run_progress", "run_waiting_human", "assignment_result", "human_run_response", "human_work_continued",
  ]);
  const activity = (project.activities || []).filter((item) => (
    statusKinds.has(item.kind)
      && String(item.metadata?.assignment_id || "") === String(assignment.assignment_id)
  )).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))[0];
  return activity?.created_at || assignment.updated_at || assignment.created_at;
}

function historicalTaskWork(project, assignment, now = Date.now()) {
  if (["waiting_human", "running", "starting", "leased"].includes(assignment.run_status)) return false;
  if (["completed", "cancelled"].includes(assignment.status)) return true;
  const changed = Date.parse(assignmentStatusChangedAt(project, assignment));
  return Number.isFinite(changed) && now - changed >= 7 * 24 * 60 * 60 * 1000;
}

function latestTaskCollaboration(project) {
  const kinds = new Set(["task_message", "human_work_continued", "assignment_result", "final_submitted", "accepted", "changes_requested"]);
  return [...(project.activities || [])].filter((item) => kinds.has(item.kind))
    .sort((a, b) => Number(b.task_sequence || 0) - Number(a.task_sequence || 0)
      || String(b.created_at).localeCompare(String(a.created_at))).slice(0, 5);
}

function renderLatestTaskCollaboration(project) {
  const section = document.querySelector("#task-latest");
  section.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "最新协作";
  const note = document.createElement("p");
  note.className = "task-files-note";
  note.textContent = "最近 5 条交流与结果，最新在前；以下为原文摘录，不代表已确认结论。";
  section.append(heading, note);
  const items = latestTaskCollaboration(project);
  if (!items.length) {
    const empty = document.createElement("p");
    empty.textContent = "还没有交流或结果。";
    section.append(empty);
  }
  items.forEach((activity) => {
    const card = document.createElement("article");
    card.className = `task-latest-item human-tone-${humanColorTone(activity.actor_human_user_id)}`;
    const byline = document.createElement("div");
    byline.className = "task-latest-byline";
    const who = document.createElement("strong");
    who.textContent = activity.actor_display_name || "任务成员";
    const time = document.createElement("time");
    time.textContent = dateText(activity.created_at);
    byline.append(who, time);
    const meta = activity.metadata || {};
    const title = document.createElement("strong");
    const kind = activity.kind === "task_message" ? (meta.reply_to_activity_id ? "回复" : "发起讨论") : ({ human_work_continued: meta.action === "complete" ? "Human 补交结果" : "Human 更换执行 AI", assignment_result: "AI 提交结果", final_submitted: "提交任务验收", accepted: "Human 已验收", changes_requested: "要求修改" })[activity.kind];
    title.textContent = `${kind} · ${meta.subject || "任务更新"}`;
    const text = document.createElement("p");
    const body = meta.body ?? meta.result_summary ?? meta.summary ?? meta.note ?? "请查看原记录。";
    text.textContent = plainTaskExcerpt(typeof body === "string" ? body : JSON.stringify(body), 220);
    card.append(byline, title);
    if (activity.actor_agent_display_name) {
      const agent = document.createElement("small");
      agent.className = "task-latest-agent";
      agent.textContent = `通过 ${activity.actor_agent_display_name}`;
      card.append(agent);
    }
    card.append(text);
    appendTaskRecordLink(card, activity.activity_id, "查看原文及上下文", "all");
    section.append(card);
  });
}

function checkpointHumanPrompt(checkpoint) {
  if (!checkpoint || typeof checkpoint !== "object" || !Object.keys(checkpoint).length) {
    return "AI 没有说明需要确认的具体问题，请在回复中要求 AI 补充。";
  }
  for (const key of ["question", "human_request", "request", "message", "summary", "reason"]) {
    const value = checkpoint[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return JSON.stringify(checkpoint, null, 2);
}

function taskRecordTarget(project, assignment) {
  const activity = (project.activities || []).find((item) => (
    String(item.metadata?.assignment_id || "") === String(assignment.assignment_id)
      && ["assignment_result", "run_waiting_human", "assignment_created"].includes(item.kind)
  ));
  return activity?.activity_id || null;
}

function taskDiscussionGroups(activities) {
  const byId = new Map(activities.map((item) => [item.activity_id, item]));
  const groups = new Map();
  for (const activity of activities) {
    let root = activity;
    const seen = new Set([root.activity_id]);
    while (byId.has(root.metadata?.reply_to_activity_id)) {
      const parent = byId.get(root.metadata.reply_to_activity_id);
      if (seen.has(parent.activity_id)) break;
      seen.add(parent.activity_id);
      root = parent;
    }
    const group = groups.get(root.activity_id) || [];
    group.push(activity);
    groups.set(root.activity_id, group);
  }
  return [...groups.values()].map((group) => group.sort((a, b) => (
    a.created_at.localeCompare(b.created_at) || a.activity_id.localeCompare(b.activity_id)
  ))).sort((a, b) => b.at(-1).created_at.localeCompare(a.at(-1).created_at));
}

function suggestedTaskReplyParent(project, activity) {
  if (activity.kind !== "task_message" || activity.metadata?.reply_to_activity_id
      || activity.metadata?.reply_suggestion_dismissed || !activity.actor_agent_display_name) {
    return null;
  }
  const childTime = Date.parse(activity.created_at);
  return (project.activities || []).find((candidate) => {
    const age = childTime - Date.parse(candidate.created_at);
    return candidate.kind === "task_message"
      && candidate.activity_id !== activity.activity_id
      && candidate.actor_display_name !== activity.actor_display_name
      && age > 0
      && age <= 2 * 60 * 60 * 1000;
  }) || null;
}

async function decideTaskReplyRelation(childActivityId, parentActivityId, decision) {
  const project = state.selectedProject;
  if (!project) return;
  const updated = await requestJson(
    `/api/v1/tasks/${encodeURIComponent(project.task_id)}/activity-relations/reply`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({
        child_activity_id: childActivityId,
        parent_activity_id: parentActivityId,
        decision,
      }),
    },
  );
  if (state.selectedProjectId === updated.task_id) {
    state.selectedProject = updated;
    renderProjectDetail();
  }
}

async function openTaskContext(project) {
  const dialog=document.createElement("dialog");
  dialog.className="task-context-dialog";
  const heading=document.createElement("h2");heading.textContent="协作简报与检索";
  const close=document.createElement("button");close.textContent="关闭";close.onclick=()=>dialog.close();
  const form=document.createElement("form");
  const label=document.createElement("label");label.textContent="搜索讨论关键词";
  const input=document.createElement("input");input.maxLength=100;input.type="search";label.append(input);
  const search=document.createElement("button");search.textContent="查找";form.append(label,search);
  const content=document.createElement("div");
  const status=document.createElement("p");status.setAttribute("role","status");
  const copy=document.createElement("button");copy.textContent="复制简报";
  const download=document.createElement("button");download.textContent="导出 Markdown";
  const more=document.createElement("button");more.textContent="更多原文";more.hidden=true;
  let cursor="", markdown="", busy=false, snapshot=null;
  async function load(append=false) {
    if(busy)return;
    busy=true;search.disabled=true;more.disabled=true;status.textContent="正在读取…";
    try {
      const data=await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/context?query=${encodeURIComponent(input.value.trim())}${append && cursor ? `&before=${encodeURIComponent(cursor)}` : ""}`);
      snapshot=data;
      if(!append) {
        content.replaceChildren();
        for (const saved of [data.confirmed_summary, data.summary].filter((item, index, items)=>item && items.findIndex(x=>x?.activity_id===item.activity_id)===index)) {
          const box=document.createElement("article");
          const title=document.createElement("h3");title.textContent=`${saved.confirmed ? "Human 已确认摘要" : "待确认整理稿"}${saved.stale ? " · 来源之后有新记录，请复核" : ""}`;
          box.append(title);
          for(const [key,label] of [["conclusions","结论"],["open_questions","开放问题"],["next_steps","下一步"]]) {
            const p=document.createElement("p");p.className="content";p.textContent=`${label}：${saved[key] || "未填写"}`;box.append(p);
          }
          saved.source_activity_ids.forEach((id,index)=>{const link=document.createElement("button");link.textContent=`来源 ${index+1}`;link.onclick=()=>{dialog.close();openTaskFileSource(id,"all");};box.append(link);});content.append(box);
        }
        markdown=`# ${data.title}

任务：${data.task_id}

目标：${data.goal}

预期产出：${data.expected_output}

状态：${projectStatusLabel(data)}

${data.guidance}

`;
        if(data.summary) markdown+=`摘要：${data.summary.confirmed?"Human 已确认":"待确认整理稿"}${data.summary.stale?"（需复核新记录）":""}\n结论：${data.summary.conclusions}\n开放问题：${data.summary.open_questions}\n下一步：${data.summary.next_steps}\n\n`;
        const summary=document.createElement("p");summary.className="content";summary.textContent=`${data.title}\n目标：${data.goal}\n预期产出：${data.expected_output}\n状态：${projectStatusLabel(data)}\n${data.guidance}`;content.append(summary);
        data.work.forEach(work=>{const p=document.createElement("p");p.textContent=`${work.responsible_human} · ${taskExecutionStatusLabel(work.status)} · ${work.instruction}`;content.append(p);markdown+=p.textContent+"\n\n";});
      }
      data.sources.forEach(source=>{
        const article=document.createElement("article");
        const text=document.createElement("p");text.className="content";text.textContent=`${source.author} · ${source.subject || activityText({kind:source.kind})} · ${dateText(source.created_at)}
${source.excerpt}${source.truncated ? "（摘录，查看原文继续）" : ""}`;
        const link=document.createElement("a");link.href=source.source_url;link.textContent="查看原文";
        link.onclick=async(event)=>{event.preventDefault();dialog.close();await openTaskFileSource(source.activity_id, "all");};
        article.append(text,link);content.append(article);
        markdown+=`## ${source.subject || activityText({kind:source.kind})}

${source.excerpt}

[原文](${location.origin}${source.source_url})

`;
      });
      cursor=data.next_cursor || "";more.hidden=!cursor;
      status.textContent=cursor?"当前为部分记录，可继续加载；导出包含已加载记录。":"当前检索结果已加载完毕。";
    } catch(error) {status.textContent=error.message;} finally {busy=false;search.disabled=false;more.disabled=false;}
  }
  form.onsubmit=event=>{event.preventDefault();load();};
  more.onclick=()=>load(true);
  copy.onclick=async()=>{try{await navigator.clipboard.writeText(markdown);status.textContent="简报已复制。";}catch{status.textContent="复制未完成，请使用导出 Markdown。";}};
  download.onclick=()=>{const url=URL.createObjectURL(new Blob([markdown],{type:"text/markdown;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="AgentPost-协作简报.md";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  const edit=document.createElement("details");const editTitle=document.createElement("summary");editTitle.textContent="整理或更新摘要";edit.append(editTitle);
  const editForm=document.createElement("form");const fields={};
  for(const [key,name] of [["conclusions","结论"],["open_questions","开放问题"],["next_steps","下一步"]]) {
    const label=document.createElement("label");label.textContent=name;const input=document.createElement("textarea");input.maxLength=5000;label.append(input);fields[key]=input;editForm.append(label);
  }
  const confirmLabel=document.createElement("label");const confirm=document.createElement("input");confirm.type="checkbox";confirm.disabled=project.membership_role!=="owner";confirmLabel.append(confirm,document.createTextNode("作为任务负责人确认以上摘要（不代表验收任务）"));editForm.append(confirmLabel);
  const instruction=document.createElement("p");instruction.textContent="摘要引用当前这页检索结果；请先查找并核对原文。未勾选确认则保存为整理稿。";
  const save=document.createElement("button");save.textContent="保存摘要";editForm.append(instruction,save);
  editForm.onsubmit=async(event)=>{event.preventDefault();if(!snapshot?.sources.length){status.textContent="请先检索到可引用的原文。";return;}save.disabled=true;try{
    await requestJson(`/api/v1/tasks/${project.task_id}/context-summary`,{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":state.csrfToken},body:JSON.stringify({conclusions:fields.conclusions.value,open_questions:fields.open_questions.value,next_steps:fields.next_steps.value,confirmed:confirm.checked,source_activity_ids:snapshot.sources.map(x=>x.activity_id),based_on_activity_id:snapshot.sources[0].activity_id})});
    edit.open=false;await load();
  }catch(error){status.textContent=error.message;}finally{save.disabled=false;}};
  edit.append(editForm);
  dialog.append(heading,close,form,status,copy,download,content,more,edit);
  dialog.addEventListener("close",()=>dialog.remove(),{once:true});
  document.body.append(dialog);dialog.showModal();await load();
}

function revealTaskRecord(activityId) {
  const target = document.getElementById(`task-activity-${activityId}`);
  if (!target) return;
  for (let parent = target.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === "DETAILS") parent.open = true;
  }
  target.tabIndex = -1;
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: "center", behavior: "smooth" });
}

function openTaskRecord(activityId, filter = "all") {
  state.taskRecordFilter = filter;
  renderProjectDetail();
  requestAnimationFrame(() => revealTaskRecord(activityId));
}

function appendTaskRecordLink(container, activityId, label = "查看任务记录", filter = "all") {
  if (!activityId) return;
  const link = document.createElement("a");
  link.className = "task-record-link";
  link.href = `${taskRouteUrl(state.selectedProjectId)}#task-activity-${activityId}`;
  link.textContent = label;
  link.addEventListener("click", (event) => {
    event.preventDefault();
    openTaskRecord(activityId, filter);
  });
  container.append(link);
}

function taskMessageRecipientLabel(project, recipient) {
  const status = recipient.status === "legacy_delivered"
    ? "兼容投递，尚无自动执行"
    : recipient.status === "context_available" ? "可查看" : "状态待确认";
  for (const member of project.members || []) {
    const agent = (member.agents || []).find((item) => item.agent_id === recipient.agent_id);
    if (agent) {
      return `${member.display_name} · ${agent.display_name}：${status}`;
    }
  }
  return `历史参与 AI：${status}`;
}

function taskMessageRecipientSummary(recipients) {
  const humans = new Set(recipients.map((item) => item.human_user_id).filter(Boolean));
  const hasUnknownHuman = recipients.some((item) => !item.human_user_id);
  const label = hasUnknownHuman ? `共享范围：${recipients.length} 个 AI` : `共享给 ${humans.size} 人`;
  const legacy = recipients.filter((item) => item.status === "legacy_delivered").length;
  const unknown = recipients.filter((item) => !["context_available", "legacy_delivered"].includes(item.status)).length;
  return label + (legacy ? ` · ${legacy} 个 AI 兼容投递` : "")
    + (unknown ? ` · ${unknown} 个状态待确认` : "");
}

function taskMessageAudienceLabel(project, activity) {
  const recipients = Array.isArray(activity.metadata?.recipient_statuses)
    ? activity.metadata.recipient_statuses
    : [];
  const humanIds = [...new Set(recipients.map((item) => item.human_user_id).filter(Boolean))];
  const names = humanIds.map((id) => (
    (project.members || []).find((member) => String(member.human_user_id) === String(id))?.display_name
  )).filter(Boolean);
  if (!humanIds.length) return "任务成员（具体范围待确认）";
  if (names.length !== humanIds.length) return `${humanIds.length} 位任务成员`;
  if (names.length <= 3) return names.join("、");
  return `${names.slice(0, 2).join("、")}等 ${names.length} 位任务成员`;
}

function taskMessageTopic(project, activity) {
  const parentId = activity.metadata?.reply_to_activity_id;
  if (parentId) {
    const original = (project.activities || []).find((item) => item.activity_id === parentId);
    return {
      label: "回应对象",
      value: original
        ? `${original.actor_display_name || "任务成员"} 的「${taskContentTitle(original)}」`
        : "较早的任务消息（原记录暂不可用）",
    };
  }
  const subject = plainTaskExcerpt(activity.metadata?.subject || "", 64);
  return subject ? { label: "讨论主题", value: subject } : null;
}

function appendTaskMessageContext(container, project, activity) {
  const topic = taskMessageTopic(project, activity);
  if (topic) appendTaskMessageFact(container, topic.label, topic.value, "reason");
  appendTaskMessageFact(container, "共享范围", taskMessageAudienceLabel(project, activity), "audience");
}

function appendTaskMessageFact(container, label, value, className = "") {
  const fact = document.createElement("span");
  fact.className = `task-message-fact ${className}`.trim();
  const name = document.createElement("b");
  name.textContent = label;
  const content = document.createElement("span");
  content.textContent = value;
  fact.append(name, content);
  container.append(fact);
}

function syncTaskPrimaryAgentOptions(preferredAgentId = "") {
  const selected = Array.from(
    elements.taskMyAgentOptions.querySelectorAll('input[name="task-my-agent"]:checked'),
  );
  const previous = preferredAgentId || elements.taskMyPrimaryAgent.value;
  elements.taskMyPrimaryAgent.replaceChildren();
  selected.forEach((input) => {
    const option = document.createElement("option");
    option.value = input.value;
    option.textContent = input.dataset.agentName;
    option.selected = String(input.value) === String(previous);
    elements.taskMyPrimaryAgent.append(option);
  });
  if (selected.length && !elements.taskMyPrimaryAgent.value) {
    elements.taskMyPrimaryAgent.value = selected[0].value;
  }
  elements.taskMyPrimaryAgent.disabled = !selected.length;
}

function taskStateAxesLabel(project) {
  const axes = project.state_axes;
  if (!axes) {
    return "状态待同步";
  }
  const acceptanceLabels = {
    not_ready: "尚未提交",
    pending: "等待 Human 验收",
    accepted: "Human 已验收",
    changes_requested: "Human 要求修改",
    cancelled: "验收已取消",
  };
  return acceptanceLabels[axes.human_acceptance_status] || "验收待同步";
}

function showTaskSection(id) {
  const section = document.getElementById(id);
  if (!section || section.hidden) return;
  if (section.tagName === "DETAILS") section.open = true;
  if (id === "task-submission-blockers") section.querySelector("details")?.setAttribute("open", "");
  let parent = section.parentElement;
  while (parent) {
    if (parent.tagName === "DETAILS") parent.open = true;
    parent = parent.parentElement;
  }
  section.querySelector(".task-compose-panel")?.setAttribute("open", "");
  section.scrollIntoView({ block: "start", behavior: "auto" });
  if (!section.hasAttribute("tabindex")) section.setAttribute("tabindex", "-1");
  section.focus({ preventScroll: true });
}

function taskSubmissionBlockers(project) {
  // Match the server's submit gate; do not hide unfinished participation or history.
  return (project.assignments || []).filter((item) => !["completed", "cancelled"].includes(item.status));
}

function taskHumanActions(project, userId, now = Date.now()) {
  const owner = String(project.owner_human_user_id) === String(userId);
  const actions = visibleTaskAssignments(project)
    .filter((item) => item.run_status === "waiting_human"
      && (owner || String(item.responsible_human_user_id) === String(userId)))
    .map((item) => ({
      label: "回答并继续",
      title: item.assignment_kind === "participant_start"
        ? `${item.responsible_human_display_name || "参与 AI"} · 参与准备需要你回答`
        : plainTaskExcerpt(item.instruction, 100) || "AI 等待你的回答",
      reason: plainTaskExcerpt(checkpointHumanPrompt(item.run_checkpoint), 240),
      target: `task-work-${item.assignment_id}`,
    }));
  if(project.status==="active") visibleTaskAssignments(project).filter(item=>
    item.assignment_kind==="human_directed" && item.status==="queued" && item.run_status==="queued"
    && (owner || String(item.responsible_human_user_id)===String(userId))
    && now-Date.parse(item.updated_at || item.created_at)>=30*60*1000
  ).forEach(item=>actions.push({
    label:"查看接续方式",title:plainTaskExcerpt(item.instruction,100) || "工作等待接续",
    reason:"这项工作已等待领取超过30分钟，可在原工作卡补交结果或更换已授权AI。",
    target:`task-work-${item.assignment_id}`,
  }));
  if (owner && project.status === "awaiting_acceptance") actions.push({
    label: "查看并验收", title: "任务成果等待你确认",
    reason: "查看提交的成果，选择接受或要求修改。", target: "task-review-controls",
  });
  return actions;
}

function renderTaskAttention(project, ownerAccess) {
  const attention = document.querySelector("#task-attention");
  attention.replaceChildren();
  const userId = String(state.dashboard?.user?.id || "");
  const actions = taskHumanActions(project, userId);
  attention.hidden = !actions.length;
  const title = document.createElement("strong");
  title.textContent = `需要我处理 · ${actions.length} 项`;
  attention.append(title);
  actions.forEach((action) => {
    const card = document.createElement("div");
    card.className = "task-attention-item";
    const heading = document.createElement("strong");
    heading.textContent = action.title;
    const reason = document.createElement("p");
    reason.textContent = action.reason;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quiet-button";
    button.textContent = action.label;
    button.addEventListener("click", () => showTaskSection(action.target));
    card.append(heading, reason, button);
    attention.append(card);
  });
  const blockers = document.querySelector("#task-submission-blockers");
  blockers.replaceChildren();
  const pending = taskSubmissionBlockers(project);
  if (pending.length) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `提交前待处理 · ${pending.length} 项`;
    const note = document.createElement("p");
    note.textContent = "当前提交规则要求以下执行全部结束。参与准备与明确工作分别列出；日报或讨论中的完成自述不会替代执行结果。";
    details.append(summary, note);
    pending.forEach((item) => {
      const row = document.createElement("p");
      row.textContent = `${item.responsible_human_display_name} · ${item.assignment_kind === "participant_start" ? "参与准备" : "工作"} · ${taskAssignmentStatusLabel(item)}\n${taskProgressSummary(item).text}`;
      appendTaskRecordLink(row, taskRecordTarget(project, item), "查看相关记录", "all");
      details.append(row);
    });
    blockers.append(details);
  }
  document.querySelectorAll("[data-task-target]").forEach((button) => {
    let target = button.dataset.taskTarget;
    if (target === "task-submission-controls") {
      target = project.status === "awaiting_acceptance" ? "task-review-controls"
        : project.status === "completed" ? "task-completed-result" : target;
    }
    button.hidden = Boolean(document.getElementById(target)?.hidden);
    button.onclick = () => showTaskSection(target);
  });
}

function attachmentPreviewType(contentType, filename = "") {
  const declared = safeText(contentType, "").split(";", 1)[0].trim().toLowerCase();
  if (["application/zip", "application/x-zip-compressed"].includes(declared) && String(filename).toLowerCase().endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (declared === "application/x-zip-compressed") return "application/zip";
  const known = ["text/markdown", "text/x-markdown", "application/markdown", "text/html",
    "application/json", "application/pdf", "application/zip", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
  if (known.includes(declared)) return declared;
  const suffix = String(filename).toLowerCase().match(/\.[^.\/]+$/)?.[0];
  return ({ ".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain",
    ".json": "application/json", ".html": "text/html", ".htm": "text/html",
    ".zip": "application/zip", ".pdf": "application/pdf", ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document" })[suffix] || declared;
}

function taskFileTypeLabel(contentType, filename = "") {
  const type = attachmentPreviewType(contentType, filename);
  if (["text/markdown", "text/x-markdown", "application/markdown"].includes(type)) return "Markdown";
  if (type === "application/json") return "JSON";
  if (type === "text/html") return "HTML";
  if (type === "application/pdf") return "PDF";
  if (["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(type)) return "Word";
  if (type === "application/zip") return "ZIP 压缩包";
  if (type.startsWith("text/")) return "文本";
  return type ? "其他" : "未知类型";
}

async function openTaskFileSource(activityId, filter = "discussion") {
  let project = currentTaskForAction();
  if (!project) return;
  const loaded = () => (project.activities || []).some(
    (activity) => String(activity.activity_id) === String(activityId),
  );
  if (!loaded() && project.activities_truncated && state.taskActivityLimit < 2000) {
    state.taskActivityLimit = 2000;
    await loadProjectDetail(project.task_id);
    project = currentTaskForAction();
  }
  if (project && loaded()) {
    openTaskRecord(activityId, filter);
  } else {
    elements.projectActionResult.textContent = "来源记录较早，当前页面未能定位；文件仍可直接预览或下载。";
  }
}

function renderTaskFiles(project) {
  const allFiles = state.taskFiles || [];
  const previousUploader = state.taskFileUploader;
  const previousType = state.taskFileType;
  const uploaders = [...new Map(allFiles.map((file) => [
    String(file.uploader_human_user_id || file.uploader_display_name),
    file.uploader_display_name,
  ])).entries()].sort((a, b) => a[1].localeCompare(b[1], "zh-CN"));
  const types = [...new Set(allFiles.map((file) => taskFileTypeLabel(file.content_type, file.filename)))].sort();
  elements.taskFileUploader.replaceChildren(new Option("全部上传人", ""));
  uploaders.forEach(([value, label]) => elements.taskFileUploader.append(new Option(label, value)));
  elements.taskFileUploader.value = previousUploader;
  elements.taskFileType.replaceChildren(new Option("全部类型", ""));
  types.forEach((label) => elements.taskFileType.append(new Option(label, label)));
  elements.taskFileType.value = previousType;

  const query = state.taskFileQuery.toLocaleLowerCase("zh-CN");
  const currentHumanId = String(state.dashboard?.user?.id || "");
  const files = allFiles.filter((file) => {
    const uploaderKey = String(file.uploader_human_user_id || file.uploader_display_name);
    const searchable = `${file.filename} ${file.source_subject || ""}`.toLocaleLowerCase("zh-CN");
    return (!query || searchable.includes(query))
      && (!state.taskFileUploader || uploaderKey === state.taskFileUploader)
      && (!state.taskFileType || taskFileTypeLabel(file.content_type, file.filename) === state.taskFileType)
      && (!state.taskFileMine || String(file.uploader_human_user_id) === currentHumanId);
  });
  const filtersActive = Boolean(
    state.taskFileQuery || state.taskFileUploader || state.taskFileType || state.taskFileMine,
  );
  elements.taskFileCount.textContent = filtersActive
    ? `匹配 ${files.length} / 共 ${allFiles.length}`
    : String(allFiles.length);
  elements.taskFileClear.hidden = !filtersActive;
  elements.taskFileList.replaceChildren();
  if (!allFiles.length) {
    elements.taskFileList.append(emptyState("这个任务还没有已关联的文件。"));
    return;
  }
  if (!files.length) {
    elements.taskFileList.append(emptyState("没有符合当前筛选条件的文件。"));
    return;
  }
  files.forEach((file) => {
    const card = document.createElement("article");
    card.className = "task-file-card";
    const heading = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = safeText(file.filename, "未命名附件");
    const type = document.createElement("span");
    type.className = "data-chip";
    type.textContent = taskFileTypeLabel(file.content_type, file.filename);
    heading.append(title, type);
    const meta = document.createElement("p");
    meta.textContent = `${file.uploader_display_name} · 通过 ${file.uploader_agent_display_name} · ${dateText(file.uploaded_at)} · ${formatFileSize(file.size)}`;
    const source = document.createElement("p");
    source.className = "task-file-source";
    source.textContent = `来源：${file.source_subject || "未命名讨论"}`;
    const actions = document.createElement("div");
    actions.className = "task-file-actions";
    const attachment = { ...file, id: file.attachment_id };
    const normalizedType = attachmentPreviewType(file.content_type, file.filename);
    const previewable = new Set([
      "application/json", "application/markdown", "application/pdf", "text/html", "application/zip",
      "text/markdown", "text/plain", "text/x-markdown", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]).has(normalizedType);
    if (previewable) {
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "text-button";
      preview.textContent = normalizedType === "application/zip" ? "查看目录"
        : normalizedType === "application/pdf" ? "打开预览" : "查看内容";
      preview.addEventListener("click", () => openAttachmentPreview(attachment));
      actions.append(preview);
    }
    const download = document.createElement("a");
    download.className = "task-record-link";
    download.href = `/api/v1/orbit/attachments/${encodeURIComponent(file.attachment_id)}`;
    download.download = safeText(file.filename, "attachment");
    download.textContent = "下载";
    const locate = document.createElement("button");
    locate.type = "button";
    locate.className = "text-button";
    locate.textContent = "查看来源讨论";
    locate.addEventListener("click", () => void openTaskFileSource(file.source_activity_id));
    actions.append(download, locate);
    card.append(heading, meta, source, actions);
    elements.taskFileList.append(card);
  });
}

function renderProjectDetail() {
  const project = state.selectedProjectId === state.selectedProject?.task_id
    ? state.selectedProject
    : null;
  elements.projectEmpty.hidden = Boolean(state.selectedProjectId);
  elements.projectDetail.hidden = !state.selectedProjectId;
  const content = document.querySelector("#task-detail-content");
  const loading = document.querySelector("#task-detail-loading");
  content.hidden = !project;
  content.inert = !project;
  loading.hidden = Boolean(project);
  loading.querySelector("p").textContent = state.taskLoadError || "正在读取任务…";
  loading.querySelector("button").hidden = !state.taskLoadError;
  elements.projectDetail.setAttribute("aria-busy", String(!project && !state.taskLoadError));
  if (!state.selectedProjectId) {
    return;
  }
  if (!project) {
    elements.projectDetailTitle.textContent = "正在读取任务";
    elements.projectDetailDescription.textContent = "请稍候…";
    return;
  }
  const owner = project.members.find((member) => member.role === "owner");
  const ownerAccess = project.membership_role === "owner" && project.membership_status === "active";
  const invited = project.membership_status === "invited";
  elements.projectInvitationActions.hidden = !invited;
  elements.projectDetailType.textContent = projectKind(project);
  elements.projectDetailTitle.textContent = project.title;
  elements.projectTaskId.textContent = project.task_id;
  elements.projectDetailDescription.textContent = project.goal + "\n预期交付：" + project.expected_output;
  elements.projectDetailStatus.textContent = invited ? "待确认" : projectStatusLabel(project);
  elements.projectDetailStatus.classList.toggle("archived", project.status === "archived");
  elements.projectOwner.textContent = project.owner_display_name;
  elements.projectMemberCount.textContent = project.active_member_count + " 人"
    + (project.invited_member_count ? " · " + project.invited_member_count + " 人待确认" : "");
  elements.projectDue.textContent = dateOnlyText(project.due_at);
  elements.projectStateAxes.textContent = taskStateAxesLabel(project);
  const memberAccess = project.membership_status === "active";
  elements.projectInvite.hidden = !memberAccess;
  elements.projectMemberInvite.hidden = !memberAccess;
  elements.projectInvite.disabled = project.status === "archived";
  elements.projectMemberInvite.disabled = project.status === "archived";
  elements.projectArchive.hidden = !ownerAccess;
  const canSubmit = ownerAccess && project.status === "active";
  const canReview = ownerAccess && project.status === "awaiting_acceptance";
  elements.taskOwnerControls.hidden = !canSubmit;
  elements.taskSubmissionControls.hidden = !canSubmit;
  elements.taskReviewControls.hidden = !canReview;
  elements.taskCompletedResult.hidden = project.status !== "completed";
  elements.taskFinalSummary.value = project.final_summary || "";
  elements.taskReviewSummary.textContent = project.final_summary || "尚未填写交付说明";
  elements.taskCompletedSummary.textContent = project.final_summary || "任务结果已验收通过。";
  elements.taskReviewNote.value = "";
  elements.taskAssignmentOutputInherited.textContent = project.expected_output;
  const operationalAssignments = operationalTaskAssignments(project);
  const visibleAssignments = visibleTaskAssignments(project);
  const unfinishedAssignments = (project.assignments || []).filter(
    (assignment) => !["completed", "cancelled"].includes(assignment.status),
  ).length;
  elements.taskSubmitFinal.disabled = unfinishedAssignments > 0;
  elements.taskSubmissionHelp.textContent = unfinishedAssignments > 0
    ? `还有 ${unfinishedAssignments} 个 AI 执行单元未完成。查看“提交前待处理”了解具体原因。`
    : "提交后任务进入“待验收”，不能再创建新的 AI 执行单元。";
  renderTaskAssignmentForm(project);
  renderTaskFiles(project);
  elements.projectArchive.textContent = project.status === "paused" ? "继续任务" : "暂停任务";

  elements.projectAcceptAgentOptions.replaceChildren();
  if (invited) {
    ownedTaskAgents().forEach((agent, index) => {
      const label = document.createElement("label");
      label.className = "project-invite-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "task-accept-agent";
      input.value = agent.id;
      input.checked = index === 0;
      label.append(input, document.createTextNode(agentDisplayName(agent)));
      elements.projectAcceptAgentOptions.append(label);
    });
  }

  const currentUserId = String(state.dashboard?.user?.id || "");
  const currentMember = project.members.find(
    (member) => String(member.human_user_id) === currentUserId,
  );
  elements.taskMyAgentOptions.replaceChildren();
  const selectedAgentIds = new Set((currentMember?.agents || []).map((agent) => String(agent.agent_id)));
  ownedTaskAgents().forEach((agent) => {
    const label = document.createElement("label");
    label.className = "task-agent-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = "task-my-agent";
    input.value = agent.id;
    input.dataset.agentName = taskAgentDisplayName(agent);
    input.checked = selectedAgentIds.has(String(agent.id));
    input.addEventListener("change", () => syncTaskPrimaryAgentOptions());
    const copy = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = taskAgentDisplayName(agent);
    const capability = document.createElement("small");
    capability.textContent = Array.isArray(agent.capabilities) && agent.capabilities.length
      ? agent.capabilities.join(" · ")
      : "暂未声明能力";
    copy.append(name, capability);
    label.append(input, copy);
    elements.taskMyAgentOptions.append(label);
  });
  syncTaskPrimaryAgentOptions(currentMember?.primary_agent_id || "");
  elements.taskMyAgentForm.hidden = !currentMember || !ownedTaskAgents().length;
  elements.taskAddAgent.hidden = !currentMember;
  elements.taskMyAgentHelp.textContent = currentMember?.agent_selection_source === "default"
    ? "当前由默认 AI 自动参与；可以继续勾选其他自己的 AI，并指定主要 AI。"
    : `当前有 ${selectedAgentIds.size} 个 AI 参与；新增选择会进入协同队列。`;

  elements.projectMemberList.replaceChildren();
  [...project.members].sort((left, right) => {
    if (left.role === right.role) {
      return left.invited_at.localeCompare(right.invited_at);
    }
    return left.role === "owner" ? -1 : 1;
  }).forEach((member) => {
    const friend = friendById(member.human_user_id);
    const row = document.createElement(friend ? "button" : "article");
    if (friend) {
      row.type = "button";
    }
    row.className = "project-member-row" + (friend ? " interactive" : "");
    const avatar = document.createElement("span");
    avatar.className = "project-member-avatar" + (member.role === "owner" ? " current" : "");
    avatar.textContent = member.role === "owner" ? "负" : member.display_name.slice(0, 1);
    const copy = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = member.display_name + (member.role === "owner" ? " · 负责人" : "");
    const agent = document.createElement("small");
    const selectedAgents = Array.isArray(member.agents) ? member.agents : [];
    const source = member.agent_selection_source === "default" ? " · 默认选择" : " · Human 选择";
    const email = member.email_notification_status === "sent" ? " · 邮件已通知"
      : (member.email_notification_status === "failed" ? " · 邮件发送失败" : "");
    agent.textContent = member.status === "invited"
      ? "历史邀请待处理"
      : (selectedAgents.length
        ? selectedAgents.map((item) => item.display_name + (item.role === "primary" ? "（主）" : "")).join("、") + source + email
        : "尚未选择 AI");
    copy.append(name, agent);
    row.append(avatar, copy);
    if (friend) {
      const arrow = document.createElement("span");
      arrow.className = "project-member-arrow";
      arrow.textContent = "›";
      row.append(arrow);
      row.addEventListener("click", () => {
        state.selectedFriendId = friend.human_user_id;
        activateRoute("friends", "directory", { focusContent: true });
        renderFriendBrowser();
      });
    }
    elements.projectMemberList.append(row);
  });
  if (!owner && project.members.length === 0) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = "当前任务还没有成员信息。";
    elements.projectMemberList.append(empty);
  }

  elements.projectCollaborationList.replaceChildren();
  renderLatestTaskCollaboration(project);
  const workHistory = document.createElement("details");
  workHistory.className = "task-work-history";
  const historyLabel = document.createElement("summary");
  workHistory.append(historyLabel);
  const historyNote = document.createElement("p");
  historyNote.textContent = "已完成或连续 7 天无进展的工作收在这里；仅调整展示，未结工作的状态不变。";
  workHistory.append(historyNote);
  let historyCount = 0;
  let currentCount = 0;
  const renderedWorkRequirements = new Set();
  visibleAssignments.sort((left, right) => Number(right.run_status === "waiting_human")
    - Number(left.run_status === "waiting_human")
    || String(assignmentStatusChangedAt(project, right)).localeCompare(String(assignmentStatusChangedAt(project, left))))
    .forEach((assignment) => {
    const requirementKey = JSON.stringify([assignment.responsible_human_user_id,
      assignment.assignee_agent_id, assignment.instruction]);
    const repeatedRequirement = renderedWorkRequirements.has(requirementKey);
    renderedWorkRequirements.add(requirementKey);
    const row = document.createElement("article");
    const humanTone = humanColorTone(assignment.responsible_human_user_id);
    row.className = `project-collaboration-row human-tone-${humanTone}`;
    row.id = `task-work-${assignment.assignment_id}`;
    const avatar = document.createElement("span");
    avatar.className = "project-progress-avatar";
    avatar.textContent = assignment.responsible_human_display_name.slice(0, 1);
    const copy = document.createElement("div");
    copy.className = "project-progress-copy";
    const heading = document.createElement("div");
    heading.className = "project-progress-heading";
    const name = document.createElement("strong");
    const initiator = assignment.source_actor_type === "platform"
      ? "AgentPost"
      : (assignment.source_actor_human_display_name
        || assignment.created_by_human_display_name
        || "AgentPost");
    const targetHuman = assignment.responsible_human_display_name;
    name.textContent = initiator === targetHuman ? targetHuman : `${initiator} → ${targetHuman}`;
    const time = document.createElement("time");
    time.textContent = `状态变化 ${dateText(assignmentStatusChangedAt(project, assignment))}`;
    const status = document.createElement("span");
    status.textContent = taskAssignmentStatusLabel(assignment);
    heading.append(name, time, status);
    const agent = document.createElement("small");
    agent.textContent = (assignment.cancellation_reason === "human_completed" ? "原执行 AI：" : "执行 AI：") + assignment.assignee_agent_display_name;
    const route = document.createElement("small");
    const priorityLabels = { low: "低", normal: "普通", high: "高", urgent: "紧急" };
    const wakeLabels = {
      queued: "已排队，尚未被任务监听领取",
      claimed: "Connector 已领取",
      mapped: "已映射本地会话",
      woken: "本地 AI 已唤醒",
      running: "本地 AI 已唤醒并执行",
      finished: "执行已结束",
    };
    const sourceLabels = {
      agent_joined_collaboration: "加入任务",
      assignment_created: "Human 明确工作",
      changes_requested: "Human 要求修改",
      task_created: "任务创建",
    };
    route.textContent = `工作来源：${sourceLabels[assignment.source_kind] || "任务创建"} · `
      + `优先级 ${priorityLabels[assignment.priority] || assignment.priority} · `
      + `${assignment.cancellation_reason === "human_completed" ? "Human 已补交，原执行已停止" : wakeLabels[assignment.wake_stage] || assignment.wake_stage}`;
    const heartbeat = document.createElement("small");
    heartbeat.className = "project-progress-heartbeat";
    heartbeat.textContent = assignment.run_last_heartbeat_at
      ? `最近心跳：${dateText(assignment.run_last_heartbeat_at)}`
      : "本次执行尝试：尚未上报心跳";
    const summary = document.createElement("p");
    const progress = taskProgressSummary(assignment);
    if (assignment.cancellation_reason === "human_completed") {
      summary.textContent = `Human 补交结果：${assignment.result_summary || "请查看原始记录"}`;
    } else if (assignment.run_status === "waiting_human") {
      summary.textContent = `AI 需要 Human 确认：${checkpointHumanPrompt(assignment.run_checkpoint)}`;
    } else if (assignment.run_status === "queued" && assignment.run_checkpoint?.human_response) {
      summary.textContent = `Human 已回复：${String(assignment.run_checkpoint.human_response)}\n等待 AI 重新领取。`;
    } else {
      summary.textContent = assignment.result_summary
        ? `AI 反馈：${progress.text}`
        : `工作要求：${progress.text}\n${assignment.run_status === "queued" ? "等待 AI 领取。" : "AI 尚未提交结果。"}`;
    }
    const workTitle = document.createElement("h4");
    workTitle.textContent = assignment.assignment_kind === "participant_start"
      ? "参与准备需要你回答"
      : plainTaskExcerpt(assignment.instruction, 100) || "明确工作";
    const technical = document.createElement("details");
    technical.className = "task-work-technical";
    const technicalLabel = document.createElement("summary");
    technicalLabel.textContent = "执行详情与来源";
    const identity = document.createElement("small");
    identity.textContent = `所属任务：${project.title} · 工作 ID：${assignment.assignment_id}`;
    technical.append(technicalLabel, identity, route, heartbeat);
    copy.append(heading, workTitle, agent, summary, technical);
    if (project.status==="active" && !["completed","cancelled"].includes(assignment.status)
        && [project.owner_human_user_id,assignment.responsible_human_user_id].map(String).includes(String(currentUserId))) {
      const recovery=document.createElement("details");const title=document.createElement("summary");title.textContent="由我补交结果／更换执行 AI";
      const form=document.createElement("form");const label=document.createElement("label");label.textContent="补交结果或接续说明";
      const body=document.createElement("textarea");body.required=true;body.maxLength=10000;label.append(body);
      const selectLabel=document.createElement("label");selectLabel.textContent="处理方式";
      const select=document.createElement("select");select.append(new Option("由我补交工作结果","complete"));
      const member=project.members.find(m=>String(m.human_user_id)===String(assignment.responsible_human_user_id));
      (member?.agents || []).forEach(a=>{if(a.agent_id!==assignment.assignee_agent_id)select.append(new Option(`改由 ${a.display_name} 接续`,a.agent_id));});selectLabel.append(select);
      const note=document.createElement("p");note.textContent="提交后旧执行租约失效；已经发生的外部操作无法撤销。补交结果不等于整项任务验收。";
      const submit=document.createElement("button");submit.textContent="确认并接续";
      const feedback=document.createElement("p");feedback.setAttribute("role","status");
      let operationId=crypto.randomUUID(),previousDraft="";
      form.onsubmit=async(event)=>{event.preventDefault();submit.disabled=true;try{
        const draft=JSON.stringify([select.value,body.value]);if(previousDraft && previousDraft!==draft)operationId=crypto.randomUUID();previousDraft=draft;
        const updated=await requestJson(`/api/v1/tasks/${project.task_id}/assignments/${assignment.assignment_id}/continue`,{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":state.csrfToken},body:JSON.stringify({action:select.value==="complete"?"complete":"reassign",agent_id:select.value==="complete"?null:select.value,body:body.value,operation_id:operationId})});
        state.selectedProject=updated;renderProjectDetail();
      }catch(error){feedback.textContent=error.message;}finally{submit.disabled=false;}};
      form.append(label,selectLabel,note,submit,feedback);recovery.append(title,form);copy.append(recovery);
    }
    if (project.membership_role === "owner" && assignment.status === "queued") {
      const cancelWork = document.createElement("button");
      cancelWork.type = "button";
      cancelWork.className = "quiet-button";
      cancelWork.textContent = "取消排队工作";
      const cancelStatus = document.createElement("small");
      cancelStatus.setAttribute("role", "status");
      cancelWork.addEventListener("click", async () => {
        if (cancelWork.disabled) return;
        cancelWork.disabled = true;
        cancelStatus.textContent = "正在取消…";
        try {
          await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/assignments/${encodeURIComponent(assignment.assignment_id)}/cancel`, {
            method: "POST", headers: { "X-CSRF-Token": state.csrfToken },
          });
          cancelStatus.textContent = "已取消，历史记录保留";
          if (state.selectedProjectId === project.task_id) await loadProjectDetail(project.task_id);
        } catch (error) {
          cancelStatus.textContent = `${error.message}。请刷新核对，已开始执行的工作不能在此取消。`;
          cancelWork.disabled = false;
        }
      });
      technical.append(cancelWork, cancelStatus);
    }

    if (repeatedRequirement) {
      const note = document.createElement("p");
      note.className = "task-field-help";
      note.textContent = "同一执行对象还有相同要求的工作。此项保留独立状态，请按工作 ID 核对来源。";
      copy.append(note);
    }
    appendTaskRecordLink(
      copy,
      taskRecordTarget(project, assignment),
      progress.truncated ? "查看完整任务记录" : "查看依据",
      "work",
    );
    const currentUserCanRespond = assignment.run_status === "waiting_human"
      && [project.owner_human_user_id, assignment.responsible_human_user_id]
        .map(String).includes(String(currentUserId));
    if (currentUserCanRespond) {
      const responseForm = document.createElement("form");
      responseForm.className = "task-human-response-form";
      responseForm.dataset.assignmentId = assignment.assignment_id;
      responseForm.dataset.taskId = project.task_id;
      const responseLabel = document.createElement("label");
      responseLabel.textContent = "回复 AI 并继续执行";
      const response = document.createElement("textarea");
      response.name = "response";
      response.rows = 3;
      response.maxLength = 10000;
      response.required = true;
      response.placeholder = "回答 AI 的问题，或说明下一步应如何处理";
      const submit = document.createElement("button");
      submit.type = "submit";
      submit.className = "primary-action";
    submit.textContent = "保存回答，等待 AI 继续";
      responseLabel.append(response);
      responseForm.append(responseLabel, submit);
      responseForm.addEventListener("submit", respondToWaitingAgent);
      copy.append(responseForm);
    }
    row.append(avatar, copy);
    if ((historicalTaskWork(project, assignment) || repeatedRequirement) && assignment.run_status !== "waiting_human") {
      const history = document.createElement("details");
      history.className = "task-earlier-work";
      const label = document.createElement("summary");
      label.textContent = `${targetHuman} · ${taskAssignmentStatusLabel(assignment)} · ${plainTaskExcerpt(assignment.instruction, 80)} · ${dateText(assignment.created_at)}`;
      history.append(label, row);
      workHistory.append(history);
      historyCount += 1;
    } else {
      elements.projectCollaborationList.append(row);
      currentCount += 1;
    }
  });
  if (!currentCount) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = "暂无近期进行中的明确工作。最新交流请看上方“最新协作”。";
    elements.projectCollaborationList.append(empty);
  }
  if (historyCount) {
    historyLabel.textContent = `历史及未结工作 · ${historyCount} 项`;
    elements.projectCollaborationList.append(workHistory);
  }
  const execution = document.createElement("details");
  execution.className = "task-execution-state";
  const executionSummary = document.createElement("summary");
  const activeExecutionCount = operationalAssignments.filter(
    (assignment) => !["completed", "cancelled"].includes(assignment.status),
  ).length;
  executionSummary.textContent = `AI 执行状态 · ${activeExecutionCount} 个未结束`;
  const executionNote = document.createElement("p");
  executionNote.textContent = "这里显示领取、唤醒和心跳等技术状态，不等同于业务进展或 Human 验收。";
  execution.append(executionSummary, executionNote);
  operationalAssignments.forEach((assignment) => {
    const item = document.createElement("div");
    item.className = "task-execution-state-row";
    const owner = document.createElement("strong");
    owner.textContent = assignment.responsible_human_display_name;
    const agent = document.createElement("span");
    agent.textContent = assignment.assignee_agent_display_name;
    const status = document.createElement("span");
    status.textContent = `${assignment.assignment_kind === "participant_start" ? "参与协同" : "明确工作"} · ${taskAssignmentStatusLabel(assignment)}`;
    const heartbeat = document.createElement("time");
    heartbeat.textContent = assignment.run_last_heartbeat_at
      ? `心跳 ${dateText(assignment.run_last_heartbeat_at)}`
      : "尚无心跳";
    item.append(owner, agent, status, heartbeat);
    execution.append(item);
  });
  if (!operationalAssignments.length) {
    const empty = document.createElement("p");
    empty.textContent = "当前没有 AI 执行单元。";
    execution.append(empty);
  }
  elements.projectCollaborationList.append(execution);
  renderTaskAttention(project, ownerAccess);

  elements.projectActivityList.replaceChildren();
  const recordToolbar = document.createElement("div");
  recordToolbar.className = "task-record-toolbar";
  const recordFilters = [
    ["discussion", "讨论"],
    ["work", "工作与结果"],
    ["system", "系统记录"],
    ["all", "全部"],
  ];
  if (ownerAccess) recordFilters.push(["relations", "整理历史回复关系"]);
  recordFilters.forEach(([value, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = value === state.taskRecordFilter ? "active" : "";
    button.setAttribute("aria-pressed", String(value === state.taskRecordFilter));
    button.textContent = label;
    button.addEventListener("click", () => {
      state.taskRecordFilter = value;
      renderProjectDetail();
    });
    recordToolbar.append(button);
  });
  if (project.activities_truncated) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "quiet-button task-record-more";
    const reachedLimit = state.taskActivityLimit >= 2000;
    more.textContent = reachedLimit
      ? `已显示最近 2000 条（共 ${project.activity_total} 条）`
      : `加载更早记录（共 ${project.activity_total} 条）`;
    more.disabled = reachedLimit;
    if (!reachedLimit) {
      more.addEventListener("click", async () => {
        state.taskActivityLimit = Math.min(Math.max(state.taskActivityLimit + 200, 400), 2000);
        more.disabled = true;
        await loadProjectDetail(project.task_id);
      });
    }
    recordToolbar.append(more);
  }
  elements.projectActivityList.append(recordToolbar);
  const assignmentsById = new Map(
    (project.assignments || []).map((assignment) => [String(assignment.assignment_id), assignment]),
  );
  const legacyActivities = [];
  const currentActivities = [];
  (project.activities || []).forEach((activity) => {
    const assignment = assignmentsById.get(String(activity.metadata?.assignment_id || ""));
    const historicalAutomatic = assignment
      && (["result_sync", "task_message"].includes(assignment.assignment_kind)
        || assignment.cancellation_reason === "legacy_pre_0_1_44_backlog");
    (historicalAutomatic ? legacyActivities : currentActivities).push(activity);
  });
  const discussionKinds = new Set(["task_message"]);
  const workKinds = new Set([
    "assignment_created", "assignment_cancelled", "run_leased", "run_progress", "run_waiting_human",
    "human_run_response", "human_work_continued", "assignment_result", "final_submitted", "accepted",
    "changes_requested",
  ]);
  const recordActivities = state.taskRecordFilter === "relations"
    ? currentActivities.filter((activity) => ownerAccess && suggestedTaskReplyParent(project, activity))
    : state.taskRecordFilter === "discussion"
    ? currentActivities.filter((activity) => discussionKinds.has(activity.kind))
    : (state.taskRecordFilter === "work"
      ? currentActivities.filter((activity) => workKinds.has(activity.kind))
      : (state.taskRecordFilter === "system"
        ? currentActivities.filter((activity) => (
          !discussionKinds.has(activity.kind) && !workKinds.has(activity.kind)
        ))
        : currentActivities));
  const latestActivity = [...currentActivities].filter((activity) => discussionKinds.has(activity.kind))
    .sort((a,b) => String(b.created_at).localeCompare(String(a.created_at))
      || String(b.activity_id).localeCompare(String(a.activity_id)))[0];
  document.querySelector("#task-context-open").onclick = () => openTaskContext(project);
  const latestButton = document.querySelector("#task-jump-latest");
  latestButton.hidden = !latestActivity;
  latestButton.textContent = project.unread_count > 0
    ? `最新讨论 · ${project.unread_count} 条新内容`
    : "最新讨论";
  latestButton.onclick = latestActivity
    ? () => openTaskRecord(latestActivity.activity_id, "discussion")
    : null;
  const renderActivitiesInto = (activities, container) => activities.forEach((activity) => {
    const row = document.createElement("article");
    row.className = `project-activity-row human-tone-${humanColorTone(activity.actor_human_user_id)}`;
    row.id = `task-activity-${activity.activity_id}`;
    const avatar = document.createElement("span");
    avatar.className = `project-activity-avatar actor-${activity.actor_type}`;
    avatar.textContent = (activity.actor_display_name || "系").slice(0, 1);
    const copy = document.createElement("div");
    copy.className = "project-activity-copy";
    const parentId = activity.metadata?.reply_to_activity_id;
    const referenceIds = [...new Set([parentId, ...(activity.metadata?.referenced_activity_ids || [])].filter(Boolean))];
    referenceIds.forEach((id) => {
      const original = project.activities.find((item) => item.activity_id === id);
      const link = document.createElement("a");
      link.href = `#task-activity-${id}`;
      link.textContent = original
        ? `${id === parentId ? "回复" : "引用"} ${original.actor_display_name} · ${dateText(original.created_at)}`
        : "原记录暂不可用";
      link.addEventListener("click", (event) => { event.preventDefault(); revealTaskRecord(id); });
      copy.append(link);
    });
    if (parentId && activity.metadata?.reply_relation_source) {
      const relation = document.createElement("small");
      relation.className = "task-reply-relation-source";
      relation.textContent = activity.metadata.reply_relation_source === "human_confirmed"
        ? "回复关系由 Human 确认"
        : "回复关系由任务桥接记录还原";
      copy.append(relation);
    }
    const heading = document.createElement("div");
    heading.className = "project-activity-heading";
    const actor = document.createElement("strong");
    const actorHuman = activity.actor_display_name || "AgentPost";
    const actorAgent = activity.actor_agent_display_name;
    if (["task_created", "created"].includes(activity.kind) && actorAgent) {
      const origin = activity.metadata?.publication_origin;
      actor.textContent = origin === "human_delegated"
        ? `${actorHuman} 委托 ${actorAgent} 发布`
        : (origin === "agent_autonomous"
          ? `${actorHuman} 的 ${actorAgent} 主动发布`
          : `${actorHuman} 通过 ${actorAgent} 发布`);
    } else {
      actor.textContent = actorHuman;
    }
    const time = document.createElement("time");
    time.textContent = dateText(activity.created_at);
    heading.append(actor, time);
    const textNode = document.createElement("p");
    textNode.className = "project-activity-action";
    textNode.textContent = activityText(activity);
    copy.append(heading);
    if (activity.kind === "task_message" && actorAgent) {
      const agent = document.createElement("small");
      agent.className = "project-activity-agent";
      const origin = activity.metadata?.publication_origin;
      agent.textContent = origin === "human_delegated"
        ? `由 ${actorAgent} 代为发布`
        : (origin === "agent_autonomous"
          ? `其 ${actorAgent} 主动发布`
          : `通过 ${actorAgent} 发布`);
      copy.append(agent);
    } else if (activity.actor_agent_display_name
      && !["task_created", "created"].includes(activity.kind)) {
      const agent = document.createElement("small");
      agent.className = "project-activity-agent";
      agent.textContent = "通过 AI：" + activity.actor_agent_display_name;
      copy.append(agent);
    }
    if (activity.kind === "task_message") {
      const context = document.createElement("div");
      context.className = "task-message-context";
      appendTaskMessageContext(context, project, activity);
      copy.append(context);
    } else copy.append(textNode);
    const suggestedParent = ownerAccess && state.taskRecordFilter === "relations"
      ? suggestedTaskReplyParent(project, activity) : null;
    if (suggestedParent) {
      const suggestion = document.createElement("div");
      suggestion.className = "task-reply-suggestion";
      const message = document.createElement("span");
      message.textContent = `可能回应 ${suggestedParent.actor_display_name} · ${dateText(suggestedParent.created_at)}`;
      const comparison = document.createElement("blockquote");
      comparison.textContent = `候选原文：${plainTaskExcerpt(suggestedParent.metadata?.body || activityText(suggestedParent), 360)}`;
      const confirm = document.createElement("button");
      confirm.type = "button";
      confirm.className = "quiet-button";
      confirm.textContent = "确认关联";
      confirm.addEventListener("click", async () => {
        confirm.disabled = true;
        try {
          await decideTaskReplyRelation(
            activity.activity_id,
            suggestedParent.activity_id,
            "confirm",
          );
        } catch (error) {
          confirm.disabled = false;
          message.textContent = error.message;
        }
      });
      const dismiss = document.createElement("button");
      dismiss.type = "button";
      dismiss.className = "quiet-button";
      dismiss.textContent = "不是回复";
      dismiss.addEventListener("click", async () => {
        dismiss.disabled = true;
        try {
          await decideTaskReplyRelation(
            activity.activity_id,
            suggestedParent.activity_id,
            "dismiss",
          );
        } catch (error) {
          dismiss.disabled = false;
          message.textContent = error.message;
        }
      });
      const actions = document.createElement("span");
      actions.className = "task-reply-suggestion-actions";
      actions.append(confirm, dismiss);
      suggestion.append(message, comparison, actions);
      copy.append(suggestion);
    }
    if (activity.kind === "assignment_created" && activity.metadata?.instruction) {
      const instruction = document.createElement("p");
      instruction.className = "task-activity-text-body";
      instruction.textContent = `工作要求：${String(activity.metadata.instruction)}`;
      copy.append(instruction);
    }
    if (["assignment_result", "human_work_continued"].includes(activity.kind) && activity.metadata?.summary) {
      const result = document.createElement("p");
      result.className = "task-activity-text-body";
      result.textContent = `${activity.kind === "human_work_continued" ? "Human 接续说明" : "AI 反馈"}：${String(activity.metadata.summary)}`;
      copy.append(result);
    }
    if (activity.kind === "run_waiting_human" && activity.metadata?.checkpoint) {
      const checkpoint = document.createElement("p");
      checkpoint.className = "task-activity-text-body task-activity-human-request";
      checkpoint.textContent = `需要 Human 确认：${checkpointHumanPrompt(activity.metadata.checkpoint)}`;
      copy.append(checkpoint);
    }
    if (activity.kind === "human_run_response" && activity.metadata?.response) {
      const response = document.createElement("p");
      response.className = "task-activity-text-body";
      response.textContent = `Human 回复：${String(activity.metadata.response)}`;
      copy.append(response);
    }
    if (activity.kind === "task_message"
      && Array.isArray(activity.metadata?.recipient_statuses)
      && activity.metadata.recipient_statuses.length) {
      const recipients = document.createElement("details");
      recipients.className = "project-activity-recipients";
      const summary = document.createElement("summary");
      summary.textContent = `查看接收状态 · ${taskMessageRecipientSummary(activity.metadata.recipient_statuses)}`;
      recipients.append(summary);
      activity.metadata.recipient_statuses.forEach((item) => {
        const recipient = document.createElement("div");
        recipient.textContent = taskMessageRecipientLabel(project, item);
        recipients.append(recipient);
      });
      copy.append(recipients);
    }
    if (activity.kind === "task_message" && activity.metadata?.body !== undefined) {
      const format = String(activity.metadata.content_format || "text").toLowerCase();
      if (["markdown", "json", "html"].includes(format)) {
        copy.append(createTaskActivityAttachment(activity, format, activity.metadata.body));
      } else if (String(activity.metadata.body).length > 600 || /^\s*#{1,6}\s/m.test(String(activity.metadata.body))) {
        copy.append(createTaskActivityAttachment(activity, "text", activity.metadata.body));
      } else {
        const message = document.createElement("section");
        message.className = "task-message-body";
        const label = document.createElement("strong");
        label.textContent = "说了什么";
        const body = document.createElement("p");
        body.className = "task-activity-text-body";
        body.textContent = typeof activity.metadata.body === "string"
          ? activity.metadata.body
          : JSON.stringify(activity.metadata.body);
        message.append(label, body);
        copy.append(message);
      }
    }
    if (Array.isArray(activity.metadata?.attachments)) {
      appendThreadAttachments({ attachments: activity.metadata.attachments }, copy);
    }
    row.append(avatar, copy);
    if (["task_message", "created", "task_created", "assignment_created", "assignment_result"].includes(activity.kind)) {
      const reply = document.createElement("details");
      reply.className = "task-record-reply";
      const replyLabel = document.createElement("summary");
      replyLabel.textContent = "回复";
      const form = document.createElement("form");
      form.className = "task-reply-form";
      const context = document.createElement("p");
      context.textContent = `以 ${state.dashboard?.user?.display_name || "当前 Human"} 的身份回复 ${actorHuman}。回复进入共享讨论，需要执行时请另行安排明确工作。`;
      const quote = document.createElement("blockquote");
      quote.textContent = taskContentTitle(activity);
      const input = document.createElement("textarea");
      input.rows = 3;
      input.required = true;
      input.maxLength = 20000;
      input.placeholder = "写下你的回复…";
      input.setAttribute("aria-label", `回复 ${actorHuman}`);
      const draftId = `${project.task_id}:${activity.activity_id}`;
      const draft = state.taskReplyDrafts.get(draftId) || { body: "", key: crypto.randomUUID(), pending: false, submittedBody: null };
      state.taskReplyDrafts.set(draftId, draft);
      input.value = draft.body;
      input.disabled = draft.pending || draft.submittedBody !== null;
      input.addEventListener("input", () => { draft.body = input.value; });
      const send = document.createElement("button");
      send.type = "submit";
      send.className = "primary-action";
      send.textContent = draft.submittedBody === null ? "发送回复" : "重试同一回复";
      send.disabled = draft.pending;
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.className = "quiet-button";
      cancel.textContent = "收起，保留草稿";
      cancel.addEventListener("click", () => { reply.open = false; replyLabel.focus(); });
      const feedback = document.createElement("small");
      feedback.setAttribute("role", "status");
      const actions = document.createElement("div");
      actions.className = "task-reply-actions";
      actions.append(cancel, send);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (draft.pending || !input.value.trim() || state.selectedProjectId !== project.task_id) return;
        draft.pending = true;
        draft.submittedBody = draft.submittedBody ?? input.value;
        input.disabled = true;
        send.disabled = true;
        feedback.textContent = "正在发送…";
        let sent = false;
        try {
          await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/messages`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken, "Idempotency-Key": draft.key },
            body: JSON.stringify({ body: draft.submittedBody, reply_to_activity_id: activity.activity_id }),
          });
          sent = true;
          state.taskReplyDrafts.delete(draftId);
          feedback.textContent = "回复已保存";
          if (state.selectedProjectId === project.task_id) {
            await loadProjectDetail(project.task_id);
            if (state.selectedProjectId === project.task_id) revealTaskRecord(activity.activity_id);
          }
        } catch (error) {
          // Unknown acceptance: keep the original body and key together for a safe retry.
          feedback.textContent = sent ? "回复已保存，请刷新查看。" : `${error.message}。可重试同一回复，内容已保留。`;
          send.textContent = "重试同一回复";
          send.disabled = sent;
        } finally {
          draft.pending = false;
        }
      });
      form.append(context, quote, input, actions, feedback);
      reply.append(replyLabel, form);
      copy.append(reply);
    }
    container.append(row);
  });
  const lifecycleKinds = new Set([
    "run_leased", "run_progress", "run_waiting_human", "assignment_result", "human_run_response", "human_work_continued",
  ]);
  const lifecycleGroups = new Map();
  recordActivities.forEach((activity) => {
    const assignmentId = String(activity.metadata?.assignment_id || "");
    if (assignmentId && lifecycleKinds.has(activity.kind)) {
      const group = lifecycleGroups.get(assignmentId) || [];
      group.push(activity);
      lifecycleGroups.set(assignmentId, group);
    }
  });
  const renderedLifecycleAssignments = new Set();
  const discussions = taskDiscussionGroups(recordActivities);
  const discussionByActivity = new Map();
  if (state.taskRecordFilter === "discussion" || state.taskRecordFilter === "all") {
    discussions.filter((group) => group.length > 1).forEach((group) => {
      group.forEach((item) => discussionByActivity.set(item.activity_id, group));
    });
  }
  const renderedDiscussions = new Set();
  recordActivities.forEach((activity) => {
    const discussion = discussionByActivity.get(activity.activity_id);
    if (discussion) {
      if (renderedDiscussions.has(discussion)) return;
      renderedDiscussions.add(discussion);
      const details = document.createElement("details");
      details.className = "task-discussion";
      const summary = document.createElement("summary");
      const root = discussion[0];
      const latest = discussion.at(-1);
      const title = root.metadata?.subject || String(root.metadata?.body || activityText(root)).slice(0, 80);
      const heading = document.createElement("span");
      heading.className = "task-discussion-heading";
      const topic = document.createElement("strong");
      topic.textContent = plainTaskExcerpt(title, 92);
      const time = document.createElement("time");
      time.textContent = dateText(latest.created_at);
      heading.append(topic, time);
      const facts = document.createElement("span");
      facts.className = "task-discussion-facts";
      appendTaskMessageFact(facts, "发起", root.actor_display_name || "Human 待确认");
      appendTaskMessageFact(facts, "共享范围", taskMessageAudienceLabel(project, root));
      appendTaskMessageFact(facts, "回复", `${discussion.length - 1} 条`);
      const preview = document.createElement("p");
      preview.textContent = `最新回复 · ${latest.actor_display_name || "Human 待确认"}：${plainTaskExcerpt(latest.metadata?.body || activityText(latest), 120)}`;
      const list = document.createElement("div");
      renderActivitiesInto(discussion, list);
      summary.append(heading, facts, preview);
      details.append(summary, list);
      elements.projectActivityList.append(details);
      return;
    }
    const assignmentId = String(activity.metadata?.assignment_id || "");
    const group = lifecycleKinds.has(activity.kind)
      ? lifecycleGroups.get(assignmentId)?.filter((item) => !discussionByActivity.has(item.activity_id))
      : null;
    if (!group || group.length < 2) {
      renderActivitiesInto([activity], elements.projectActivityList);
      return;
    }
    if (renderedLifecycleAssignments.has(assignmentId)) return;
    renderedLifecycleAssignments.add(assignmentId);
    const assignment = assignmentsById.get(assignmentId);
    const details = document.createElement("details");
    details.className = "task-run-activity";
    details.open = assignment?.run_status === "waiting_human";
    const summary = document.createElement("summary");
    const human = assignment?.responsible_human_display_name || activity.actor_display_name || "Human";
    summary.textContent = `${human} · AI 执行过程（${group.length} 条）· ${activityText(group[0])}`;
    const list = document.createElement("div");
    list.className = "project-activity-list";
    renderActivitiesInto(group, list);
    details.append(summary, list);
    elements.projectActivityList.append(details);
  });
  if (legacyActivities.length && ["system", "all"].includes(state.taskRecordFilter)) {
    const legacy = document.createElement("details");
    legacy.className = "task-legacy-activity";
    const summary = document.createElement("summary");
    summary.textContent = `0.1.47 前的历史自动协同（${legacyActivities.length} 条，已停止）`;
    const list = document.createElement("div");
    list.className = "project-activity-list";
    renderActivitiesInto(legacyActivities, list);
    legacy.append(summary, list);
    elements.projectActivityList.append(legacy);
  }
  if (!recordActivities.length
      && !(legacyActivities.length && ["system", "all"].includes(state.taskRecordFilter))) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = "这个分类下暂时没有记录。";
    elements.projectActivityList.append(empty);
  }
}

function renderFriendBrowser() {
  renderFriendPendingNotice();
  const friends = filteredFriends();
  if (!friends.some((friend) => friend.human_user_id === state.selectedFriendId)) {
    state.selectedFriendId = isMobileWorkspace() ? "" : (friends[0]?.human_user_id || "");
  }
  elements.friendBrowserCount.textContent = friends.length + " 人";
  elements.friendBrowserList.replaceChildren();
  if (!friends.length) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = state.friendQuery ? "没有匹配的好友，请调整搜索条件。"
      : state.friendFilter === "pending_incoming" ? "暂无待你确认的好友申请。"
        : state.friendFilter === "pending_outgoing" ? "暂无已发出的好友申请。"
          : "当前列表暂无好友。";
    elements.friendBrowserList.append(empty);
  }
  friends.forEach((friend) => {
    elements.friendBrowserList.append(createCollaborationListButton({
      title: friend.display_name,
      meta: "@" + friend.username + " · " + (friend.relation_status === "accepted"
        ? friend.agents.length + " 个可见 Agent" : "成为好友后可查看 Agent"),
      badge: friendRelationLabel(friend),
      active: state.selectedFriendId === friend.human_user_id,
      avatar: friend.display_name.slice(0, 1),
      onClick: () => {
        state.selectedFriendId = friend.human_user_id;
        renderFriendBrowser();
        updateCollaborationWorkspaceMode();
        elements.friendDetailName.focus({ preventScroll: true });
        resetMobileLayerScroll();
      },
    }));
  });
  renderFriendDetail();
}

function renderFriendPendingNotice() {
  const count = state.friends.filter((friend) => friend.relation_status === "pending_incoming").length;
  elements.friendPendingBadge.hidden = count === 0;
  elements.friendPendingBadge.textContent = count ? String(count) : "";
  elements.friendPendingBadge.setAttribute("aria-label", count + " 条好友申请待你确认");
  elements.friendPendingNotice.hidden = count === 0;
  elements.friendPendingNotice.textContent = count + " 人申请成为好友 · 点击处理";
  elements.friendFilters.forEach((button) => {
    const active = state.friendFilter === button.dataset.friendFilter;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
    if (button.dataset.friendFilter === "pending_incoming") {
      button.textContent = count ? "待你确认（" + count + "）" : "待你确认";
    }
  });
}

function renderFriendDetail() {
  const friend = friendById(state.selectedFriendId);
  elements.friendEmpty.hidden = Boolean(friend);
  elements.friendDetail.hidden = !friend;
  if (!friend) {
    return;
  }
  elements.friendDetailAvatar.textContent = friend.display_name.slice(0, 1);
  const relationLabels = {
    accepted: "正式好友",
    pending_incoming: "等待你确认",
    pending_outgoing: "等待对方确认",
    suggested: "沟通过，可申请好友",
  };
  elements.friendDetailRelation.textContent = relationLabels[friend.relation_status] || "协作联系";
  elements.friendDetailName.textContent = friend.display_name;
  elements.friendDetailRole.textContent = "@" + friend.username;
  elements.friendDetailOnline.textContent = relationLabels[friend.relation_status] || "协作联系";
  elements.friendDetailOnline.classList.remove("online", "offline");
  elements.friendDetailNote.textContent = friend.relation_status === "accepted"
    ? "双方已经明确确认好友关系，可以互相邀请加入任务。"
    : "历史沟通不自动成为好友，必须由双方明确确认。";
  const actionLabels = {
    accepted: "发起任务",
    pending_incoming: "接受好友申请",
    pending_outgoing: "等待对方确认",
    suggested: "申请加好友",
  };
  elements.friendStartProject.textContent = actionLabels[friend.relation_status] || "申请加好友";
  elements.friendStartProject.disabled = friend.relation_status === "pending_outgoing";
  elements.friendCapabilities.replaceChildren();
  const capabilities = [...new Set(friend.agents.flatMap((agent) => agent.capabilities || []))];
  capabilities.forEach((capability) => {
    const chip = document.createElement("span");
    chip.textContent = capability;
    elements.friendCapabilities.append(chip);
  });
  if (!capabilities.length) {
    const empty = document.createElement("span");
    empty.textContent = "暂未声明能力";
    elements.friendCapabilities.append(empty);
  }
  elements.friendAgentCount.textContent = friend.relation_status === "accepted"
    ? friend.agents.length + " 个" : "确认好友后可查看";
  elements.friendAgentList.replaceChildren();
  friend.agents.forEach((agent) => {
    const row = document.createElement("article");
    row.className = "friend-agent-row";
    const avatar = document.createElement("span");
    avatar.textContent = "A";
    const copy = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = agent.display_name;
    const status = document.createElement("small");
    status.textContent = agent.address + (agent.work_availability ? " · " + statusLabel(agent.work_availability) : "");
    copy.append(name, status);
    row.append(avatar, copy);
    elements.friendAgentList.append(row);
  });
  const relatedProjects = state.projects.filter((project) =>
    project.members?.some((member) => member.human_user_id === friend.human_user_id));
  elements.friendProjectCount.textContent = relatedProjects.length + " 个";
  elements.friendProjectList.replaceChildren();
  if (!relatedProjects.length) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = "还没有共同任务，可以从右上方发起。";
    elements.friendProjectList.append(empty);
  }
  relatedProjects.forEach((project) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "friend-project-row";
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = project.title;
    const meta = document.createElement("small");
    meta.textContent = projectKind(project) + " · " + projectStatusLabel(project);
    copy.append(title, meta);
    const arrow = document.createElement("span");
    arrow.textContent = "查看任务 ›";
    row.append(copy, arrow);
    row.addEventListener("click", async () => {
      state.selectedProjectId = project.task_id;
      setProjectFilter(["awaiting_acceptance", "completed"].includes(project.status)
        ? project.status
        : (project.status === "archived" || project.status === "cancelled" ? "all" : "active"));
      activateRoute("projects", "board", { focusContent: true });
      renderProjectBrowser();
      await loadProjectDetail(project.task_id);
    });
    elements.friendProjectList.append(row);
  });
}

function openProjectCreateDialog() {
  elements.projectCreateForm.reset();
  elements.projectCreateResult.textContent = "";
  elements.projectCreateAgentOptions.replaceChildren();
  ownedTaskAgents().forEach((agent, index) => {
    const label = document.createElement("label");
    label.className = "project-invite-option";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "task-create-agent";
    input.value = agent.id;
    input.checked = index === 0;
    label.append(input, document.createTextNode(agentDisplayName(agent)));
    elements.projectCreateAgentOptions.append(label);
  });
  if (!ownedTaskAgents().length) {
    elements.projectCreateAgentOptions.append(emptyState("请先在“AI”中连接至少一个自己的 AI。"));
  }
  elements.projectCreateDialog.showModal();
  elements.projectCreateName.focus();
}

function closeProjectCreateDialog() {
  elements.projectCreateDialog.close();
}

async function actOnSelectedFriend() {
  const friend = friendById(state.selectedFriendId);
  if (!friend) {
    return;
  }
  if (friend.relation_status === "accepted") {
    openProjectCreateDialog();
    return;
  }
  if (friend.relation_status === "pending_outgoing") {
    return;
  }
  try {
    if (friend.relation_status === "pending_incoming") {
      await requestJson(`/api/v1/friend-requests/${encodeURIComponent(friend.friendship_id)}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
        body: JSON.stringify({ decision: "accept" }),
      });
    } else {
      await requestJson("/api/v1/friend-requests", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
        body: JSON.stringify({ username: friend.username }),
      });
    }
    await loadFriends();
    updateCollaborationWorkspaceMode();
    resetMobileLayerScroll();
  } catch (error) {
    elements.friendDetailNote.textContent = error.message;
  }
}

async function createProject(event) {
  event.preventDefault();
  if (!elements.projectCreateForm.reportValidity()) {
    return;
  }
  const selectedAgentId = elements.projectCreateForm.querySelector('input[name="task-create-agent"]:checked')?.value;
  if (!selectedAgentId) {
    elements.projectCreateResult.textContent = "必须选择至少一个自己的 AI。";
    return;
  }
  elements.projectCreateResult.textContent = "正在创建任务…";
  try {
    const project = await requestJson("/api/v1/tasks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": state.csrfToken,
      },
      body: JSON.stringify({
        title: elements.projectCreateName.value.trim(),
        goal: elements.projectCreateGoal.value.trim(),
        expected_output: elements.projectCreateOutput.value.trim(),
        agent_ids: [selectedAgentId],
        primary_agent_id: selectedAgentId,
      }),
    });
    state.selectedProjectId = project.task_id;
    state.selectedProject = project;
    state.projectFilter = "active";
    history.pushState({ task: project.task_id }, "", taskRouteUrl(project.task_id));
    closeProjectCreateDialog();
    activateRoute("projects", "board", { focusContent: true });
    await loadProjects();
    elements.projectActionResult.textContent = "任务已创建，可以安排工作或邀请好友参与。";
  } catch (error) {
    elements.projectCreateResult.textContent = error.message;
  }
}

async function openProjectInviteDialog() {
  const project = state.selectedProject;
  if (!project) {
    return;
  }
  elements.projectInviteResult.textContent = "";
  elements.projectInviteSummary.textContent = "只能邀请已双向确认的好友加入“" + project.title + "”。";
  elements.projectInviteOptions.replaceChildren();
  try {
    const payload = await requestJson(
      "/api/v1/tasks/" + encodeURIComponent(project.task_id) + "/invite-candidates",
    );
    state.projectInvitationCandidates = Array.isArray(payload?.items) ? payload.items : [];
  } catch (error) {
    elements.projectInviteResult.textContent = error.message;
    state.projectInvitationCandidates = [];
  }
  state.projectInvitationCandidates.forEach((friend) => {
    const label = document.createElement("label");
    label.className = "project-invite-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = "project-invite-friend";
    input.value = friend.human_user_id;
    const avatar = document.createElement("span");
    avatar.className = "project-member-avatar";
    avatar.textContent = friend.display_name.slice(0, 1);
    const copy = document.createElement("span");
    const name = document.createElement("strong");
    name.textContent = friend.display_name;
    const meta = document.createElement("small");
    meta.textContent = "@" + friend.username + " · " + friend.agents.length + " 个 Agent";
    copy.append(name, meta);
    label.append(input, avatar, copy);
    elements.projectInviteOptions.append(label);
  });
  if (!state.projectInvitationCandidates.length) {
    const empty = document.createElement("p");
    empty.className = "prototype-inline-empty";
    empty.textContent = "当前没有可以邀请的好友。";
    elements.projectInviteOptions.append(empty);
  }
  elements.projectInviteDialog.showModal();
}

function closeProjectInviteDialog() {
  elements.projectInviteDialog.close();
}

async function inviteProjectFriends(event) {
  event.preventDefault();
  const project = state.selectedProject;
  const selected = Array.from(
    elements.projectInviteForm.querySelectorAll('input[name="project-invite-friend"]:checked'),
  ).map((input) => input.value);
  if (!project || !selected.length) {
    elements.projectInviteResult.textContent = "请至少选择一位好友。";
    return;
  }
  try {
    const updated = await requestJson(
      "/api/v1/tasks/" + encodeURIComponent(project.task_id) + "/members",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": state.csrfToken,
        },
        body: JSON.stringify({ human_user_ids: selected }),
      },
    );
    state.selectedProject = updated;
    closeProjectInviteDialog();
    await loadProjects();
    elements.projectActionResult.textContent = "好友已加入任务，其默认 Agent 已进入协同队列，邮件通知已安排发送。";
  } catch (error) {
    elements.projectInviteResult.textContent = error.message;
  }
}

async function updateSelectedProjectStatus() {
  const project = currentTaskForAction();
  if (!project) {
    return;
  }
  const action = project.status === "paused" ? "resume" : "pause";
  try {
    const updated = await requestJson(
      "/api/v1/tasks/" + encodeURIComponent(project.task_id) + "/status",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": state.csrfToken,
        },
        body: JSON.stringify({ action }),
      },
    );
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    setProjectFilter("active");
    await loadProjects();
    elements.projectActionResult.textContent = action === "pause" ? "任务已经暂停。" : "任务已经继续。";
  } catch (error) {
    if (state.selectedProjectId === project?.task_id) elements.projectActionResult.textContent = error.message;
  }
}

async function decideSelectedProjectInvitation(accept) {
  const project = state.selectedProject;
  if (!project) {
    return;
  }
  try {
    const selectedAgentId = elements.projectAcceptAgentOptions
      .querySelector('input[name="task-accept-agent"]:checked')?.value;
    if (accept && !selectedAgentId) {
      elements.projectActionResult.textContent = "加入任务前必须选择至少一个自己的 AI。";
      return;
    }
    await requestJson(
      "/api/v1/tasks/" + encodeURIComponent(project.task_id)
        + (accept ? "/accept" : "/decline"),
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": state.csrfToken,
        },
        body: accept ? JSON.stringify({
          agent_ids: [selectedAgentId],
          primary_agent_id: selectedAgentId,
        }) : undefined,
      },
    );
    await loadProjects({ preserveSelection: accept });
    if (accept) {
      elements.projectActionResult.textContent = "你已经选择 AI 并加入任务。";
    }
  } catch (error) {
    elements.projectActionResult.textContent = error.message;
  }
}

async function saveMyTaskAgent(event) {
  event.preventDefault();
  const project = currentTaskForAction();
  const agentIds = Array.from(
    elements.taskMyAgentOptions.querySelectorAll('input[name="task-my-agent"]:checked'),
  ).map((input) => input.value);
  const primaryAgentId = elements.taskMyPrimaryAgent.value;
  if (!project) {
    return;
  }
  if (!agentIds.length || !primaryAgentId) {
    elements.projectActionResult.textContent = "请至少选择一个参与 AI，并指定主要 AI。";
    return;
  }
  try {
    const updated = await requestJson(
      `/api/v1/tasks/${encodeURIComponent(project.task_id)}/my-agents`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
        body: JSON.stringify({ agent_ids: agentIds, primary_agent_id: primaryAgentId }),
      },
    );
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    renderProjectDetail();
    elements.projectActionResult.textContent = `已保存 ${agentIds.length} 个参与 AI；新加入的 AI 已进入协同队列。`;
  } catch (error) {
    if (state.selectedProjectId === project?.task_id) elements.projectActionResult.textContent = error.message;
  }
}

function taskAssignmentDraft(taskId) {
  if (!state.taskAssignmentDrafts.has(taskId)) {
    state.taskAssignmentDrafts.set(taskId, {
      agentIds: [], instruction: "", expectedOutput: "", key: crypto.randomUUID(),
      submittedBody: null, pending: false, feedback: "",
    });
  }
  return state.taskAssignmentDrafts.get(taskId);
}

function renderTaskAssignmentForm(project) {
  const draft = taskAssignmentDraft(project.task_id);
  const locked = draft.pending || draft.submittedBody !== null;
  elements.taskAssignmentAgent.replaceChildren();
  project.members.filter((member) => member.status === "active").forEach((member) => {
    if (!(member.agents || []).length) return;
    const group = document.createElement("fieldset");
    group.className = "task-assignment-human";
    const legend = document.createElement("legend");
    legend.textContent = member.display_name;
    group.append(legend);
    member.agents.forEach((agent) => {
      const label = document.createElement("label");
      label.className = "task-agent-option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "assignment-agent";
      input.value = agent.agent_id;
      input.dataset.humanUserId = member.human_user_id;
      input.checked = draft.agentIds.includes(agent.agent_id);
      input.disabled = locked;
      const name = document.createElement("span");
      name.textContent = `${agent.display_name}${agent.role === "primary" ? "（主 AI）" : ""}`;
      label.append(input, name);
      group.append(label);
    });
    elements.taskAssignmentAgent.append(group);
  });
  elements.taskAssignmentInstruction.value = draft.instruction;
  elements.taskAssignmentOutput.value = draft.expectedOutput;
  elements.taskAssignmentInstruction.disabled = locked;
  elements.taskAssignmentOutput.disabled = locked;
  elements.taskAssignmentSubmit.disabled = draft.pending;
  elements.taskAssignmentSubmit.textContent = draft.pending ? "正在安排…"
    : draft.submittedBody !== null ? "重试确认这批工作" : "交给所选 AI 执行";
  elements.taskAssignmentFeedback.textContent = draft.feedback;
  updateTaskAssignmentSelection();
}

function updateTaskAssignmentSelection() {
  const count = elements.taskAssignmentAgent.querySelectorAll('input:checked').length;
  elements.taskAssignmentSelection.textContent = count
    ? `已选 ${count} 个 AI，将分别执行并反馈。`
    : "请选择至少一个 AI（最多 64 个）。";
}

function saveTaskAssignmentDraft() {
  const project = currentTaskForAction();
  if (!project) return;
  const draft = taskAssignmentDraft(project.task_id);
  if (draft.pending || draft.submittedBody !== null) return;
  draft.agentIds = [...elements.taskAssignmentAgent.querySelectorAll('input:checked')].map(input => input.value);
  draft.instruction = elements.taskAssignmentInstruction.value;
  draft.expectedOutput = elements.taskAssignmentOutput.value;
  updateTaskAssignmentSelection();
}

async function createTaskAssignment(event) {
  event.preventDefault();
  const project = currentTaskForAction();
  if (!project) return;
  const draft = taskAssignmentDraft(project.task_id);
  if (draft.pending) return;
  if (draft.submittedBody === null) {
    saveTaskAssignmentDraft();
    const targets = [...elements.taskAssignmentAgent.querySelectorAll('input:checked')];
    if (!targets.length || targets.length > 64 || !draft.instruction.trim()) {
      elements.taskAssignmentFeedback.textContent = "请勾选 1 至 64 个 AI，并填写明确的工作要求。";
      if (!targets.length) elements.taskAssignmentAgent.querySelector('input')?.focus();
      else elements.taskAssignmentInstruction.focus();
      return;
    }
    draft.submittedBody = JSON.stringify({
      assignees: targets.map(input => ({
        responsible_human_user_id: input.dataset.humanUserId,
        assignee_agent_id: input.value,
      })),
      instruction: draft.instruction.trim(),
      expected_output: draft.expectedOutput.trim() || null,
    });
  }
  const count = JSON.parse(draft.submittedBody).assignees.length;
  draft.pending = true;
  draft.feedback = `正在为 ${count} 个 AI 安排工作…`;
  renderTaskAssignmentForm(project);
  try {
    const updated = await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/assignments/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken, "Idempotency-Key": draft.key },
      body: draft.submittedBody,
    });
    state.taskAssignmentDrafts.delete(project.task_id);
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    renderProjectDetail();
    elements.projectActionResult.textContent = `已为 ${count} 个 AI 分别安排工作，可在任务进展中查看各自状态与结果。`;
  } catch (error) {
    if ([400, 401, 403, 404, 409, 422].includes(error.status)) {
      draft.submittedBody = null;
      draft.feedback = `${error.message}。请检查任务状态与参与 AI 后重试。`;
    } else {
      draft.feedback = `${error.message}。结果尚未确认，请重试同一批工作；已保留原内容，避免重复派工。`;
    }
  } finally {
    draft.pending = false;
    if (currentTaskForAction()?.task_id === project.task_id) renderTaskAssignmentForm(currentTaskForAction());
  }
}

async function respondToWaitingAgent(event) {
  event.preventDefault();
  const project = currentTaskForAction();
  const form = event.currentTarget;
  const assignmentId = form.dataset.assignmentId;
  const response = form.elements.response.value.trim();
  const submit = form.querySelector('button[type="submit"]');
  if (!project || form.dataset.taskId !== project.task_id || !assignmentId || !response) {
    elements.projectActionResult.textContent = "请先填写要回复 AI 的内容。";
    return;
  }
  submit.disabled = true;
  try {
    const updated = await requestJson(
      `/api/v1/tasks/${encodeURIComponent(project.task_id)}`
        + `/assignments/${encodeURIComponent(assignmentId)}/human-response`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
        body: JSON.stringify({ response }),
      },
    );
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    renderProjectDetail();
    elements.projectActionResult.textContent = "回复已记录，AI 执行已重新进入可靠队列。";
  } catch (error) {
    submit.disabled = false;
    if (state.selectedProjectId === project?.task_id) elements.projectActionResult.textContent = error.message;
  }
}

async function submitTaskForAcceptance(event) {
  event.preventDefault();
  const project = currentTaskForAction();
  const summary = elements.taskFinalSummary.value.trim();
  if (!project || !summary) {
    elements.projectActionResult.textContent = "请先填写最终交付汇总。";
    return;
  }
  try {
    const updated = await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ summary }),
    });
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    renderProjectDetail();
    elements.projectActionResult.textContent = "任务已提交，等待 Human 验收。";
  } catch (error) {
    if (state.selectedProjectId === project?.task_id) elements.projectActionResult.textContent = error.message;
  }
}

async function decideTaskAcceptance(decision) {
  const project = currentTaskForAction();
  const note = elements.taskReviewNote.value.trim();
  if (!project) {
    return;
  }
  if (decision === "request_changes" && !note) {
    elements.projectActionResult.textContent = "请说明需要修改的内容。";
    elements.taskReviewNote.focus();
    return;
  }
  try {
    const updated = await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/acceptance`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ decision, note: note || null }),
    });
    if (!acceptTaskUpdate(project.task_id, updated)) return;
    renderProjectDetail();
    elements.projectActionResult.textContent = decision === "accept" ? "Human 已验收通过。" : "已退回修改。";
  } catch (error) {
    if (state.selectedProjectId === project?.task_id) elements.projectActionResult.textContent = error.message;
  }
}

function initializeCollaborationModules() {
  document.querySelector("#task-detail-retry").addEventListener("click", () => {
    state.taskLoadError = "";
    renderProjectDetail();
    void loadProjectDetail(state.selectedProjectId);
  });
  renderProjectBrowser();
  renderFriendBrowser();
  elements.projectSearchInput.addEventListener("input", () => {
    state.projectQuery = elements.projectSearchInput.value;
    renderProjectBrowser();
  });
  elements.projectFilters.forEach((button) => {
    button.addEventListener("click", () => {
      setProjectFilter(button.dataset.projectFilter);
      const projects = filteredProjects();
      if (!projects.some((project) => project.task_id === state.selectedProjectId)) {
        void selectTask(isMobileWorkspace() ? "" : (projects[0]?.task_id || ""));
      } else renderProjectBrowser();
    });
  });
  elements.friendSearchInput.addEventListener("input", () => {
    state.friendQuery = elements.friendSearchInput.value;
    renderFriendBrowser();
    window.clearTimeout(state.friendSearchTimer);
    state.friendSearchTimer = window.setTimeout(() => {
      void loadFriends(state.friendQuery);
    }, 250);
  });
  elements.friendFilters.forEach((button) => {
    button.addEventListener("click", () => {
      state.friendFilter = button.dataset.friendFilter;
      elements.friendFilters.forEach((item) => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      renderFriendBrowser();
    });
  });
  elements.friendPendingNotice.addEventListener("click", () => {
    state.friendFilter = "pending_incoming";
    state.friendQuery = "";
    elements.friendSearchInput.value = "";
    state.selectedFriendId = "";
    renderFriendBrowser();
    updateCollaborationWorkspaceMode();
  });
  [elements.projectBrowserNew, elements.projectEmptyNew].forEach((button) => {
    button.addEventListener("click", openProjectCreateDialog);
  });
  elements.friendStartProject.addEventListener("click", actOnSelectedFriend);
  [elements.projectInvite, elements.projectMemberInvite].forEach((button) => {
    button.addEventListener("click", openProjectInviteDialog);
  });
  bindTaskAction(elements.projectArchive, "click", updateSelectedProjectStatus);
  elements.projectAccept.addEventListener("click", () => decideSelectedProjectInvitation(true));
  elements.projectDecline.addEventListener("click", () => decideSelectedProjectInvitation(false));
  elements.projectCreateForm.addEventListener("submit", createProject);
  elements.projectCreateClose.addEventListener("click", closeProjectCreateDialog);
  elements.projectCreateCancel.addEventListener("click", closeProjectCreateDialog);
  elements.projectInviteForm.addEventListener("submit", inviteProjectFriends);
  elements.projectInviteClose.addEventListener("click", closeProjectInviteDialog);
  elements.projectInviteCancel.addEventListener("click", closeProjectInviteDialog);
  elements.taskAssignmentForm.addEventListener("input", saveTaskAssignmentDraft);
  elements.taskAssignmentForm.addEventListener("submit", createTaskAssignment);
  bindTaskAction(elements.taskMyAgentForm, "submit", saveMyTaskAgent);
  elements.taskAddAgent.addEventListener("click", () => {
    activateRoute("relay", "agents", { focusContent: true });
  });
  elements.projectTaskIdCopy.addEventListener("click", async () => {
    const taskId = state.selectedProject?.task_id;
    if (!taskId) {
      return;
    }
    try {
      await navigator.clipboard.writeText(taskId);
      elements.projectTaskIdCopy.textContent = "已复制";
      window.setTimeout(() => {
        elements.projectTaskIdCopy.textContent = "复制";
      }, 1600);
    } catch (_error) {
      elements.projectActionResult.textContent = "浏览器未允许自动复制，请手动选择任务 ID。";
    }
  });
  bindTaskAction(elements.taskSubmissionForm, "submit", submitTaskForAcceptance);
  bindTaskAction(elements.taskAcceptFinal, "click", () => decideTaskAcceptance("accept"));
  bindTaskAction(elements.taskRequestChanges, "click", () => decideTaskAcceptance("request_changes"));
  elements.projectMobileBack.addEventListener("click", () => {
    if (isMobileWorkspace()) {
      void selectTask("");
      return;
    }
    elements.projectBrowser.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  elements.friendMobileBack.addEventListener("click", () => {
    if (isMobileWorkspace()) {
      state.selectedFriendId = "";
      updateCollaborationWorkspaceMode();
      resetMobileLayerScroll();
      return;
    }
    elements.friendBrowser.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function normalizedRoute(module, section) {
  const definition = MODULE_DEFINITIONS[module] || MODULE_DEFINITIONS.projects;
  const normalizedModule = MODULE_DEFINITIONS[module] ? module : "projects";
  const normalizedSection = definition.sections.includes(section)
    ? section
    : state.lastSectionByModule[normalizedModule] || definition.defaultSection;
  return { module: normalizedModule, section: normalizedSection };
}

function routeUrl(module, section) {
  const url = new URL(window.location.href);
  url.searchParams.set("module", module);
  url.searchParams.set("view", section);
  url.hash = "";
  return `${url.pathname}${url.search}`;
}

function currentRouteUrlWithoutWorkflowParameters() {
  const url = new URL(window.location.href);
  ["pairing", "code", "oauth_request"].forEach((name) => url.searchParams.delete(name));
  url.searchParams.set("module", state.activeModule);
  url.searchParams.set("view", state.activeSection);
  url.hash = "";
  return `${url.pathname}${url.search}`;
}

function applyThreadRouteParameters(parameters) {
  state.threadFilter = ["exception", "archived"].includes(parameters.get("filter"))
    ? parameters.get("filter")
    : "all";
  state.threadQuery = parameters.get("q") || "";
  state.selectedThreadId = parameters.get("thread") || "";
  elements.threadSearchInput.value = state.threadQuery;
  elements.threadFilters.forEach((button) => {
    const active = button.dataset.threadFilter === state.threadFilter;
    button.classList.toggle("active", active);
    if (button.getAttribute("aria-disabled") !== "true") {
      button.setAttribute("aria-pressed", String(active));
    }
  });
}

function applyAgentRouteParameters(parameters) {
  const allowedTabs = new Set([
    "summary",
    "connection",
    "capabilities",
    "access",
    "history",
    "threads",
    "danger",
  ]);
  state.selectedAgentId = parameters.get("agent") || "";
  state.agentTab = allowedTabs.has(parameters.get("agentTab"))
    ? parameters.get("agentTab")
    : "summary";
  state.agentQuery = parameters.get("agentQuery") || "";
  elements.agentSearchInput.value = state.agentQuery;
}

function threadRouteUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("module", "orbit");
  url.searchParams.set("view", "communications");
  const values = {
    filter: state.threadFilter === "all" ? "" : state.threadFilter,
    q: state.threadQuery,
    thread: state.selectedThreadId,
  };
  Object.entries(values).forEach(([name, value]) => {
    if (value) {
      url.searchParams.set(name, value);
    } else {
      url.searchParams.delete(name);
    }
  });
  url.hash = "";
  return `${url.pathname}${url.search}`;
}

function agentRouteUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("module", "relay");
  url.searchParams.set("view", "agents");
  const values = {
    agent: state.selectedAgentId,
    agentTab: state.selectedAgentId && state.agentTab !== "summary" ? state.agentTab : "",
    agentQuery: state.agentQuery,
  };
  Object.entries(values).forEach(([name, value]) => {
    if (value) {
      url.searchParams.set(name, value);
    } else {
      url.searchParams.delete(name);
    }
  });
  url.hash = "";
  return `${url.pathname}${url.search}`;
}

function updateThreadWorkspaceMode() {
  const active = state.activeModule === "orbit" && state.activeSection === "communications";
  elements.workspaceView.classList.toggle("thread-workspace-mode", active);
  elements.workspaceView.classList.toggle(
    "thread-detail-open",
    active && Boolean(state.selectedThreadId),
  );
  elements.threadBrowser.hidden = !active || !state.threadBrowserExpanded;
  elements.threadParentToggle?.setAttribute("aria-expanded", String(state.threadBrowserExpanded));
  elements.threadParentToggle?.classList.toggle("expanded", state.threadBrowserExpanded);
}

function updateAgentWorkspaceMode() {
  const active = state.activeModule === "relay" && state.activeSection === "agents";
  elements.workspaceView.classList.toggle("agent-workspace-mode", active);
  elements.workspaceView.classList.toggle(
    "agent-detail-open",
    active && Boolean(state.selectedAgentId),
  );
  elements.agentBrowser.hidden = !active;
}

function updateCollaborationWorkspaceMode() {
  const projectsActive = state.activeModule === "projects" && state.activeSection === "board";
  const friendsActive = state.activeModule === "friends" && state.activeSection === "directory";
  elements.workspaceView.classList.toggle("project-workspace-mode", projectsActive);
  elements.workspaceView.classList.toggle("friend-workspace-mode", friendsActive);
  elements.workspaceView.classList.toggle(
    "project-detail-open",
    projectsActive && Boolean(state.selectedProjectId),
  );
  elements.workspaceView.classList.toggle(
    "friend-detail-open",
    friendsActive && Boolean(state.selectedFriendId),
  );
  elements.projectBrowser.hidden = !projectsActive;
  elements.friendBrowser.hidden = !friendsActive;
}

function isMobileWorkspace() {
  return window.matchMedia("(max-width: 860px)").matches;
}

function resetMobileLayerScroll() {
  if (isMobileWorkspace()) {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }
}

function activateRoute(module, section, { updateHistory = true, focusContent = false } = {}) {
  const route = normalizedRoute(module, section);
  const definition = MODULE_DEFINITIONS[route.module];
  const routeChanged = state.activeModule !== route.module || state.activeSection !== route.section;
  state.activeModule = route.module;
  state.activeSection = route.section;
  state.lastSectionByModule[route.module] = route.section;

  elements.primaryNavigationItems.forEach((item) => {
    const active = item.dataset.module === route.module;
    item.classList.toggle("active", active);
    if (active) {
      item.setAttribute("aria-current", "page");
    } else {
      item.removeAttribute("aria-current");
    }
  });
  elements.contextNavigationGroups.forEach((group) => {
    group.hidden = group.dataset.contextModule !== route.module;
  });
  elements.contextNavigationItems.forEach((item) => {
    const active = item.dataset.module === route.module && item.dataset.section === route.section;
    item.classList.toggle("active", active);
    if (item.classList.contains("orbit-mobile-shortcut")) {
      item.setAttribute("aria-pressed", String(active));
    }
    if (active) {
      item.setAttribute("aria-current", "page");
    } else {
      item.removeAttribute("aria-current");
    }
  });
  elements.moduleViews.forEach((view) => {
    view.hidden = !(view.dataset.module === route.module && view.dataset.section === route.section);
  });
  elements.contextEyebrow.textContent = definition.label;
  document.querySelector("#context-heading").hidden = route.module === "projects";
  elements.contextTitle.textContent = definition.title;
  elements.contextCopy.textContent = definition.description;
  elements.brandSection.textContent = definition.label;
  document.title = `AgentPost · ${definition.label}`;
  updateThreadWorkspaceMode();
  updateAgentWorkspaceMode();
  updateCollaborationWorkspaceMode();
  if (routeChanged) {
    resetMobileLayerScroll();
  }
  if (updateHistory && routeChanged) {
    history.pushState({ module: route.module, section: route.section }, "", routeUrl(route.module, route.section));
  }
  if (focusContent && !elements.workspaceView.hidden) {
    elements.workspaceView.querySelector(".workspace-content")?.focus({ preventScroll: true });
  }
}

function initializeWorkspaceNavigation() {
  const parameters = new URLSearchParams(window.location.search);
  applyThreadRouteParameters(parameters);
  applyAgentRouteParameters(parameters);
  const route = normalizedRoute(parameters.get("module") || "projects", parameters.get("view") || "");
  activateRoute(route.module, route.section, { updateHistory: false });

  elements.primaryNavigationItems.forEach((item) => {
    item.addEventListener("click", async () => {
      const module = item.dataset.module;
      if (module === "orbit") {
        await returnToAllConversations();
        return;
      }
      activateRoute(module, state.lastSectionByModule[module] || MODULE_DEFINITIONS[module].defaultSection, {
        focusContent: true,
      });
    });
  });
  elements.contextNavigationItems.forEach((item) => {
    item.addEventListener("click", async () => {
      if (item === elements.threadParentToggle) {
        const alreadyActive = state.activeModule === "orbit" && state.activeSection === "communications";
        if (!alreadyActive) {
          state.threadBrowserExpanded = true;
          await returnToAllConversations();
          return;
        }
        state.threadBrowserExpanded = alreadyActive ? !state.threadBrowserExpanded : true;
      }
      const mobileShortcutIsActive = item.classList.contains("orbit-mobile-shortcut")
        && isMobileWorkspace()
        && state.activeModule === "orbit"
        && state.activeSection === item.dataset.section;
      if (item.classList.contains("orbit-mobile-shortcut") && isMobileWorkspace()) {
        state.threadFilter = "all";
        elements.threadFilters.forEach((filter) => {
          const active = (filter.dataset.threadFilter || "all") === "all";
          filter.classList.toggle("active", active);
          filter.setAttribute("aria-pressed", String(active));
        });
      }
      activateRoute(
        item.dataset.module,
        mobileShortcutIsActive ? "communications" : item.dataset.section,
        { focusContent: true },
      );
      updateThreadWorkspaceMode();
      renderThreadParentSummary();
    });
  });
  document.addEventListener("click", async (event) => {
    if (state.activeModule !== "orbit" || !["tasks", "approvals"].includes(state.activeSection)) {
      return;
    }
    if (event.target.closest(
      "button, a, input, select, textarea, details, dialog, .task-item, .approval-card, .section-heading",
    )) {
      return;
    }
    await returnToAllConversations();
  });
  [elements.primaryNavigation, elements.contextNavigation, elements.orbitMobileShortcuts].forEach((navigation) => {
    navigation.addEventListener("keydown", (event) => {
      if (!["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"].includes(event.key)) {
        return;
      }
      const visibleItems = Array.from(navigation.querySelectorAll("button:not([hidden])"))
        .filter((item) => item.offsetParent !== null);
      const currentIndex = visibleItems.indexOf(document.activeElement);
      if (currentIndex < 0 || visibleItems.length < 2) {
        return;
      }
      event.preventDefault();
      const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
      visibleItems[(currentIndex + direction + visibleItems.length) % visibleItems.length].focus();
    });
  });
}

function setConnection(message, kind = "", compactMessage = message) {
  elements.connectionState.className = `connection ${kind}`.trim();
  const dot = document.createElement("span");
  dot.className = "connection-dot";
  dot.setAttribute("aria-hidden", "true");
  const fullLabel = document.createElement("span");
  fullLabel.className = "connection-label-full";
  fullLabel.textContent = message;
  const compactLabel = document.createElement("span");
  compactLabel.className = "connection-label-compact";
  compactLabel.textContent = compactMessage;
  elements.connectionState.replaceChildren(dot, fullLabel, compactLabel);
}

function setFormStatus(message, kind = "") {
  elements.accessResult.className = `form-status ${kind}`.trim();
  elements.accessResult.textContent = message;
}

function errorMessage(payload, status) {
  const error = payload && typeof payload === "object" ? payload.error : null;
  if (status === 422 && Array.isArray(error?.details)) {
    const fields = new Set(
      error.details
        .map((detail) => Array.isArray(detail?.loc) ? detail.loc.at(-1) : null)
        .filter(Boolean),
    );
    if (fields.has("local_agent_id")) {
      return "Agent 地址格式不正确：只填写 @ 前面的部分，并使用小写字母、数字、点、下划线或连字符。";
    }
    if (fields.has("capabilities")) {
      return "能力标签格式不正确：请用逗号分隔，最多 64 项，每项不超过 100 个字符。";
    }
    if (fields.has("display_name")) {
      return "Agent 名称格式不正确：名称不能为空，且不能超过 200 个字符。";
    }
    if (fields.has("handle")) {
      return "短名称格式不正确：请使用 1–32 个中文、英文字母或数字；连字符只能放在名称中间且不能连续。";
    }
    if (fields.has("username")) {
      return "用户名格式不正确：请使用 3–32 位小写字母、数字或单个连字符。";
    }
    return "提交内容格式不正确。请检查页面中填写的 Agent 地址、名称和能力标签。";
  }
  if (status === 409 && Array.isArray(error?.details?.suggestions)) {
    return `这个短名称已被使用。可以试试：${error.details.suggestions.join("、")}。`;
  }
  if (status === 409 && String(error?.code || "").toUpperCase() === "USERNAME_ALREADY_REGISTERED") {
    return "这个用户名已被使用，请换一个。";
  }
  if (error && typeof error.message === "string") {
    return `AgentPost 请求失败（${status}）：${error.message}`;
  }
  return `AgentPost 请求失败（${status}）。`;
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: options.headers || {},
    cache: "no-store",
    credentials: "same-origin",
    redirect: "error",
    referrerPolicy: "no-referrer",
    body: options.body,
  });
  const contentType = response.headers.get("content-type") || "";
  let payload = null;
  if (contentType.includes("application/json")) {
    const responseBody = await response.text();
    payload = responseBody.trim() ? JSON.parse(responseBody) : null;
  }
  if (!response.ok) {
    const error = new Error(errorMessage(payload, response.status));
    error.status = response.status;
    throw error;
  }
  return payload;
}

function safeText(value, fallback = "—") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
}

function dateText(value) {
  if (!value) {
    return "暂无活动";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return safeText(value);
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function mfaProof(value) {
  const candidate = value.trim();
  if (!candidate) {
    return { totp_code: null, recovery_code: null };
  }
  if (/^[0-9]{6}$/.test(candidate)) {
    return { totp_code: candidate, recovery_code: null };
  }
  return { totp_code: null, recovery_code: candidate };
}

function reauthentication(candidate, mfaValue, extra = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-CSRF-Token": state.csrfToken,
  };
  const payload = { ...extra, ...mfaProof(mfaValue) };
  if (candidate.startsWith("hum_")) {
    headers.Authorization = `Bearer ${candidate}`;
  } else {
    payload.password = candidate;
  }
  return { headers, payload };
}

function validReauthenticationCandidate(candidate) {
  return candidate.startsWith("hum_") ? candidate.length >= 20 : candidate.length >= 12;
}

function clearSensitiveInputs() {
  state.taskReplyDrafts.clear();
  state.taskAssignmentDrafts.clear();
  [
    elements.loginPassword,
    elements.loginMfa,
    elements.registerCode,
    elements.registerPassword,
    elements.recoveryCode,
    elements.recoveryPassword,
    elements.recoveryMfa,
    elements.mfaPassword,
    elements.mfaCurrentProof,
    elements.mfaConfirmCode,
    elements.keyPassword,
    elements.keyMfa,
    elements.approvalAccessKey,
    elements.approvalMfa,
    elements.pairingAccessKey,
    elements.revokeAccessKey,
    elements.revokeMfa,
  ].forEach((input) => {
    if (input) {
      input.value = "";
    }
  });
  elements.mfaProvisioning.textContent = "";
  elements.mfaProvisioning.hidden = true;
  elements.keyOutput.textContent = "";
  elements.keyOutput.hidden = true;
}

function emptyState(message) {
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = message;
  return empty;
}

function emptyStateWithAction(message, label, action) {
  const empty = document.createElement("div");
  empty.className = "empty-state action-empty-state";
  const copy = document.createElement("p");
  copy.textContent = message;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "quiet-button";
  button.textContent = label;
  button.addEventListener("click", action);
  empty.append(copy, button);
  return empty;
}

function statusLabel(value, type = "status") {
  if (type === "approval" && value === "pending") {
    return "待审批";
  }
  const labels = {
    pending: "待处理",
    approved: "已批准",
    rejected: "已拒绝",
    expired: "已过期",
    completed: "已完成",
    partial: "部分完成",
    failed: "失败",
    cancelled: "已取消",
    accepted: "正在投递",
    delivered: "已送达",
    read: "Agent 已读取",
    acked: "Agent 已确认收到",
    replied: "已回复",
    low: "低",
    normal: "普通",
    high: "高",
    urgent: "紧急",
    active: "运行中",
    owner: "所有者",
    operator: "操作员",
    viewer: "观察者",
    auditor: "审计者",
    consumed: "已领取",
    denied: "已拒绝",
    revoked: "已撤销",
    replaced: "已替换",
    verified: "已验证",
    unknown: "尚未上报",
    healthy: "健康",
    degraded: "降级",
    error: "故障",
    connected: "在线",
    disconnected: "未连接",
    offline: "离线",
    connection_error: "连接异常",
    awaiting_agent: "等待 Agent 完成本机连接",
    ready: "可接任务",
    working: "正在工作",
    recovering: "恢复中",
    needs_attention: "需要处理",
    listening: "正在监听",
    stopped: "已停止监听",
  };
  return labels[value] || safeText(value);
}

function chip(value, type = "status") {
  const item = document.createElement("span");
  item.className = `data-chip ${type} ${safeText(value, "unknown")}`;
  item.textContent = statusLabel(value, type);
  return item;
}

function agentHumanStatus(agent) {
  if (agent.work_availability === "needs_attention") {
    if (agent.connection_state === "connection_error") {
      return { label: "连接异常", className: "connection_error" };
    }
    return { label: "暂不可接任务", className: "needs_attention" };
  }
  return {
    label: statusLabel(agent.work_availability),
    className: safeText(agent.work_availability, "unknown"),
  };
}

function renderAgents(agents) {
  renderAgentOverview(agents);
  renderAgentBrowser(agents);
  if (state.selectedAgentId) {
    const agent = agents.find((item) => String(item.id) === state.selectedAgentId);
    if (agent) {
      renderAgentDetail(agent);
      void loadAgentRelatedThreads(agent);
    } else {
      renderMissingAgent();
    }
  } else {
    renderAgentOverviewState();
  }
}

function agentConnectionCopy(agent) {
  const copies = {
    connected: `${safeText(agent.current_connector_name, agent.current_connector_type || "当前连接")} 正常连接，最近连接 ${dateText(agent.current_connector_last_heartbeat_at)}`,
    awaiting_agent: "你已完成授权，正在等待 Agent 完成设置并首次上线",
    disconnected: "没有当前有效连接；Agent 身份和历史仍保留",
    offline: `曾经连接，但最近连接已超时（${dateText(agent.current_connector_last_heartbeat_at)}）`,
    connection_error: `检测到明确连接异常${agent.current_connector_error_code ? `：${safeText(agent.current_connector_error_code)}` : ""}`,
  };
  return copies[agent.connection_state] || "连接证据不足";
}

function agentAvailabilityCopy(agent) {
  const copies = {
    ready: `任务监听正常，最近确认 ${dateText(agent.current_task_listener_last_heartbeat_at)}`,
    working: "已有任务 Run 正在执行，进度以任务页的运行记录为准",
    recovering: "AgentPost 正在尝试恢复任务执行",
    needs_attention: agent.connection_state === "connected"
      ? agent.current_task_listener_status === "listening"
        ? `平台曾收到任务监听上报，但最近证据已过期（${dateText(agent.current_task_listener_last_heartbeat_at)}）；请重新连接或重启任务监听。`
        : agent.current_task_listener_status === "stopped"
          ? "连接可以通信，任务监听已明确停止；新工作会继续排队。"
          : "连接可以通信，但平台尚未收到任务监听上报；本机存在轮询进程也不能代替服务端心跳证据。"
      : agentConnectionCopy(agent),
  };
  return copies[agent.work_availability] || "暂时没有足够证据判断是否能接任务";
}

function agentMatchesQuery(agent) {
  if (!state.agentQuery) {
    return true;
  }
  const searchable = [
    agent.handle,
    agent.display_name,
    agent.address,
    agent.current_connector_type,
    ...(agent.capabilities || []),
  ].map((value) => safeText(value, "").toLocaleLowerCase("zh-CN"));
  return searchable.some((value) => value.includes(state.agentQuery.toLocaleLowerCase("zh-CN")));
}

function renderAgentOverview(agents) {
  const counts = {
    ready: 0,
    working: 0,
    recovering: 0,
    needs_attention: 0,
  };
  agents.forEach((agent) => {
    if (Object.hasOwn(counts, agent.work_availability)) {
      counts[agent.work_availability] += 1;
    }
  });
  elements.agentStatAll.textContent = String(agents.length);
  elements.agentStatConnected.textContent = String(counts.ready);
  elements.agentStatAwaiting.textContent = String(counts.working);
  elements.agentStatOffline.textContent = String(counts.recovering);
  elements.agentStatError.textContent = String(counts.needs_attention);
  elements.agentOverviewGroups.replaceChildren();
  if (!agents.length) {
    elements.agentOverviewGroups.append(emptyState("还没有可查看的 Agent。连接新的 Agent 后会在这里出现。"));
    return;
  }
  const values = [["我的 AI", agents.length, "任务中的参与范围由任务成员和所选 AI 共同确定"]];
  values.forEach(([name, count, copy]) => {
    const card = document.createElement("article");
    const label = document.createElement("span");
    label.textContent = name;
    const number = document.createElement("strong");
    number.textContent = `${count} 个`;
    const description = document.createElement("p");
    description.textContent = copy;
    card.append(label, number, description);
    elements.agentOverviewGroups.append(card);
  });
}

function agentBrowserButton(agent) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "agent-browser-item";
  button.classList.toggle("active", String(agent.id) === state.selectedAgentId);
  if (String(agent.id) === state.selectedAgentId) {
    button.setAttribute("aria-current", "true");
  }
  const identity = document.createElement("span");
  identity.className = "agent-browser-identity";
  const avatar = agentAvatar(agent, "agent-mini-avatar");
  const names = document.createElement("span");
  const name = document.createElement("strong");
  name.textContent = agentDisplayName(agent);
  const display = document.createElement("small");
  display.textContent = `${safeText(agent.display_name)} · ${agent.current_connector_type ? agentTypeLabel({ agent_type: agent.current_connector_type }) : "类型未提供"}`;
  names.append(name, display);
  identity.append(avatar, names);
  const humanStatus = agentHumanStatus(agent);
  const status = chip(humanStatus.className);
  status.textContent = humanStatus.label;
  status.title = agentAvailabilityCopy(agent);
  button.append(identity, status);
  button.addEventListener("click", () => selectAgent(String(agent.id)));
  return button;
}

function renderAgentBrowser(agents) {
  const visible = agents.filter(agentMatchesQuery);
  elements.agentBrowserCount.textContent = `${visible.length} 个`;
  elements.agentBrowserList.replaceChildren();
  if (!visible.length) {
    elements.agentBrowserList.append(emptyState(
      state.agentQuery ? "没有找到符合条件且你有权查看的 Agent。" : "当前没有可查看的 Agent。",
    ));
    return;
  }
  const appendGroup = (title, values) => {
    if (!values.length) return;
    const section = document.createElement("section");
    section.className = "agent-browser-group";
    const heading = document.createElement("h3");
    heading.textContent = `${title} · ${values.length}`;
    section.append(heading);
    values.forEach((agent) => section.append(agentBrowserButton(agent)));
    elements.agentBrowserList.append(section);
  };
  appendGroup("我的 AI", visible);
}

function renderAgentOverviewState() {
  state.selectedAgent = null;
  elements.agentOverview.hidden = false;
  elements.agentDetail.hidden = true;
  elements.agentDetailMissing.hidden = true;
  updateAgentWorkspaceMode();
  if (state.activeModule === "relay") {
    document.title = "AgentPost · AI";
  }
}

function detailFact(label, value, copy = "") {
  const card = document.createElement("article");
  const name = document.createElement("span");
  name.textContent = label;
  const detail = document.createElement("strong");
  detail.textContent = safeText(value);
  card.append(name, detail);
  if (copy) {
    const description = document.createElement("p");
    description.textContent = copy;
    card.append(description);
  }
  return card;
}

function renderCurrentAgentConnection(agent) {
  elements.agentCurrentConnection.replaceChildren();
  const intro = document.createElement("div");
  const humanStatus = agentHumanStatus(agent);
  intro.className = `agent-connection-banner ${humanStatus.className}`;
  const heading = document.createElement("strong");
  heading.textContent = humanStatus.label;
  const copy = document.createElement("p");
  copy.textContent = agentAvailabilityCopy(agent);
  intro.append(heading, copy);
  elements.agentCurrentConnection.append(intro);
  if (agent.connection_state === "disconnected") {
    return;
  }
  const facts = document.createElement("div");
  facts.className = "agent-detail-summary";
  [
    ["Agent 类型", agent.current_connector_type || "未提供"],
    ["当前连接", agent.current_connector_name || "名称未提供"],
    ["设备", agent.current_connector_device || "设备未提供"],
    ["初始连接时间", dateText(agent.current_connector_activated_at)],
    ["最近连接时间", dateText(agent.current_connector_last_heartbeat_at)],
    ["最近心跳的健康上报（不代表当前在线）", statusLabel(agent.current_connector_health || "unknown")],
    ["平台收到的任务监听", statusLabel(agent.current_task_listener_status || "unknown")],
    ["平台最近收到监听上报", dateText(agent.current_task_listener_last_heartbeat_at)],
    ["唤醒方式", ({ automatic: "AgentPost 可自动唤醒", manual: "需先手动启动监听", unsupported: "当前宿主不支持" })[agent.current_wake_capability] || "未上报"],
  ].forEach(([label, value]) => facts.append(detailFact(label, value)));
  const technical = document.createElement("details");
  technical.className = "agent-technical-details";
  const summary = document.createElement("summary");
  summary.textContent = "查看连接详情";
  const version = document.createElement("p");
  version.textContent = `首次接入版本：${safeText(agent.current_connector_version, "未提供")}；当前运行版本请到“连接管理”查看。`;
  technical.append(summary, version);
  elements.agentCurrentConnection.append(facts, technical);
}

function wakeErrorCopy(code) {
  return ({
    WAKE_RATE_LIMITED: "一分钟内已有发送，请稍后再试；本次没有触发工作流",
    WAKE_BUSINESS_REJECTED: "工作流未接受请求，提醒已暂停，请核对协议、密钥及飞书执行记录",
    WAKE_RESULT_UNKNOWN: "发送被中断，结果不明；提醒已暂停，请核对飞书执行记录后再测试恢复",
    WAKE_TRANSPORT_ERROR: "网络结果不明，可能已触发；请先核对飞书记录，勿连续测试",
    WAKE_INVALID_RESPONSE: "返回内容无法识别，请核对飞书记录；不会自动重试",
  })[code] || safeText(code, "请检查工作流地址和密钥");
}

function renderAgentWakeChannel(agent, channel = null) {
  const supported = agent.role === "owner";
  elements.agentWakeChannel.hidden = !supported;
  if (!supported) return;
  const isAily = agent.current_connector_type === "feishu_aily";
  const configured = Boolean(channel);
  const labels = {
    configured: "等待测试后启用",
    active: isAily ? "自动唤醒已启用" : "飞书提醒已启用",
    error: "提醒已暂停",
  };
  const status = channel?.status || "awaiting_agent";
  elements.agentWakeStatus.className = `data-chip ${status === "active" ? "ready" : status === "error" ? "needs_attention" : "awaiting_agent"}`;
  elements.agentWakeStatus.textContent = labels[status] || "尚未配置";
  elements.agentWakeTag.textContent = isAily ? "飞书 aily · 自动接任务" : "Human 通知 · 飞书 Webhook";
  elements.agentWakeTitle.textContent = isAily ? "任务唤醒" : "飞书消息提醒";
  elements.agentWakeCopy.textContent = configured
    ? `已保存 ${safeText(channel.endpoint_host)} 的加密配置。待发送：${Number(channel.pending_deliveries || 0)}；最近成功：${dateText(channel.last_success_at)}。验证协议：${channel.auth_scheme === "hmac_sha256" ? "HMAC-SHA256" : "Bearer Token"}。重新保存时需要同时输入完整地址和密钥。`
    : isAily
      ? "在飞书 aily 中建立接收 AgentPost 唤醒事件的工作流，再把工作流提供的 HTTPS 地址和 Bearer Token 填到这里。"
      : "在飞书自动化中建立 Webhook 触发器和“发送飞书消息”动作，按工作流要求选择 HMAC 签名或 Bearer Token，再保存 HTTPS 地址与密钥。这里仅提醒你有新工作，不代表这个 Agent 已启动或开始执行。";
  elements.agentWakeTest.textContent = isAily ? "发送测试唤醒" : "发送测试提醒";
  elements.agentWakeDisable.textContent = isAily ? "停用自动唤醒" : "停用飞书提醒";
  elements.agentWakeSecurity.textContent = isAily
    ? "地址和 Token 加密保存，页面不会再次显示；唤醒事件只含任务、工单和 Run ID，任务正文仍由 aily 通过授权后的 AgentPost MCP 读取。"
    : "地址和 Token 加密保存，页面不会再次显示；提醒只含任务、工单、Run 和目标 Agent ID，不授予飞书读取任务正文或代替 Agent 执行的权限。";
  elements.agentWakeAuth.value = channel?.auth_scheme || "hmac_sha256";
  elements.agentWakeTestConsent.checked = false;
  elements.agentWakeTest.disabled = !configured;
  elements.agentWakeDisable.disabled = !configured;
  elements.agentWakeUrl.value = "";
  elements.agentWakeToken.value = "";
  elements.agentWakeResult.textContent = channel?.last_error_code
    ? `最近发送：${wakeErrorCopy(channel.last_error_code)}`
    : "";
  elements.agentWakeResult.className = channel?.last_error_code ? "form-status error" : "form-status";
}

async function loadAgentWakeChannel(agent) {
  renderAgentWakeChannel(agent);
  if (agent.role !== "owner") return;
  try {
    const channel = await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/wake-channel`);
    if (String(state.selectedAgent?.id) === String(agent.id)) renderAgentWakeChannel(agent, channel);
  } catch (error) {
    if (error.status !== 404 && String(state.selectedAgent?.id) === String(agent.id)) {
      elements.agentWakeResult.textContent = error.message;
      elements.agentWakeResult.className = "form-status error";
    }
  }
}

function renderAgentConnectionHistory(agent) {
  elements.agentConnectionHistory.replaceChildren();
  if (agent.role !== "owner") {
    elements.agentConnectionHistory.append(emptyState("连接历史属于 Agent 所有者的审计信息；当前权限只提供连接状态。"));
    return;
  }
  const history = state.connectors.filter(
    (connector) => String(connector.agent?.id) === String(agent.id)
      && !(connector.is_current && connector.status === "active"),
  );
  if (!history.length) {
    elements.agentConnectionHistory.append(emptyState("还没有过去的连接记录。"));
    return;
  }
  history.forEach((connector) => elements.agentConnectionHistory.append(connectorCard(connector, true)));
}

function renderAgentAccess(agent) {
  elements.agentDetailAccess.replaceChildren();
  elements.agentDetailAccess.append(
    detailFact("当前权限", statusLabel(agent.role), "可执行的操作以你的实际权限为准。"),
  );
}

function renderAgentCapabilities(agent) {
  elements.agentDetailCapabilities.replaceChildren();
  const values = Array.isArray(agent.capabilities) ? agent.capabilities : [];
  if (!values.length) {
    const empty = document.createElement("span");
    empty.textContent = "Agent 尚未声明能力";
    elements.agentDetailCapabilities.append(empty);
    return;
  }
  values.forEach((capability) => {
    const value = document.createElement("span");
    value.textContent = safeText(capability);
    elements.agentDetailCapabilities.append(value);
  });
}

function renderAgentTab() {
  elements.agentDetailTabs.forEach((button) => {
    const active = button.dataset.agentTab === state.agentTab;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  elements.agentDetailPanels.forEach((panel) => {
    panel.hidden = panel.dataset.agentPanel !== state.agentTab;
  });
}

function renderAgentDetail(agent) {
  state.selectedAgent = agent;
  elements.agentOverview.hidden = true;
  elements.agentDetailMissing.hidden = true;
  elements.agentDetail.hidden = false;
  elements.agentDetailName.textContent = agentDisplayName(agent);
  elements.agentDetailSubtitle.textContent = agent.handle
    ? safeText(agent.display_name)
    : `${safeText(agent.display_name)} · 尚未设置短名称`;
  elements.agentDetailAvatar.textContent = agentDisplayName(agent).slice(0, 1).toUpperCase();
  elements.agentDetailAvatar.style.setProperty("--agent-hue", String(agentHue(agent)));
  const humanStatus = agentHumanStatus(agent);
  elements.agentDetailStatus.className = `data-chip ${humanStatus.className}`;
  elements.agentDetailStatus.textContent = humanStatus.label;
  elements.agentDetailStatus.title = agentAvailabilityCopy(agent);
  elements.agentDetailSummary.replaceChildren(
    detailFact("常用名称", agentDisplayName(agent)),
    detailFact("显示名称", agent.display_name),
    detailFact(
      "别人通过我的用户名联系时",
      agent.is_default ? "由这个 Agent 接收" : "由其他默认 Agent 接收",
    ),
    detailFact("最近活动", dateText(agent.last_seen_at)),
    detailFact("待 Agent 读取", agent.unread_count, "表示消息还未被 Agent 读取。"),
    detailFact("进行中任务", agent.pending_task_count),
  );
  const identity = document.createElement("details");
  identity.className = "agent-technical-details";
  const identitySummary = document.createElement("summary");
  identitySummary.textContent = "查看底层身份";
  const address = document.createElement("p");
  address.textContent = safeText(agent.address);
  identity.append(identitySummary, address);
  elements.agentDetailSummary.append(identity);
  renderCurrentAgentConnection(agent);
  void loadAgentWakeChannel(agent);
  renderAgentCapabilities(agent);
  renderAgentAccess(agent);
  renderAgentConnectionHistory(agent);
  const owner = agent.role === "owner";
  elements.agentOwnerActions.hidden = !owner;
  elements.agentReadonlyActions.hidden = owner;
  elements.agentRename.hidden = !owner;
  elements.agentSetDefault.hidden = !owner;
  elements.agentSetDefault.disabled = Boolean(agent.is_default);
  elements.agentSetDefault.textContent = agent.is_default ? "默认 Agent" : "设为默认 Agent";
  const currentOwnedConnector = state.connectors.find(
    (connector) => String(connector.agent?.id) === String(agent.id)
      && connector.is_current && connector.status === "active",
  );
  elements.agentDisconnect.hidden = !currentOwnedConnector;
  elements.agentRename.textContent = agent.handle ? "修改短名称" : "设置短名称";
  const returnThread = new URLSearchParams(window.location.search).get("returnThread");
  elements.agentReturnThread.hidden = !returnThread;
  renderAgentTab();
  updateAgentWorkspaceMode();
  document.title = `AgentPost · ${agentDisplayName(agent)}`;
}

function renderMissingAgent() {
  state.selectedAgent = null;
  elements.agentOverview.hidden = true;
  elements.agentDetail.hidden = true;
  elements.agentDetailMissing.hidden = false;
  updateAgentWorkspaceMode();
}

async function loadAgentRelatedThreads(agent) {
  state.agentRelatedThreads = [];
  elements.agentRelatedThreads.replaceChildren(emptyState("正在读取相关对话…"));
  try {
    const threads = await requestJson(
      `/api/v1/orbit/threads?limit=200&agent_id=${encodeURIComponent(agent.id)}`,
    );
    if (!state.selectedAgent || String(state.selectedAgent.id) !== String(agent.id)) {
      return;
    }
    state.agentRelatedThreads = Array.isArray(threads) ? threads : [];
    elements.agentRelatedThreads.replaceChildren();
    if (!state.agentRelatedThreads.length) {
      elements.agentRelatedThreads.append(emptyState("这个 Agent 还没有你有权查看的相关对话。"));
      return;
    }
    state.agentRelatedThreads.forEach((thread) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "agent-related-thread";
      const topic = document.createElement("strong");
      topic.textContent = safeText(thread.topic, "无主题对话");
      const meta = document.createElement("span");
      meta.textContent = `${thread.message_count} 条消息 · ${dateText(thread.latest_activity_at)}`;
      button.append(topic, meta);
      button.addEventListener("click", () => openRelatedThread(String(thread.thread_id)));
      elements.agentRelatedThreads.append(button);
    });
  } catch (_error) {
    elements.agentRelatedThreads.replaceChildren(emptyState("相关对话暂时无法读取，请稍后刷新。"));
  }
}

function openRelatedThread(threadId) {
  state.selectedThreadId = threadId;
  state.threadQuery = "";
  state.threadFilter = "all";
  const url = new URL(window.location.href);
  ["agent", "agentTab", "agentQuery", "returnThread"].forEach((name) => url.searchParams.delete(name));
  url.searchParams.set("module", "orbit");
  url.searchParams.set("view", "communications");
  url.searchParams.set("thread", threadId);
  url.searchParams.delete("q");
  url.searchParams.delete("filter");
  history.pushState({ module: "orbit", section: "communications", thread: threadId }, "", `${url.pathname}${url.search}`);
  activateRoute("orbit", "communications", { updateHistory: false, focusContent: true });
  renderThreadList();
  void loadThreadDetail(threadId);
}

function selectAgent(agentId, { updateHistory = true } = {}) {
  state.selectedAgentId = String(agentId);
  state.agentTab = "summary";
  const agent = (state.dashboard?.agents || []).find(
    (item) => String(item.id) === state.selectedAgentId,
  );
  renderAgentBrowser(state.dashboard?.agents || []);
  if (updateHistory) {
    history.pushState({ module: "relay", section: "agents", agent: agentId }, "", agentRouteUrl());
  }
  if (agent) {
    renderAgentDetail(agent);
    void loadAgentRelatedThreads(agent);
    if (isMobileWorkspace()) {
      elements.agentMobileBack.scrollIntoView({ block: "start" });
      elements.agentMobileBack.focus({ preventScroll: true });
    } else {
      elements.agentDetailName.focus({ preventScroll: true });
    }
  } else {
    renderMissingAgent();
  }
}

function clearAgentSelection({ updateHistory = true } = {}) {
  state.selectedAgentId = "";
  state.selectedAgent = null;
  state.agentTab = "summary";
  renderAgentBrowser(state.dashboard?.agents || []);
  renderAgentOverviewState();
  if (updateHistory) {
    history.pushState({ module: "relay", section: "agents" }, "", agentRouteUrl());
  }
  resetMobileLayerScroll();
}

function openHandleDialog(agent) {
  elements.handleAgentId.value = safeText(agent.id, "");
  elements.agentHandle.value = safeText(agent.handle, "");
  elements.handleSummary.textContent = `为 ${safeText(agent.display_name, "这个 Agent")} 设置容易记住的称呼。`;
  elements.handleResult.textContent = agent.handle
    ? "修改后，底层身份、权限、连接和历史消息都保持不变。"
    : "设置后，你可以在收件人、任务和 Agent 列表中使用这个短名称。";
  elements.handleResult.className = "form-status";
  elements.handleDialog.showModal();
  elements.agentHandle.focus();
}

function closeHandleDialog() {
  elements.handleAgentId.value = "";
  elements.agentHandle.value = "";
  elements.handleResult.textContent = "";
  if (elements.handleDialog.open) {
    elements.handleDialog.close();
  }
}

async function saveAgentHandle(event) {
  event.preventDefault();
  const agentId = elements.handleAgentId.value.trim();
  const handle = elements.agentHandle.value.trim().toLowerCase();
  elements.agentHandle.value = handle;
  const handleProblem = agentHandleProblem(handle);
  if (!agentId || handleProblem) {
    elements.handleResult.textContent = handleProblem || "没有找到要修改的 Agent，请关闭后重试。";
    elements.handleResult.className = "form-status error";
    return;
  }
  elements.handleSubmit.disabled = true;
  elements.handleResult.textContent = "正在保存短名称…";
  elements.handleResult.className = "form-status";
  try {
    await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agentId)}/handle`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ handle: handle || null }),
    });
    closeHandleDialog();
    await loadDashboard();
    setConnection(handle ? `短名称 ${handle} 已保存` : "Agent 短名称已移除", "success");
  } catch (error) {
    elements.handleResult.textContent = error.message;
    elements.handleResult.className = "form-status error";
  } finally {
    elements.handleSubmit.disabled = false;
  }
}

async function setSelectedAgentAsDefault() {
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner" || agent.is_default) return;
  elements.agentSetDefault.disabled = true;
  elements.agentSetDefault.textContent = "正在设置…";
  try {
    await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/default`, {
      method: "PUT",
      headers: { "X-CSRF-Token": state.csrfToken },
    });
    await loadDashboard();
    setConnection(`${agentDisplayName(agent)} 已设为默认 Agent`, "success");
  } catch (error) {
    elements.agentSetDefault.disabled = false;
    elements.agentSetDefault.textContent = "设为默认 Agent";
    setConnection(error.message, "error");
  }
}

function openRevokeDialog(connector) {
  elements.revokeConnectorId.value = safeText(connector.connector_id, "");
  const agentLabel = connector.agent?.handle || connector.agent?.display_name || connector.agent?.address;
  elements.revokeSummary.textContent = `将断开 ${safeText(agentLabel, "这个 Agent")} 当前使用的 ${safeText(connector.display_name)} 连接。`;
  elements.revokeResult.textContent = "请重新输入当前密码（或旧版集成凭证）；验证后输入内容会立即清除。";
  elements.revokeResult.className = "form-status";
  elements.revokeDialog.showModal();
  elements.revokeAccessKey.focus();
}

function connectorVersionLabel(status) {
  return {
    current: "已是最新版",
    update_available: "建议升级",
    update_required: "需要升级",
    unknown: "需要检查",
  }[status] || "需要检查";
}

function connectorVersionAdvice(connector) {
  const advice = document.createElement("section");
  advice.className = `connector-version-advice ${connector.version_status}`;
  const heading = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = connectorVersionLabel(connector.version_status);
  const target = document.createElement("span");
  target.textContent = `推荐版本 ${safeText(connector.recommended_version)}`;
  heading.append(title, target);
  const reason = document.createElement("p");
  reason.textContent = safeText(connector.upgrade_reason);
  advice.append(heading, reason);

  if (connector.upgrade_prompt) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "查看安全升级方法";
    const prompt = document.createElement("pre");
    prompt.textContent = connector.upgrade_prompt;
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "quiet-button";
    copy.textContent = "复制升级指令";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(connector.upgrade_prompt);
        copy.textContent = "已复制";
      } catch (_error) {
        details.open = true;
        copy.textContent = "请手动复制上方指令";
      }
    });
    details.append(summary, prompt, copy);
    advice.append(details);
  }
  return advice;
}

function connectorCard(connector, historical = false) {
  const card = document.createElement("article");
  card.className = historical ? "connector-card historical" : "connector-card";
  const heading = document.createElement("div");
  heading.className = "connector-heading";
  const identity = document.createElement("div");
  const name = document.createElement("strong");
  const agentLabel = connector.agent?.handle || connector.agent?.display_name || "这个 Agent";
  name.textContent = safeText(agentLabel, "这个 Agent");
  const connectionName = document.createElement("span");
  connectionName.textContent = safeText(connector.display_name, "本机连接");
  identity.append(name, connectionName);
  const connectionBadge = chip(historical ? connector.status : connector.work_availability);
  if (!historical) connectionBadge.textContent = agentHumanStatus(connector).label;
  heading.append(identity, connectionBadge);

  const facts = document.createElement("dl");
  [
    ["Agent 类型", connector.connector_type],
    ["设备", connector.device_name],
    ["实际运行版本", connector.runtime_version || "未上报"],
    ["升级建议", connectorVersionLabel(connector.version_status)],
    ["初始连接时间", dateText(connector.activated_at)],
    ["最近连接时间", dateText(connector.last_heartbeat_at)],
    ["当前连接状态", statusLabel(connector.connection_state)],
    ["接任务状态", agentHumanStatus(connector).label],
  ].forEach(([label, value]) => {
    const cell = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = safeText(value);
    cell.append(term, detail);
    facts.append(cell);
  });
  card.append(heading, facts);

  const technicalDetails = document.createElement("details");
  technicalDetails.className = "connector-technical-details";
  const technicalSummary = document.createElement("summary");
  technicalSummary.textContent = "查看连接详情";
  const technicalFacts = document.createElement("dl");
  [
    ["规范地址", connector.agent?.address],
    ["首次接入版本", connector.client_version],
    ["已安装版本", connector.installed_version],
    ["配置目标版本", connector.configured_version],
    ["当前运行版本", connector.runtime_version],
    ["当前会话启动", dateText(connector.runtime_session_started_at)],
    ["版本上报时间", dateText(connector.runtime_version_reported_at)],
    ["实际加载能力", (connector.runtime_capabilities || []).join("、") || "未上报"],
    ["最近心跳的健康上报（不代表当前在线）", statusLabel(connector.health_status)],
    ["任务监听原始状态", connector.task_listener_status || "未上报"],
    ["监听会话", connector.task_listener_session_id || "未上报"],
    ["最近监听心跳", dateText(connector.task_listener_last_heartbeat_at)],
    ["唤醒能力", connector.wake_capability || "未上报"],
    ["推荐版本", connector.recommended_version],
    ["最低完整协作版本", connector.minimum_supported_version],
  ].forEach(([label, value]) => {
    const cell = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = safeText(value);
    cell.append(term, detail);
    technicalFacts.append(cell);
  });
  technicalDetails.append(technicalSummary, technicalFacts);
  card.append(technicalDetails);

  if (connector.reconnect_required) {
    const reconnectNotice = document.createElement("p");
    reconnectNotice.className = "connector-reconnect-notice";
    reconnectNotice.textContent = "新版本已安装或已配置，但当前会话仍在运行旧版本；请重新连接后再确认升级完成。";
    card.append(reconnectNotice);
  }

  if (
    connector.is_current
    && connector.status === "active"
    && connector.version_status !== "current"
  ) {
    card.append(connectorVersionAdvice(connector));
  }

  if (connector.is_current && connector.status === "active") {
    const actions = document.createElement("div");
    actions.className = "connector-actions";
    const current = document.createElement("span");
    const connected = connector.connection_state === "connected";
    current.textContent = connected
      ? "当前连接 · Agent 身份和历史记录会独立保留"
      : connector.connection_state === "awaiting_agent"
        ? "授权已完成，等待 Agent 首次上线；身份和历史保留"
        : connector.connection_state === "offline"
          ? "曾经连接，当前心跳已超时；请在原宿主恢复连接，无需新建 Agent"
          : "当前连接异常或已断开，请查看连接详情；身份和历史保留";
    const revoke = document.createElement("button");
    revoke.type = "button";
    revoke.className = "quiet-button danger";
    revoke.textContent = connector.connection_state === "awaiting_agent" ? "取消未完成连接" : "撤销连接";
    revoke.addEventListener("click", () => openRevokeDialog(connector));
    actions.append(current, revoke);
    card.append(actions);
  }
  return card;
}

function renderConnectors(connectors) {
  elements.connectorList.replaceChildren();
  if (!connectors.length) {
    elements.connectorList.append(emptyStateWithAction(
      "还没有连接 Agent。选择你常用的 Agent 类型，然后复制一句话发给它即可。",
      "连接新的 Agent",
      () => openPairingDialog(),
    ));
    return;
  }
  const currentConnectors = connectors.filter(
    (connector) => connector.is_current && connector.status === "active",
  );
  const historicalConnectors = connectors.filter(
    (connector) => !(connector.is_current && connector.status === "active"),
  );
  const fragment = document.createDocumentFragment();
  if (currentConnectors.length === 0) {
    fragment.append(emptyState("当前没有已连接的 Agent；已有身份和历史仍保留。"));
  } else {
    currentConnectors.forEach((connector) => fragment.append(connectorCard(connector)));
  }
  if (historicalConnectors.length > 0) {
    const history = document.createElement("details");
    history.className = "connector-history";
    const summary = document.createElement("summary");
    summary.textContent = `查看 ${historicalConnectors.length} 条历史连接记录`;
    const explanation = document.createElement("p");
    explanation.textContent = "这些是同一 Agent 过去使用过的连接，仅为审计保留，不是多个可删除的 Agent。";
    const historyGrid = document.createElement("div");
    historyGrid.className = "connector-history-grid";
    historicalConnectors.forEach((connector) => {
      historyGrid.append(connectorCard(connector, true));
    });
    history.append(summary, explanation, historyGrid);
    fragment.append(history);
  }
  elements.connectorList.append(fragment);
}

function showPairingGuide(targetAgent = state.pairingTargetAgent, preferredHost = "") {
  state.pairingTargetAgent = targetAgent || null;
  state.pairingNewAgentIntent = targetAgent
    ? ""
    : state.pairingNewAgentIntent || crypto.randomUUID();
  elements.pairingGuide.hidden = false;
  elements.pairingApproval.hidden = true;
  elements.pairingDialogSummary.textContent = targetAgent
    ? `重新连接 ${safeText(targetAgent.handle, targetAgent.display_name)}。复制接入码到它的普通对话框，原身份和历史保持不变。`
    : "先选择你正在使用的 Agent。AgentPost 会生成一段接入码，复制到它的普通对话框即可。";
  state.selectedPairingHost = "";
  elements.pairingHostCards.forEach((button) => {
    const host = button.dataset.connectorType;
    const unavailable = PAIRING_HOSTS[host]?.connectionMode === "unavailable"
      || state.authConfig?.host_connection_modes?.[host] === "unavailable";
    button.classList.remove("selected");
    button.classList.toggle("unavailable", unavailable);
    button.disabled = unavailable;
    button.setAttribute("aria-disabled", String(unavailable));
    button.setAttribute("aria-pressed", "false");
    const description = button.querySelector("span");
    if (description?.dataset.defaultCopy) {
      description.textContent = unavailable ? "暂未开放" : description.dataset.defaultCopy;
    }
  });
  elements.pairingChatCard.hidden = true;
  elements.pairingChatPrompt.textContent = "";
  elements.pairingCopyResult.textContent = "";
  elements.pairingCopyResult.className = "form-status";
  if (PAIRING_HOSTS[preferredHost]
    && PAIRING_HOSTS[preferredHost].connectionMode !== "unavailable"
    && state.authConfig?.host_connection_modes?.[preferredHost] !== "unavailable") {
    selectPairingHost(preferredHost);
  }
  elements.pairingHostCards.find((button) => !button.disabled)?.focus();
}

const PAIRING_HOSTS = Object.freeze({
  workbuddy: { name: "WorkBuddy", code: "AP-WORKBUDDY-V1", defaultHandle: "workbuddy" },
  doubao_work: { name: "豆包工作", code: "AP-DOUBAO-WORK-V1", defaultHandle: "doubao", connectionMode: "local_bootstrap" },
  openclaw: { name: "OpenClaw", code: "AP-OPENCLAW-V1", defaultHandle: "openclaw" },
  hermes: { name: "Hermes", code: "AP-HERMES-V1", defaultHandle: "hermes" },
  codex: { name: "Codex", code: "AP-CODEX-V1", defaultHandle: "codex" },
  manus: { name: "Manus", code: "AP-MANUS-V1", defaultHandle: "manus", connectionMode: "local_bootstrap" },
  feishu_aily: {
    name: "飞书 aily 智能体",
    code: "AP-FEISHU-AILY-V1",
    defaultHandle: "aily",
    connectionMode: "unavailable",
  },
});

function agentHandleProblem(value) {
  const handle = value.trim().toLowerCase();
  if (!handle) return "";
  if (handle.length > 32) return `短名称最多 32 位；目前有 ${handle.length} 位。`;
  if (handle.startsWith("-") || handle.endsWith("-") || handle.includes("--")) {
    return "连字符不能放在开头或结尾，也不能连续使用。";
  }
  if (!/^[\p{L}\p{N}-]+$/u.test(handle)) {
    return "短名称只能使用中文、英文字母、数字和连字符“-”，不能使用空格、下划线或其他符号。";
  }
  if (RESERVED_AGENT_HANDLES.has(handle)) {
    return `“${handle}”是系统保留名称，请换一个更具体的名称。`;
  }
  return "";
}

function defaultPairingHandle(connectorType) {
  const base = PAIRING_HOSTS[connectorType]?.defaultHandle || "agent";
  const used = new Set((state.dashboard?.agents || [])
    .map((agent) => safeText(agent.handle, "").toLowerCase())
    .filter(Boolean));
  if (!used.has(base)) return base;
  for (let suffix = 2; suffix < 1000; suffix += 1) {
    const candidate = `${base}-${suffix}`;
    if (!used.has(candidate)) return candidate;
  }
  return base;
}

function setSuggestedPairingHandle(connectorType) {
  const current = elements.pairingHandle.value.trim().toLowerCase();
  if (current && current !== state.pairingSuggestedHandle) return;
  const suggestion = defaultPairingHandle(connectorType);
  state.pairingSuggestedHandle = suggestion;
  elements.pairingHandle.value = suggestion;
  updatePairingHandleHelp();
}

function updatePairingHandleHelp() {
  const handle = elements.pairingHandle.value.trim().toLowerCase();
  const problem = agentHandleProblem(handle);
  elements.pairingHandleHelp.textContent = problem
    || (handle
      ? `连接后可用“${handle}”找到这个 Agent，以后也可以修改。`
      : "系统会按 Agent 平台自动填写；也可以改为 1–32 个中文、英文字母或数字。");
  elements.pairingHandleHelp.classList.toggle("error", Boolean(problem));
}

function pairingPrompt(host) {
  const selected = PAIRING_HOSTS[host];
  if (!selected) {
    return "";
  }
  const target = state.pairingTargetAgent;
  const targetLabel = target ? safeText(target.handle, target.display_name) : "";
  const targetQuery = target?.id
    ? `?agent=${encodeURIComponent(target.id)}`
    : `?new=${encodeURIComponent(state.pairingNewAgentIntent)}`;
  const connectionMode = selected.connectionMode || state.authConfig?.host_connection_modes?.[host];
  const instructions = connectionMode === "unavailable"
    ? `当前 AgentPost 尚未发布 ${selected.name} 的安全接入服务。请保留这段接入意向，不能改用其他 Agent 的接入码、长期密钥或网页模拟登录。`
    : connectionMode === "remote_mcp_oauth"
    ? `请读取这个官方接入页，使用 ${selected.name} 内置的 Custom MCP 连接和 AgentPost 网页授权直接完成接入。不要安装 AgentPost 本机程序，也不要让我输入服务器地址、命令、密钥或其他技术参数；如果当前 ${selected.name} 不支持安全网页授权，必须明确停止，不能改用长期密钥或假装已连接。连接后回到本对话继续。`
    : host === "manus"
      ? `请先在 Manus 中创建或选择一个专用本地文件夹，再读取这个官方接入页并完成安全配对。接入程序会在该文件夹生成 AGENTS.md、xingyunyi 和校验文件，密钥仍只保存在系统钥匙串。文件生成后必须新建 Manus 任务，提交前选择这个文件夹；不要复用旧任务。先运行 ./xingyunyi status，确认身份一致且连接正常后再继续；不要改用 Custom MCP 或 Remote MCP。`
    : host === "doubao_work"
      ? `请读取这个官方接入页并完成本机安全配对。接入程序会准备好 ${selected.name} STDIO 连接器所需的唯一启动项；不要让我自行填写服务器、参数、环境变量或密钥。若 ${selected.name} 不允许自动写入连接器，我只需粘贴这一项并保存一次。确认 AgentPost 工具已在真实任务中出现后，再回到本对话继续。`
      : "请读取这个官方接入页并直接完成安装和授权。你自己识别电脑系统，不要让我输入命令、地址、密钥或其他技术参数；除一次安装确认和一次 AgentPost 网页授权外不要提问，连接后回到本对话继续。";
  return [
    target
      ? `请把当前 ${selected.name} 重新连接到我已有的 Agent“${targetLabel}”，保留原身份和历史。`
      : `请把当前 ${selected.name} 作为新的独立 Agent 连接到我的 AgentPost。`,
    `接入码：${selected.code} https://agentpost.me/connect/${host}${targetQuery}`,
    instructions,
  ].join("\n");
}

function selectPairingHost(host) {
  const selected = PAIRING_HOSTS[host];
  if (!selected) {
    return;
  }
  if (selected.connectionMode === "unavailable"
    || state.authConfig?.host_connection_modes?.[host] === "unavailable") {
    elements.pairingCopyResult.textContent = `${selected.name} 暂未开放，当前不能生成可执行的接入步骤。`;
    elements.pairingCopyResult.className = "form-status error";
    return;
  }
  state.selectedPairingHost = host;
  elements.pairingHostCards.forEach((button) => {
    const isSelected = button.dataset.connectorType === host;
    button.classList.toggle("selected", isSelected);
    button.setAttribute("aria-pressed", String(isSelected));
  });
  elements.pairingHostName.textContent = selected.name;
  elements.pairingChatPrompt.textContent = pairingPrompt(host);
  elements.pairingChatCard.hidden = false;
  elements.pairingCopyResult.textContent = "";
  elements.pairingCopyPrompt.focus();
}

function showPairingApproval({ allowBack = true } = {}) {
  elements.pairingGuide.hidden = true;
  elements.pairingApproval.hidden = false;
  elements.pairingGuideBack.hidden = !allowBack;
  elements.pairingDialogSummary.textContent = "最后一步只确认这次连接。Agent 身份会自动匹配，长期凭证由本地连接器自动领取，不会显示在 AgentPost 中。";
  (elements.pairingId.value ? elements.pairingAccessKey : elements.pairingId).focus();
}

async function copyPairingPrompt() {
  const prompt = elements.pairingChatPrompt.textContent.trim();
  if (!prompt || !state.selectedPairingHost) {
    elements.pairingCopyResult.textContent = "请先选择要连接的 Agent。";
    elements.pairingCopyResult.className = "form-status error";
    return;
  }
  const button = elements.pairingCopyPrompt;
  const originalLabel = button.textContent;
  try {
    await navigator.clipboard.writeText(prompt);
    button.textContent = "已复制";
    elements.pairingCopyResult.textContent = `已复制。现在粘贴到 ${PAIRING_HOSTS[state.selectedPairingHost].name} 的对话框并发送。`;
    elements.pairingCopyResult.className = "form-status success";
    setTimeout(() => {
      button.textContent = originalLabel;
    }, 1800);
  } catch (_error) {
    elements.pairingCopyResult.textContent = "浏览器没有允许自动复制。请选中上面那句话后手动复制。";
    elements.pairingCopyResult.className = "form-status error";
  }
}

function closePairingDialog({ clear = true } = {}) {
  elements.pairingAccessKey.value = "";
  elements.pairingResult.textContent = "";
  if (clear) {
    elements.pairingId.value = "";
    elements.pairingUserCode.value = "";
    elements.pairingCodeFields.hidden = false;
    elements.pairingTargetMode.value = "new";
    elements.pairingExistingAgent.replaceChildren();
    elements.pairingLocalId.value = "";
    elements.pairingDisplayName.value = "";
    elements.pairingCapabilities.value = "";
    elements.pairingHandle.value = "";
    state.pairingSuggestedHandle = "";
    updatePairingHandleHelp();
    elements.pairingPreview.replaceChildren();
    elements.pairingPreview.hidden = true;
    state.pairingTargetResolution = "pending";
    state.pairingCreateNewAutomatically = false;
    state.pairingRequestSignature = "";
    state.pairingIdempotencyKey = "";
    state.pairingTargetAgent = null;
    state.pairingNewAgentIntent = "";
    state.pairingConnectorType = "";
    updatePairingTargetMode();
  }
  if (elements.pairingDialog.open) {
    elements.pairingDialog.close();
  }
}

function populateExistingAgentOptions({ allowCreateNew = false } = {}) {
  elements.pairingExistingAgent.replaceChildren();
  const agents = Array.isArray(state.dashboard?.agents) ? state.dashboard.agents : [];
  const owned = agents.filter(
    (agent) => agent.access_source === "direct" && agent.role === "owner" && agent.status === "active",
  );
  owned.forEach((agent) => {
    const option = document.createElement("option");
    option.value = agent.id;
    option.textContent = agent.handle
      ? `${safeText(agent.handle)} · ${safeText(agent.display_name)}`
      : safeText(agent.display_name, agent.address);
    elements.pairingExistingAgent.append(option);
  });
  if (allowCreateNew && owned.length) {
    const option = document.createElement("option");
    option.value = "__create_new__";
    option.textContent = "＋ 这是另一个新的 AI（创建独立 Agent）";
    elements.pairingExistingAgent.append(option);
  }
  if (!owned.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "没有可迁移的自有 Agent";
    elements.pairingExistingAgent.append(option);
  }
  return owned;
}

function updatePairingTargetMode() {
  if (state.pairingTargetResolution !== "pending") {
    const ambiguous = state.pairingTargetResolution === "ambiguous";
    elements.pairingTargetModeField.hidden = true;
    elements.pairingExistingAgentField.hidden = !ambiguous;
    elements.pairingNewAgentFields.hidden = true;
    elements.pairingLocalId.required = false;
    elements.pairingExistingAgent.required = ambiguous;
    return;
  }
  const existing = elements.pairingTargetMode.value === "existing";
  elements.pairingTargetModeField.hidden = false;
  elements.pairingExistingAgentField.hidden = !existing;
  elements.pairingNewAgentFields.hidden = existing;
  elements.pairingLocalId.required = !existing;
  elements.pairingExistingAgent.required = existing;
}

function configurePairingTarget(pairing) {
  const owned = populateExistingAgentOptions();
  state.pairingConnectorType = safeText(pairing.connector_type, "");
  state.pairingCreateNewAutomatically = false;
  elements.pairingTargetSummary.hidden = false;
  const requestedAgentId = safeText(pairing.requested_existing_agent_id, "");
  const requestedAgent = requestedAgentId
    ? owned.find((agent) => String(agent.id) === requestedAgentId)
    : null;
  if (requestedAgent) {
    state.pairingTargetResolution = "automatic-existing";
    elements.pairingTargetMode.value = "existing";
    elements.pairingExistingAgent.value = requestedAgent.id;
    elements.pairingTargetSummary.textContent = `将重新连接 ${safeText(requestedAgent.handle, requestedAgent.display_name)}；原身份、权限、任务和历史保持不变。`;
    elements.pairingHandle.value = safeText(requestedAgent.handle, "");
    state.pairingSuggestedHandle = elements.pairingHandle.value;
    updatePairingHandleHelp();
    elements.pairingSubmit.disabled = false;
  } else if (requestedAgentId) {
    state.pairingTargetResolution = "invalid-target";
    elements.pairingTargetMode.value = "existing";
    elements.pairingTargetSummary.textContent = "这段接入码指定的 Agent 不属于当前账号。请关闭后，从目标 Agent 卡片重新点击“连接”。";
    elements.pairingSubmit.disabled = true;
  } else if (owned.length) {
    populateExistingAgentOptions({ allowCreateNew: true });
    const sameHost = owned.filter(
      (agent) => safeText(agent.current_connector_type, "") === state.pairingConnectorType,
    );
    const suggested = sameHost[0] || owned[0];
    state.pairingTargetResolution = "ambiguous";
    elements.pairingTargetMode.value = "existing";
    elements.pairingExistingAgent.value = suggested.id;
    elements.pairingTargetSummary.textContent = `检测到你已有 Agent。若这是重新连接或升级，请选择原 Agent（当前建议：${safeText(suggested.handle, suggested.display_name)}）；只有确实是另一个独立 AI 时才选择“创建独立 Agent”。`;
    elements.pairingHandle.value = safeText(suggested.handle, "");
    state.pairingSuggestedHandle = elements.pairingHandle.value;
    updatePairingHandleHelp();
    elements.pairingSubmit.disabled = false;
  } else {
    state.pairingTargetResolution = "automatic-new";
    state.pairingCreateNewAutomatically = true;
    elements.pairingTargetMode.value = "new";
    elements.pairingTargetSummary.textContent = `将为 ${safeText(pairing.connector_display_name, "当前 Agent")} 创建新的独立身份和可读地址，不会替换你已有的任何 Agent。`;
    setSuggestedPairingHandle(safeText(pairing.connector_type, ""));
    elements.pairingSubmit.disabled = false;
  }
  updatePairingTargetMode();
}

function renderPairingPreview(pairing) {
  elements.pairingPreview.replaceChildren();
  const heading = document.createElement("strong");
  heading.textContent = safeText(pairing.connector_display_name, pairing.connector_type);
  const details = document.createElement("p");
  details.textContent = `${safeText(pairing.connector_type)} · ${safeText(pairing.device_name, "未声明设备")} · ${safeText(pairing.client_version, "未声明版本")}`;
  const capabilities = document.createElement("p");
  const values = Array.isArray(pairing.requested_capabilities) ? pairing.requested_capabilities : [];
  capabilities.textContent = `自声明能力：${values.length ? values.join("、") : "无"}`;
  const warning = document.createElement("span");
  warning.textContent = `校验尾码 ${safeText(pairing.user_code_hint)} · ${statusLabel(pairing.status)}`;
  elements.pairingPreview.append(heading, details, capabilities, warning);
  elements.pairingPreview.hidden = false;
}

async function loadPairingPreview() {
  const pairingId = elements.pairingId.value.trim();
  if (!pairingId.startsWith("pair_")) {
    elements.pairingPreview.hidden = true;
    return;
  }
  try {
    const pairing = await requestJson(`/api/v1/orbit/pairings/${encodeURIComponent(pairingId)}`);
    renderPairingPreview(pairing);
    configurePairingTarget(pairing);
    elements.pairingResult.textContent = "请核对 Agent 上显示的完整配对码和以上设备信息。";
    elements.pairingResult.className = "form-status";
  } catch (error) {
    elements.pairingPreview.hidden = true;
    elements.pairingResult.textContent = error.message;
    elements.pairingResult.className = "form-status error";
  }
}

async function openPairingDialog(pairingId = "", userCode = "", targetAgent = null, preferredHost = "") {
  state.pairingTargetAgent = targetAgent;
  elements.pairingId.value = pairingId;
  elements.pairingUserCode.value = userCode;
  elements.pairingCodeFields.hidden = Boolean(pairingId && userCode);
  elements.pairingResult.textContent = "请核对工具和设备，确认后连接器会自动恢复原任务。";
  elements.pairingResult.className = "form-status";
  populateExistingAgentOptions();
  updatePairingTargetMode();
  elements.pairingDialog.showModal();
  if (pairingId) {
    showPairingApproval({ allowBack: false });
    await loadPairingPreview();
    return;
  }
  showPairingGuide(targetAgent, preferredHost);
}

function pairingPayload(decision) {
  if (decision === "denied") {
    return { decision: "denied" };
  }
  const handle = elements.pairingHandle.value.trim().toLowerCase() || null;
  elements.pairingHandle.value = handle || "";
  if (state.pairingCreateNewAutomatically) {
    return { decision: "approved", create_new_agent: true, handle };
  }
  if (elements.pairingTargetMode.value === "existing") {
    return {
      decision: "approved",
      existing_agent_id: elements.pairingExistingAgent.value || null,
      handle,
    };
  }
  const capabilities = [...new Set(
    elements.pairingCapabilities.value
      .split(/[,，]/)
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean),
  )];
  const localAgentId = canonicalPairingLocalId(elements.pairingLocalId.value);
  elements.pairingLocalId.value = localAgentId;
  return {
    decision: "approved",
    handle,
    local_agent_id: localAgentId,
    display_name: elements.pairingDisplayName.value.trim() || null,
    capabilities: capabilities.length ? capabilities : null,
  };
}

function managedAgentDomain() {
  return state.authConfig?.managed_agent_domain || "agents.local";
}

function canonicalPairingLocalId(value) {
  const candidate = value.trim().toLowerCase();
  const separator = candidate.lastIndexOf("@");
  if (separator > 0 && candidate.slice(separator + 1) === managedAgentDomain()) {
    return candidate.slice(0, separator);
  }
  return candidate;
}

function pairingPayloadProblem(decision, payload) {
  if (decision !== "approved") {
    return "";
  }
  const handleProblem = agentHandleProblem(payload.handle || "");
  if (handleProblem) return handleProblem;
  if (payload.create_new_agent || payload.existing_agent_id) {
    return "";
  }
  if (!payload.local_agent_id) {
    return "请为 Agent 设置一个地址。只填写 @ 前面的部分，例如 mars-codex。";
  }
  if (!LOCAL_AGENT_ID_PATTERN.test(payload.local_agent_id)) {
    return `Agent 地址只填写 @${managedAgentDomain()} 前面的部分，并使用小写字母、数字、点、下划线或连字符。`;
  }
  if ((payload.capabilities || []).length > 64 || (payload.capabilities || []).some((value) => value.length > 100)) {
    return "能力标签请用逗号分隔，最多填写 64 项，每项不超过 100 个字符。";
  }
  return "";
}

function pairingIdempotencyKey(pairingId, payload) {
  const signature = JSON.stringify({ pairingId, payload });
  if (signature !== state.pairingRequestSignature) {
    state.pairingRequestSignature = signature;
    state.pairingIdempotencyKey = `xinggui-pairing-${crypto.randomUUID()}`;
  }
  return state.pairingIdempotencyKey;
}

async function decidePairing(event, forcedDecision = null) {
  event.preventDefault();
  const decision = forcedDecision || "approved";
  const pairingId = elements.pairingId.value.trim();
  const userCode = elements.pairingUserCode.value.trim();
  const humanKey = elements.pairingAccessKey.value.trim();
  const payload = pairingPayload(decision);
  const payloadProblem = pairingPayloadProblem(decision, payload);
  if (!state.csrfToken || !pairingId.startsWith("pair_") || !userCode || !validReauthenticationCandidate(humanKey)) {
    elements.pairingResult.textContent = "请填写有效的配对信息、一次性配对码和当前密码（或旧版集成凭证）。";
    elements.pairingResult.className = "form-status error";
    return;
  }
  if (
    decision === "approved"
    && !payload.create_new_agent
    && !payload.local_agent_id
    && !payload.existing_agent_id
  ) {
    elements.pairingResult.textContent = "请选择这次连接属于哪个 Agent。";
    elements.pairingResult.className = "form-status error";
    return;
  }
  if (payloadProblem) {
    elements.pairingResult.textContent = payloadProblem;
    elements.pairingResult.className = "form-status error";
    if (agentHandleProblem(payload.handle || "")) {
      elements.pairingHandle.focus();
    } else {
      elements.pairingLocalId.focus();
    }
    return;
  }
  elements.pairingSubmit.disabled = true;
  elements.pairingDeny.disabled = true;
  elements.pairingResult.textContent = "正在验证配对码和你的身份…";
  elements.pairingResult.className = "form-status";
  try {
    let confirmation;
    try {
      const proof = reauthentication(humanKey, "", {
        intent: decision === "approved" ? "approve" : "deny",
        user_code: userCode,
      });
      confirmation = await requestJson(
        `/api/v1/orbit/pairings/${encodeURIComponent(pairingId)}/confirmation`,
        {
          method: "POST",
          headers: proof.headers,
          body: JSON.stringify(proof.payload),
        },
      );
    } finally {
      elements.pairingAccessKey.value = "";
    }
    elements.pairingResult.textContent = decision === "approved"
      ? (payload.create_new_agent
        ? "身份已确认，正在创建 Agent 并完成安全连接…"
        : payload.existing_agent_id
        ? "身份已确认，正在替换当前连接并撤销旧凭证…"
        : "身份已确认，正在创建 Agent 并完成安全连接…")
      : "身份已确认，正在拒绝本次配对…";
    await requestJson(`/api/v1/orbit/pairings/${encodeURIComponent(pairingId)}/decision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": pairingIdempotencyKey(pairingId, payload),
        "X-CSRF-Token": state.csrfToken,
        "X-Human-Confirmation": confirmation.confirmation_token,
      },
      body: JSON.stringify(payload),
    });
    const oauthRequest = new URLSearchParams(window.location.search).get("oauth_request") || "";
    closePairingDialog();
    if (oauthRequest) {
      const completion = new URL("/api/v1/orbit/oauth/authorize/complete", window.location.origin);
      completion.searchParams.set("authorization_request", oauthRequest);
      const completed = await requestJson(completion.toString(), {
        method: "POST",
        headers: { "X-CSRF-Token": state.csrfToken },
      });
      window.location.assign(completed.redirect_to);
      return;
    }
    history.replaceState(
      { module: state.activeModule, section: state.activeSection },
      "",
      currentRouteUrlWithoutWorkflowParameters(),
    );
    await loadDashboard();
    setConnection(
      decision === "approved" ? "Agent 已加入 AgentPost，等待它完成本机安全连接" : "配对已拒绝",
      "success",
    );
  } catch (error) {
    elements.pairingAccessKey.value = "";
    elements.pairingResult.textContent = error.message;
    elements.pairingResult.className = "form-status error";
  } finally {
    elements.pairingSubmit.disabled = false;
    elements.pairingDeny.disabled = false;
  }
}

function closeRevokeDialog() {
  elements.revokeAccessKey.value = "";
  elements.revokeMfa.value = "";
  elements.revokeConnectorId.value = "";
  elements.revokeResult.textContent = "";
  if (elements.revokeDialog.open) {
    elements.revokeDialog.close();
  }
}

async function revokeConnector(event) {
  event.preventDefault();
  const connectorId = elements.revokeConnectorId.value.trim();
  const humanKey = elements.revokeAccessKey.value.trim();
  const mfa = elements.revokeMfa.value.trim();
  if (!state.csrfToken || !connectorId.startsWith("con_") || !validReauthenticationCandidate(humanKey)) {
    elements.revokeResult.textContent = "请重新输入当前密码（或旧版集成凭证）。";
    elements.revokeResult.className = "form-status error";
    return;
  }
  elements.revokeSubmit.disabled = true;
  try {
    let confirmation;
    try {
      const proof = reauthentication(humanKey, mfa);
      confirmation = await requestJson(
        `/api/v1/orbit/connectors/${encodeURIComponent(connectorId)}/confirmation`,
        {
          method: "POST",
          headers: proof.headers,
          body: JSON.stringify(proof.payload),
        },
      );
    } finally {
      elements.revokeAccessKey.value = "";
      elements.revokeMfa.value = "";
    }
    await requestJson(`/api/v1/orbit/connectors/${encodeURIComponent(connectorId)}`, {
      method: "DELETE",
      headers: {
        "X-CSRF-Token": state.csrfToken,
        "X-Human-Confirmation": confirmation.confirmation_token,
      },
    });
    closeRevokeDialog();
    await loadDashboard();
    setConnection("连接已断开；Agent 身份和历史记录已保留", "success");
  } catch (error) {
    elements.revokeResult.textContent = error.message;
    elements.revokeResult.className = "form-status error";
  } finally {
    elements.revokeSubmit.disabled = false;
  }
}

function openDeleteAgentDialog(agent) {
  elements.deleteAgentId.value = safeText(agent.id, "");
  elements.deleteAgentSummary.textContent = `确定删除 ${safeText(agent.handle, agent.display_name)} 吗？这个操作只影响该 Agent，不会让其他 Agent 下线。`;
  elements.deleteAgentResult.textContent = "删除后，该 Agent 的当前连接会立即失效，历史记录仍会保留。";
  elements.deleteAgentResult.className = "form-status";
  elements.deleteAgentDialog.showModal();
  elements.deleteAgentCancel.focus();
}

function closeDeleteAgentDialog() {
  elements.deleteAgentId.value = "";
  elements.deleteAgentResult.textContent = "";
  if (elements.deleteAgentDialog.open) {
    elements.deleteAgentDialog.close();
  }
}

async function deleteAgent(event) {
  event.preventDefault();
  const agentId = elements.deleteAgentId.value.trim();
  if (!state.csrfToken || !agentId) {
    elements.deleteAgentResult.textContent = "无法确认要删除的 Agent，请关闭后重试。";
    elements.deleteAgentResult.className = "form-status error";
    return;
  }
  elements.deleteAgentSubmit.disabled = true;
  try {
    await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agentId)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ confirmation: "delete" }),
    });
    closeDeleteAgentDialog();
    await loadDashboard();
    setConnection("Agent 已删除；其他 Agent 的连接未受影响", "success");
  } catch (error) {
    elements.deleteAgentResult.textContent = error.message;
    elements.deleteAgentResult.className = "form-status error";
  } finally {
    elements.deleteAgentSubmit.disabled = false;
  }
}

async function maybeOpenRequestedPairing() {
  if (state.requestedPairingOpened) {
    return;
  }
  const parameters = new URLSearchParams(window.location.search);
  const pairingId = parameters.get("pairing") || "";
  const userCode = parameters.get("code") || "";
  if (!pairingId) {
    return;
  }
  state.requestedPairingOpened = true;
  await openPairingDialog(pairingId, userCode);
}

function renderTasks(tasks) {
  elements.taskList.replaceChildren();
  if (!tasks.length) {
    elements.taskList.append(emptyState("当前没有与你的 Agent 相关的 task 消息。"));
    return;
  }
  const fragment = document.createDocumentFragment();
  tasks.forEach((task) => {
    const item = document.createElement("article");
    item.className = `task-item ${safeText(task.work_state, "pending")}`;
    const marker = document.createElement("div");
    marker.className = "timeline-marker";

    const body = document.createElement("div");
    body.className = "task-body";
    const heading = document.createElement("div");
    heading.className = "task-heading";
    const title = document.createElement("strong");
    title.textContent = safeText(task.subject, "未命名任务");
    heading.append(title, chip(task.work_state));

    const route = document.createElement("p");
    route.className = "task-route";
    route.textContent = `${safeText(task.requester_address)} → ${safeText(task.assignee_address)}`;
    const instruction = document.createElement("p");
    instruction.className = "task-instruction";
    instruction.textContent = task.instruction === null ? "内容因审计角色而隐藏。" : safeText(task.instruction, "无任务说明");
    const states = document.createElement("div");
    states.className = "dual-state";
    const communication = document.createElement("span");
    communication.textContent = `通信：${statusLabel(task.communication_state)}`;
    const work = document.createElement("span");
    work.textContent = `工作：${statusLabel(task.work_state)}`;
    const time = document.createElement("span");
    time.textContent = dateText(task.updated_at);
    states.append(communication, work, time);
    body.append(heading, route, instruction, states);
    item.append(marker, body);
    fragment.append(item);
  });
  elements.taskList.append(fragment);
}

function closeApprovalDialog() {
  elements.approvalAccessKey.value = "";
  elements.approvalMfa.value = "";
  elements.approvalNote.value = "";
  elements.approvalResult.textContent = "";
  elements.approvalId.value = "";
  elements.approvalDecision.value = "";
  if (elements.approvalDialog.open) {
    elements.approvalDialog.close();
  }
}

function openApprovalDialog(approval, decision) {
  elements.approvalId.value = safeText(approval.approval_id, "");
  elements.approvalDecision.value = decision;
  elements.approvalDialogTitle.textContent = decision === "approved" ? "批准这项申请" : "拒绝这项申请";
  elements.approvalDialogSummary.textContent = safeText(
    approval.summary,
    "申请内容因审计角色而隐藏。",
  );
  elements.approvalSubmit.textContent = decision === "approved" ? "确认批准" : "确认拒绝";
  elements.approvalResult.textContent = "请重新输入当前密码（或旧版集成凭证）；验证后输入内容会立即清除。";
  elements.approvalDialog.showModal();
  elements.approvalAccessKey.focus();
}

function renderApprovals(approvals) {
  elements.approvalList.replaceChildren();
  if (!approvals.length) {
    elements.approvalList.append(emptyState("当前没有你可见的 Agent 审批申请。"));
    return;
  }
  const fragment = document.createDocumentFragment();
  approvals.forEach((approval) => {
    const card = document.createElement("article");
    card.className = "approval-card";
    const heading = document.createElement("div");
    heading.className = "approval-heading";
    const identity = document.createElement("div");
    const type = document.createElement("span");
    type.className = "approval-action-type";
    type.textContent = safeText(approval.action_type);
    const title = document.createElement("strong");
    title.textContent = safeText(approval.requester_address);
    identity.append(type, title);
    heading.append(identity, chip(approval.status, "approval"));

    const summary = document.createElement("p");
    summary.className = "approval-summary";
    summary.textContent = approval.content_redacted
      ? "申请内容因审计角色而隐藏。"
      : safeText(approval.summary, "无申请摘要");
    const justification = document.createElement("p");
    justification.className = "approval-justification";
    justification.textContent = approval.content_redacted
      ? "理由与参数不可见。"
      : safeText(approval.justification, "Agent 未提供额外理由。");
    const payload = document.createElement("pre");
    payload.className = "approval-payload";
    payload.textContent = approval.content_redacted
      ? "external_agent_content · redacted"
      : safeText(approval.payload, "{}");
    const metadata = document.createElement("div");
    metadata.className = "approval-meta";
    [
      `风险：${safeText(approval.risk_level)}`,
      `角色：${statusLabel(approval.access_role)}`,
      `申请：${dateText(approval.created_at)}`,
      `到期：${dateText(approval.expires_at)}`,
    ].forEach((value) => {
      const item = document.createElement("span");
      item.textContent = value;
      metadata.append(item);
    });
    card.append(heading, summary, justification, payload, metadata);

    if (approval.status === "pending" && approval.can_decide) {
      const actions = document.createElement("div");
      actions.className = "approval-actions";
      const reject = document.createElement("button");
      reject.type = "button";
      reject.className = "approval-action reject";
      reject.textContent = "拒绝";
      reject.addEventListener("click", () => openApprovalDialog(approval, "rejected"));
      const approve = document.createElement("button");
      approve.type = "button";
      approve.className = "approval-action approve";
      approve.textContent = "批准";
      approve.addEventListener("click", () => openApprovalDialog(approval, "approved"));
      actions.append(reject, approve);
      card.append(actions);
    }
    fragment.append(card);
  });
  elements.approvalList.append(fragment);
}

function agentDisplayName(agent) {
  return safeText(agent?.handle, agent?.display_name || agent?.address || "Agent");
}

function agentOwnerLabel(agent, { currentAsMe = false } = {}) {
  if (currentAsMe && agent?.owned_by_current_human) {
    return "我";
  }
  return safeText(agent?.owner_username, agent?.owner_display_name || "归属人待确认");
}

function agentConversationLabel(agent, options = {}) {
  return `${agentOwnerLabel(agent, options)} · ${agentDisplayName(agent)}`;
}

function agentTypeLabel(agent) {
  const labels = {
    codex: "Codex",
    workbuddy: "WorkBuddy",
    doubao_work: "豆包工作",
    openclaw: "OpenClaw",
    manus: "Manus",
    feishu_aily: "飞书 aily 智能体",
    hermes: "Hermes",
  };
  return labels[agent?.agent_type] || (agent?.agent_type ? safeText(agent.agent_type) : "类型未提供");
}

function agentHue(agent) {
  const value = safeText(agent?.id, agent?.address || "agent");
  let hash = 0;
  for (const character of value) {
    hash = ((hash << 5) - hash + character.codePointAt(0)) | 0;
  }
  return Math.abs(hash) % 360;
}

function agentAvatar(agent, className = "agent-mini-avatar") {
  const avatar = document.createElement("span");
  avatar.className = className;
  avatar.style.setProperty("--agent-hue", String(agentHue(agent)));
  avatar.textContent = agentDisplayName(agent).slice(0, 1).toUpperCase();
  avatar.setAttribute("aria-hidden", "true");
  return avatar;
}

function messageTypeLabel(value) {
  const labels = {
    message: "普通消息",
    task: "任务",
    response: "回复",
    request: "请求",
    result: "结果",
    notification: "通知",
    event: "系统事件",
    system: "系统事件",
    error: "异常事件",
  };
  return labels[value] || safeText(value, "消息");
}

function compactThreadContent(value, fallback = "暂无正文摘要") {
  const text = safeText(value, fallback).replace(/\s+/g, " ").trim();
  return text.length > 92 ? `${text.slice(0, 92)}…` : text;
}

function formatFileSize(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) {
    return "大小未知";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function visibleThreadSummaries() {
  return state.threads.filter((thread) => {
    if (state.threadFilter === "exception" && Number(thread.exception_count || 0) === 0) {
      return false;
    }
    return true;
  });
}

function conversationStateLabel(value) {
  const labels = {
    needs_attention: "需要关注",
    in_progress: "正在协作",
    completed: "已完成",
    waiting_for_me: "等待我回复",
    waiting_for_other: "等待对方回复",
    updated: "有新进展",
  };
  return labels[value] || "对话进行中";
}

function renderThreadParentSummary() {
  const total = visibleThreadSummaries().length;
  const unread = visibleThreadSummaries().filter(
    (thread) => thread.human_view_state === "unread",
  ).length;
  const stateLabel = state.threadBrowserExpanded ? "已展开" : "已折叠";
  const scopeLabel = state.threadFilter === "archived" ? "已归档" : stateLabel;
  elements.threadParentSummary.textContent = `${scopeLabel} · ${total} 个完整对话`;
  elements.threadUnreadCount.textContent = String(unread);
  elements.threadUnreadCount.hidden = unread === 0;
}

function renderThreadList() {
  elements.threadList.replaceChildren();
  const threads = visibleThreadSummaries();
  elements.threadCount.textContent = `${threads.length} 个对话`;
  renderThreadParentSummary();
  if (!threads.length) {
    const hasAgents = Array.isArray(state.dashboard?.agents) && state.dashboard.agents.length > 0;
    if (state.threadQuery) {
      elements.threadList.append(emptyState("没有找到你有权查看且符合搜索条件的对话。"));
    } else if (state.threadFilter === "archived") {
      elements.threadList.append(emptyState("已归档对话会集中显示在这里，恢复后会回到“我的对话”。"));
    } else if (state.threadFilter === "exception") {
      elements.threadList.append(emptyState("当前授权范围内没有异常对话。"));
    } else if (hasAgents) {
      elements.threadList.append(emptyState("AI 已连接或已授权，但目前还没有产生协作对话。"));
    } else {
      elements.threadList.append(emptyStateWithAction(
        "连接 AI 后，它们之间的协作对话会出现在这里。",
        "去 AI 中连接",
        () => activateRoute("relay", "connections", { focusContent: true }),
      ));
    }
    return;
  }
  const fragment = document.createDocumentFragment();
  threads.forEach((thread) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "thread-list-item";
    button.classList.toggle("active", String(thread.thread_id) === state.selectedThreadId);
    if (String(thread.thread_id) === state.selectedThreadId) button.setAttribute("aria-current", "true");
    button.setAttribute("aria-label", `打开对话：${safeText(thread.topic, "无主题对话")}`);
    const top = document.createElement("span");
    top.className = "thread-list-top";
    const topic = document.createElement("strong");
    topic.className = "thread-list-topic";
    topic.textContent = safeText(thread.topic, "无主题对话");
    const recency = document.createElement("span");
    recency.className = "thread-list-recency";
    const time = document.createElement("span");
    time.className = "thread-list-time";
    time.textContent = dateText(thread.latest_activity_at);
    recency.append(time);
    if (thread.human_view_state === "unread") {
      const unread = document.createElement("span");
      unread.className = "thread-unread-dot";
      unread.title = "你还没有查看这条对话的最新内容";
      unread.setAttribute("aria-label", "尚未查看");
      recency.append(unread);
    }
    top.append(topic, recency);
    const participants = document.createElement("span");
    participants.className = "thread-list-participants";
    const avatars = document.createElement("span");
    avatars.className = "thread-avatar-stack";
    [thread.latest_sender, thread.latest_recipient].filter(Boolean).forEach((agent) => avatars.append(agentAvatar(agent)));
    const names = document.createElement("span");
    names.className = "thread-participant-names";
    names.textContent = thread.latest_sender && thread.latest_recipient
      ? `${agentConversationLabel(thread.latest_sender)} → ${agentConversationLabel(thread.latest_recipient, { currentAsMe: true })}`
      : "参与者待确认";
    participants.append(avatars, names);
    const preview = document.createElement("span");
    preview.className = "thread-list-preview";
    preview.textContent = thread.latest_content_redacted ? "正文因当前权限而隐藏" : compactThreadContent(thread.latest_message_summary);
    const markers = document.createElement("span");
    markers.className = "thread-list-markers";
    const markerValues = [
      [`${thread.message_count} 条往来`, "conversation-count"],
      [conversationStateLabel(thread.conversation_state), `conversation-state ${safeText(thread.conversation_state, "updated")}`],
    ];
    if (thread.attachment_count) markerValues.push([`附件 ${thread.attachment_count}`, ""]);
    if (thread.exception_count) markerValues.push([`异常 ${thread.exception_count}`, "exception"]);
    markerValues.forEach(([label, className]) => {
      const marker = document.createElement("span");
      marker.className = `thread-marker ${className}`.trim();
      marker.textContent = label;
      markers.append(marker);
    });
    button.append(top, participants, preview, markers);
    button.addEventListener("click", () => selectThread(String(thread.thread_id)));
    fragment.append(button);
  });
  elements.threadList.append(fragment);
}

function syncThreadFilterControls() {
  elements.threadFilters.forEach((filter) => {
    const active = (filter.dataset.threadFilter || "all") === state.threadFilter;
    filter.classList.toggle("active", active);
    if (filter.getAttribute("aria-disabled") !== "true") {
      filter.setAttribute("aria-pressed", String(active));
    }
  });
}

async function returnToAllConversations() {
  state.threadFilter = "all";
  state.selectedThreadId = "";
  state.selectedThread = null;
  state.threadBrowserExpanded = true;
  syncThreadFilterControls();
  activateRoute("orbit", "communications", { updateHistory: false, focusContent: true });
  await loadThreads({ loadSelection: false });
  history.pushState({ module: "orbit", section: "communications" }, "", threadRouteUrl());
}

function renderSettingsArchiveList() {
  elements.settingsArchiveList.replaceChildren();
  if (!state.archivedThreads.length) {
    elements.settingsArchiveList.append(emptyState("目前没有已归档对话。"));
    return;
  }
  state.archivedThreads.forEach((thread) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "settings-archive-item";
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = safeText(thread.topic, "无主题对话");
    const summary = document.createElement("small");
    summary.textContent = `${Number(thread.message_count || 0)} 条往来 · ${safeText(thread.latest_message_summary, "打开查看完整内容")}`;
    copy.append(title, summary);
    const action = document.createElement("span");
    action.textContent = "打开并选择是否恢复 ›";
    button.append(copy, action);
    button.addEventListener("click", async () => {
      state.threadFilter = "archived";
      state.threadQuery = "";
      state.selectedThreadId = String(thread.thread_id);
      state.selectedThread = null;
      elements.threadSearchInput.value = "";
      syncThreadFilterControls();
      activateRoute("orbit", "communications", { updateHistory: false, focusContent: true });
      await loadThreads({ loadSelection: true });
      history.pushState(
        { module: "orbit", section: "communications", thread: state.selectedThreadId },
        "",
        threadRouteUrl(),
      );
    });
    elements.settingsArchiveList.append(button);
  });
}

function setThreadDetailEmpty(title, copy) {
  elements.threadDetail.hidden = true;
  elements.threadDetailEmpty.hidden = false;
  const heading = elements.threadDetailEmpty.querySelector("h2");
  const paragraph = elements.threadDetailEmpty.querySelector("p");
  if (heading) heading.textContent = title;
  if (paragraph) paragraph.textContent = copy;
}

function openThreadAgent(agent) {
  const accessible = (state.dashboard?.agents || []).some(
    (candidate) => String(candidate.id) === String(agent.id),
  );
  if (!accessible) {
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set("module", "relay");
  url.searchParams.set("view", "agents");
  url.searchParams.set("agent", String(agent.id));
  if (state.selectedThreadId) {
    url.searchParams.set("returnThread", state.selectedThreadId);
  }
  history.pushState({ module: "relay", section: "agents" }, "", `${url.pathname}${url.search}`);
  activateRoute("relay", "agents", { updateHistory: false, focusContent: true });
  selectAgent(String(agent.id), { updateHistory: false });
}

function participantChip(agent) {
  const accessible = (state.dashboard?.agents || []).some(
    (candidate) => String(candidate.id) === String(agent.id),
  );
  const item = document.createElement(accessible ? "button" : "span");
  item.className = "thread-participant-chip";
  if (accessible) {
    item.type = "button";
    item.title = "在 AI 中查看这个 Agent";
    item.addEventListener("click", () => openThreadAgent(agent));
  } else {
    item.title = "你可以在本对话中识别该 Agent，但没有它的管理入口";
  }
  const label = document.createElement("span");
  label.textContent = `${agentOwnerLabel(agent)} · ${agentDisplayName(agent)} · ${agentTypeLabel(agent)}`;
  item.append(agentAvatar(agent), label);
  return item;
}

function readableStructuredValue(value) {
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }
  if (["string", "number", "boolean"].includes(typeof value)) {
    return String(value);
  }
  if (Array.isArray(value) && value.every((item) => ["string", "number", "boolean"].includes(typeof item))) {
    return value.map(String).join("、");
  }
  return "包含更多结构化数据，可在下方展开查看";
}

function appendStructuredHumanSummary(message, body) {
  const summary = document.createElement("section");
  summary.className = "thread-structured-summary";
  const heading = document.createElement("strong");
  heading.textContent = "Agent 提供的结构化信息";
  summary.append(heading);
  const content = message.content_body;
  if (!content || typeof content !== "object" || Array.isArray(content)) {
    const note = document.createElement("p");
    note.textContent = Array.isArray(content)
      ? `这条消息包含 ${content.length} 项数据，可展开查看完整内容。`
      : readableStructuredValue(content);
    summary.append(note);
    body.append(summary);
    return;
  }

  const fieldLabels = {
    title: "标题",
    summary: "摘要",
    conclusion: "结论",
    message: "说明",
    instruction: "任务",
    result: "结果",
    status: "状态",
    next_step: "下一步",
    next_steps: "下一步",
  };
  const fields = Object.keys(fieldLabels)
    .filter((key) => Object.hasOwn(content, key))
    .slice(0, 6);
  if (!fields.length) {
    const note = document.createElement("p");
    note.textContent = `这条消息包含 ${Object.keys(content).length} 个结构化数据项，可展开查看完整内容。`;
    summary.append(note);
  } else {
    const grid = document.createElement("dl");
    grid.className = "thread-structured-grid";
    fields.forEach((key) => {
      const term = document.createElement("dt");
      term.textContent = fieldLabels[key];
      const detail = document.createElement("dd");
      detail.textContent = key === "status"
        ? statusLabel(content[key])
        : readableStructuredValue(content[key]);
      grid.append(term, detail);
    });
    summary.append(grid);
  }
  body.append(summary);
}

function appendAgentData(message, body) {
  const details = document.createElement("details");
  details.className = "thread-agent-data";
  const summary = document.createElement("summary");
  summary.textContent = message.content_format === "json"
    ? "查看 Agent 数据与技术信息（JSON）"
    : "查看 Agent 技术信息";
  summary.tabIndex = 0;
  summary.addEventListener("keydown", (event) => {
    if (!["Enter", " "].includes(event.key)) {
      return;
    }
    event.preventDefault();
    details.open = !details.open;
  });
  const grid = document.createElement("dl");
  grid.className = "thread-agent-data-grid";
  [
    ["消息格式", safeText(message.content_format, "text")],
    ["消息类型", safeText(message.message_type, "message")],
    ["消息编号", safeText(message.message_id)],
    ["要求确认收到", message.requires_ack ? "是" : "否"],
  ].forEach(([label, value]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    grid.append(term, detail);
  });
  details.append(summary, grid);
  if (message.content_format === "json" && !message.content_redacted) {
    const rawLabel = document.createElement("strong");
    rawLabel.className = "thread-agent-data-label";
    rawLabel.textContent = "原始 JSON";
    const raw = document.createElement("pre");
    raw.className = "thread-agent-data-json";
    raw.textContent = safeText(message.content_body, "null");
    details.append(rawLabel, raw);
  }
  const note = document.createElement("p");
  note.className = "thread-agent-data-note";
  note.textContent = "这些信息用于 Agent 协作和问题排查，不代表任务已经完成。";
  details.append(note);
  body.append(details);
}

function renderThreadMessageContent(message, body) {
  if (message.content_redacted) {
    const content = document.createElement("p");
    content.className = "thread-redacted-content";
    content.textContent = "正文因当前审计角色而隐藏。";
    body.append(content);
    appendAgentData(message, body);
    return;
  }
  if (message.content_format === "json") {
    appendStructuredHumanSummary(message, body);
  } else {
    const heading = document.createElement("p");
    heading.className = "thread-content-format";
    heading.textContent = message.content_format === "markdown"
      ? "消息内容 · 已按安全文本显示"
      : "消息内容";
    const content = document.createElement("pre");
    const contentFormat = message.content_format === "markdown" ? "markdown" : "text";
    content.className = `thread-message-content thread-message-content-${contentFormat}`;
    content.textContent = safeText(message.content_body, "无正文");
    body.append(heading, content);
  }
  appendAgentData(message, body);
}

function appendThreadTaskCard(message, body) {
  if (message.message_type !== "task" && message.message_type !== "result") {
    return;
  }
  const card = document.createElement("section");
  card.className = "thread-task-card";
  const heading = document.createElement("strong");
  heading.textContent = message.message_type === "result" ? "任务结果" : "任务信息";
  const grid = document.createElement("div");
  grid.className = "thread-task-grid";
  const fields = message.message_type === "result"
    ? [["结果摘要", message.result_summary || "结果正文见下方"]]
    : [
      ["指令", message.task_instruction || (message.content_redacted ? "已隐藏" : "未提供")],
      ["期望输出", message.task_expected_output || "未提供"],
      ["优先级", statusLabel(message.priority)],
      ["需要确认收到", message.requires_ack ? "是" : "否"],
      ["截止时间", message.task_deadline ? dateText(message.task_deadline) : "未设置"],
    ];
  fields.forEach(([label, value]) => {
    const field = document.createElement("span");
    field.className = "thread-task-field";
    const name = document.createElement("span");
    name.textContent = label;
    const detail = document.createElement("strong");
    detail.textContent = safeText(value);
    field.append(name, detail);
    grid.append(field);
  });
  card.append(heading, grid);
  body.append(card);
}

function appendThreadAttachments(message, body) {
  if (!Array.isArray(message.attachments) || !message.attachments.length) {
    return;
  }
  const list = document.createElement("div");
  list.className = "thread-attachment-list";
  message.attachments.forEach((attachment) => {
    const card = document.createElement("article");
    card.className = "thread-attachment-card";
    const name = document.createElement("strong");
    name.textContent = safeText(attachment.filename, "未命名附件");
    const info = document.createElement("span");
    info.textContent = `${taskFileTypeLabel(attachment.content_type, attachment.filename)} · ${formatFileSize(attachment.size)}`;
    const actions = document.createElement("div");
    actions.className = "thread-attachment-actions";
    const normalizedType = attachmentPreviewType(attachment.content_type, attachment.filename);
    const attachmentId = encodeURIComponent(String(attachment.id));
    const downloadUrl = `/api/v1/orbit/attachments/${attachmentId}`;
    const previewUrl = `${downloadUrl}/preview`;
    const readableTypes = new Set([
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/json",
      "application/markdown",
      "text/markdown",
      "text/plain",
      "text/x-markdown",
    ]);

    if (normalizedType === "application/pdf") {
      const open = document.createElement("a");
      open.className = "thread-attachment-action";
      open.href = previewUrl;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      open.textContent = "打开 PDF";
      open.classList.add("is-primary");
      actions.append(open);
    } else if (normalizedType === "text/html" || normalizedType === "application/zip" || readableTypes.has(normalizedType)) {
      const preview = document.createElement("button");
      preview.type = "button";
      preview.className = "thread-attachment-action is-primary";
      preview.textContent = normalizedType === "application/zip" ? "查看目录"
        : normalizedType === "text/html" ? "预览网页" : "查看内容";
      preview.addEventListener("click", () => openAttachmentPreview(attachment));
      actions.append(preview);
    }

    const download = document.createElement("a");
    download.className = "thread-attachment-action is-secondary";
    download.href = downloadUrl;
    download.download = safeText(attachment.filename, "attachment");
    download.textContent = "下载";
    const downloadStatus = document.createElement("small");
    downloadStatus.setAttribute("role", "status");
    download.addEventListener("click", async (event) => {
      event.preventDefault();
      if (download.getAttribute("aria-disabled") === "true") return;
      download.setAttribute("aria-disabled", "true");
      downloadStatus.textContent = "正在获取文件…";
      try {
        const response = await fetch(downloadUrl, { credentials: "same-origin" });
        if (!response.ok) throw new Error(`下载失败（${response.status}）`);
        const blob = await response.blob();
        if (Number.isFinite(attachment.size) && blob.size !== attachment.size) throw new Error("文件大小校验失败");
        if (attachment.sha256 && crypto.subtle) {
          const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
          const hex = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
          if (hex !== String(attachment.sha256).toLowerCase()) throw new Error("文件完整性校验失败");
        }
        const objectUrl = URL.createObjectURL(blob);
        const save = document.createElement("a");
        save.href = objectUrl;
        save.download = download.download;
        document.body.append(save);
        save.click();
        save.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
        downloadStatus.textContent = "已交给浏览器保存，请在下载列表确认";
      } catch (error) {
        downloadStatus.textContent = error.message || "下载失败，请重试";
      } finally {
        download.removeAttribute("aria-disabled");
      }
    });
    actions.append(download, downloadStatus);
    card.append(name, info, actions);
    list.append(card);
  });
  body.append(list);
}

function closeAttachmentPreview() {
  elements.attachmentPreviewFrame.removeAttribute("src");
  elements.attachmentPreviewDownload.removeAttribute("href");
  elements.attachmentPreviewMeta.textContent = "";
  if (elements.attachmentPreviewDialog.open) {
    elements.attachmentPreviewDialog.close();
  }
}

function openAttachmentPreview(attachment) {
  const attachmentId = encodeURIComponent(String(attachment.id));
  const downloadUrl = `/api/v1/orbit/attachments/${attachmentId}`;
  elements.attachmentPreviewTitle.textContent = safeText(attachment.filename, "预览附件");
  elements.attachmentPreviewMeta.textContent = `${taskFileTypeLabel(attachment.content_type, attachment.filename)} · ${formatFileSize(attachment.size)}`;
  elements.attachmentPreviewDownload.href = downloadUrl;
  elements.attachmentPreviewDownload.download = safeText(attachment.filename, "attachment");
  elements.attachmentPreviewFrame.src = `${downloadUrl}/preview`;
  elements.attachmentPreviewDialog.showModal();
  elements.attachmentPreviewDone.focus();
}

function renderTimelineEvent(message) {
  const event = document.createElement("article");
  event.className = "timeline-event";
  event.id = `message-${message.message_id}`;
  event.tabIndex = -1;
  const heading = document.createElement("strong");
  heading.textContent = `${messageTypeLabel(message.message_type)} · ${safeText(message.subject, "无主题事件")}`;
  const route = document.createElement("span");
  route.textContent = `发送自：${agentConversationLabel(message.sender)}；发送给：${agentConversationLabel(message.recipient, { currentAsMe: true })} · ${dateText(message.created_at)}`;
  const content = document.createElement("span");
  content.textContent = message.content_redacted
    ? "事件内容因当前审计角色而隐藏。"
    : compactThreadContent(message.content_body, "没有附加说明");
  event.append(heading, route, content);
  return event;
}

function renderTimelineMessage(message, messagesById, repliedMessageIds) {
  if (["event", "system", "error"].includes(message.message_type)) {
    return renderTimelineEvent(message);
  }
  const card = document.createElement("article");
  card.className = "message-card thread-message";
  card.id = `message-${message.message_id}`;
  card.tabIndex = -1;
  card.style.setProperty("--agent-hue", String(agentHue(message.sender)));
  const fromCurrentHuman = Boolean(message.sender?.owned_by_current_human);
  card.classList.toggle("from-current-human", fromCurrentHuman);
  const body = document.createElement("div");
  body.className = "thread-message-body";
  const identity = document.createElement("div");
  identity.className = "thread-message-identity";
  const sender = document.createElement("strong");
  sender.textContent = `发送自：${agentConversationLabel(message.sender)}`;
  const type = document.createElement("span");
  type.className = "thread-agent-type";
  type.textContent = `${agentTypeLabel(message.sender)} · ${messageTypeLabel(message.message_type)}`;
  const time = document.createElement("span");
  time.className = "thread-message-time";
  time.textContent = dateText(message.created_at);
  identity.append(sender, type, time);
  const route = document.createElement("div");
  route.className = "thread-message-route";
  route.textContent = `发送给：${agentConversationLabel(message.recipient, { currentAsMe: true })} · ${agentTypeLabel(message.recipient)}`;
  const subject = document.createElement("strong");
  subject.className = "thread-message-subject";
  subject.textContent = safeText(message.subject, "无主题消息");
  body.append(identity, route, subject);

  const states = document.createElement("div");
  states.className = "thread-message-states";
  const communication = document.createElement("span");
  communication.className = "thread-state-group";
  const communicationChip = chip(message.communication_state);
  communication.append(
    document.createTextNode("送达情况"),
    communicationChip,
  );
  states.append(communication);
  if (repliedMessageIds.has(message.message_id)) {
    const replied = document.createElement("span");
    replied.className = "thread-state-group";
    replied.append(document.createTextNode("回复情况"), chip("replied"));
    states.append(replied);
  }
  if (message.work_state) {
    const work = document.createElement("span");
    work.className = "thread-state-group";
    work.append(document.createTextNode("任务进度"), chip(message.work_state));
    states.append(work);
  }
  body.append(states);

  if (message.reply_to) {
    const parent = messagesById.get(message.reply_to);
    const reference = document.createElement("button");
    reference.type = "button";
    reference.className = "thread-reply-reference";
    reference.textContent = parent
      ? `回复 ${agentDisplayName(parent.sender)}：${safeText(parent.subject, "无主题消息")}`
      : "被回复的消息已不在当前可见范围";
    reference.disabled = !parent;
    if (parent) {
      reference.addEventListener("click", () => {
        const target = document.querySelector(`#message-${CSS.escape(String(parent.message_id))}`);
        target?.scrollIntoView({ behavior: "smooth", block: "center" });
        target?.focus({ preventScroll: true });
        target?.classList.add("jump-highlight");
        window.setTimeout(() => target?.classList.remove("jump-highlight"), 1400);
      });
    }
    body.append(reference);
  }
  appendThreadTaskCard(message, body);
  renderThreadMessageContent(message, body);
  appendThreadAttachments(message, body);

  const footer = document.createElement("div");
  footer.className = "message-footer";
  const trust = document.createElement("span");
  trust.textContent = message.security_label === "external_agent_content"
    ? "由 Agent 提供 · 已按安全方式展示"
    : safeText(message.security_label);
  footer.append(trust);
  body.append(footer);
  if (fromCurrentHuman) {
    card.append(body, agentAvatar(message.sender, "agent-timeline-avatar"));
  } else {
    card.append(agentAvatar(message.sender, "agent-timeline-avatar"), body);
  }
  return card;
}

function renderThreadDetail(thread) {
  state.selectedThread = thread;
  elements.threadDetailEmpty.hidden = true;
  elements.threadDetail.hidden = false;
  elements.threadDetailTopic.textContent = safeText(thread.topic, "无主题对话");
  elements.threadDetailParticipants.replaceChildren();
  elements.messageList.replaceChildren();
  const chronologicalMessages = Array.isArray(thread.messages) ? thread.messages : [];
  const messages = [...chronologicalMessages].sort((left, right) => {
    const timeDifference = new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    return timeDifference || String(right.message_id).localeCompare(String(left.message_id));
  });
  elements.threadDetailCount.textContent = `完整对话 · ${messages.length} 条往来`;
  const firstMessage = chronologicalMessages[0];
  elements.threadDetailRoute.textContent = firstMessage
    ? `发送自：${agentConversationLabel(firstMessage.sender)}　　给：${agentConversationLabel(firstMessage.recipient, { currentAsMe: true })}`
    : "发送自：—　　给：—";
  const failed = messages.some((message) => message.work_state === "failed" || message.message_type === "error");
  const completed = messages.some((message) => message.work_state === "completed");
  const pending = messages.some((message) => message.work_state === "pending");
  const detailState = failed ? "needs_attention" : completed ? "completed" : pending ? "in_progress" : "updated";
  elements.threadDetailState.className = `conversation-state-pill ${detailState}`;
  elements.threadDetailState.textContent = failed
    ? "需要关注"
    : completed
    ? "协作已完成"
    : pending
    ? "正在协作"
    : "对话进行中";
  const archived = Boolean(thread.archived_at) || state.threadFilter === "archived";
  elements.threadArchive.textContent = archived ? "恢复到我的对话" : "从我的对话删除";
  const messagesById = new Map(messages.map((message) => [message.message_id, message]));
  const repliedMessageIds = new Set(messages.map((message) => message.reply_to).filter(Boolean));
  let lastDate = "";
  messages.forEach((message) => {
    const parsed = new Date(message.created_at);
    const dateKey = Number.isNaN(parsed.getTime()) ? safeText(message.created_at) : parsed.toDateString();
    if (dateKey !== lastDate) {
      const separator = document.createElement("div");
      separator.className = "thread-date-separator";
      separator.textContent = Number.isNaN(parsed.getTime())
        ? safeText(message.created_at)
        : new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(parsed);
      elements.messageList.append(separator);
      lastDate = dateKey;
    }
    elements.messageList.append(renderTimelineMessage(message, messagesById, repliedMessageIds));
  });
  document.title = `AgentPost · ${safeText(thread.topic, "对话")}`;
}

async function markThreadViewed(threadId) {
  if (!state.csrfToken) {
    return;
  }
  const viewed = await requestJson(
    `/api/v1/orbit/threads/${encodeURIComponent(threadId)}/viewed`,
    { method: "POST", headers: { "X-CSRF-Token": state.csrfToken } },
  );
  const summary = state.threads.find((thread) => String(thread.thread_id) === String(threadId));
  if (summary) {
    summary.human_view_state = "viewed";
    summary.human_viewed_at = viewed?.viewed_at || new Date().toISOString();
  }
  if (state.selectedThread) {
    state.selectedThread.human_view_state = "viewed";
    state.selectedThread.human_viewed_at = viewed?.viewed_at || new Date().toISOString();
  }
  renderThreadList();
}

async function loadThreadDetail(threadId) {
  setThreadDetailEmpty("正在读取对话", "只会显示你有权查看的内容，不会改变 Agent 的已读或处理状态。");
  try {
    const thread = await requestJson(`/api/v1/orbit/threads/${encodeURIComponent(threadId)}`);
    if (state.selectedThreadId !== String(threadId)) {
      return;
    }
    renderThreadDetail(thread);
    try {
      await markThreadViewed(threadId);
    } catch (_error) {
      // Keep the unread indicator when the separate Human-view update did not persist.
    }
  } catch (error) {
    if (state.selectedThreadId !== String(threadId)) {
      return;
    }
    state.selectedThread = null;
    setThreadDetailEmpty(
      "无法打开这条对话",
      error.status === 404
        ? "对话已不存在，或已从你的当前授权范围移除。"
        : "对话读取失败，请稍后刷新重试。",
    );
  }
}

async function selectThread(threadId, { updateHistory = true } = {}) {
  state.selectedThreadId = String(threadId);
  state.selectedThread = null;
  updateThreadWorkspaceMode();
  renderThreadList();
  if (updateHistory) {
    history.pushState({ module: "orbit", section: "communications", thread: threadId }, "", threadRouteUrl());
  }
  await loadThreadDetail(threadId);
  if (isMobileWorkspace()) {
    elements.threadMobileBack.scrollIntoView({ block: "start" });
    elements.threadMobileBack.focus({ preventScroll: true });
  } else {
    elements.threadDetailTopic.focus?.({ preventScroll: true });
  }
}

function clearThreadSelection({ updateHistory = true } = {}) {
  state.selectedThreadId = "";
  state.selectedThread = null;
  updateThreadWorkspaceMode();
  renderThreadList();
  setThreadDetailEmpty("选择一条协作对话", "选择一个对话后，这个话题下的全部往来会按时间显示在这里。");
  if (updateHistory) {
    history.pushState({ module: "orbit", section: "communications" }, "", threadRouteUrl());
  }
  resetMobileLayerScroll();
}

function threadListEndpoint() {
  const parameters = new URLSearchParams({ limit: "200" });
  if (state.threadQuery) {
    parameters.set("query", state.threadQuery);
  }
  if (state.threadFilter === "archived") {
    parameters.set("archived", "true");
  }
  return `/api/v1/orbit/threads?${parameters.toString()}`;
}

function openThreadArchiveDialog(thread) {
  elements.threadArchiveId.value = String(thread.thread_id);
  elements.threadArchiveSummary.textContent = `“${safeText(thread.topic, "无主题对话")}”将从你和你名下 Agent 的 AgentPost 视图中隐藏。服务器消息不会删除。`;
  elements.threadArchiveResult.textContent = "";
  elements.threadArchiveDialog.showModal();
}

function closeThreadArchiveDialog() {
  elements.threadArchiveDialog.close();
  elements.threadArchiveForm.reset();
  elements.threadArchiveResult.textContent = "";
}

async function archiveThread(threadId) {
  await requestJson(`/api/v1/orbit/threads/${encodeURIComponent(threadId)}/archive`, {
    method: "PUT",
    headers: { "X-CSRF-Token": state.csrfToken },
  });
  if (state.selectedThreadId === String(threadId)) {
    clearThreadSelection({ updateHistory: true });
  }
  await loadThreads({ loadSelection: false });
  await loadArchivedThreadsForSettings();
}

async function restoreThread(threadId) {
  await requestJson(`/api/v1/orbit/threads/${encodeURIComponent(threadId)}/archive`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": state.csrfToken },
  });
  if (state.selectedThreadId === String(threadId)) {
    clearThreadSelection({ updateHistory: true });
  }
  await loadThreads({ loadSelection: false });
  await loadArchivedThreadsForSettings();
}

async function loadArchivedThreadsForSettings() {
  const threads = await requestJson("/api/v1/orbit/threads?limit=200&archived=true");
  state.archivedThreads = Array.isArray(threads) ? threads : [];
  renderSettingsArchiveList();
}

async function loadThreads({ loadSelection = true } = {}) {
  const threads = await requestJson(threadListEndpoint());
  state.threads = Array.isArray(threads) ? threads : [];
  renderThreadList();
  if (loadSelection && state.selectedThreadId) {
    await loadThreadDetail(state.selectedThreadId);
  } else if (!state.selectedThreadId) {
    setThreadDetailEmpty("选择一条协作对话", "选择一个对话后，这个话题下的全部往来会按时间显示在这里。");
  }
}

function renderSecurity(security) {
  const password = security.password_configured ? "密码已设置" : "需先找回账户设置密码";
  const mfa = security.mfa_enabled ? "双重验证已开启" : "双重验证未开启";
  const keys = `${safeText(security.active_human_keys, "0")} 个旧版集成凭证`;
  elements.securityStatus.textContent = `${password} · ${mfa} · ${keys}`;
  elements.openMfa.disabled = !security.password_configured;
  elements.openKeyRotation.disabled = !security.password_configured;
}

function renderDashboard(dashboard) {
  state.dashboard = dashboard;
  const user = dashboard.user || {};
  const agents = Array.isArray(dashboard.agents) ? dashboard.agents : [];
  const tasks = Array.isArray(dashboard.tasks) ? dashboard.tasks : [];
  const approvals = Array.isArray(dashboard.approvals) ? dashboard.approvals : [];
  elements.humanName.textContent = safeText(user.display_name, "AgentPost 用户");
  elements.humanEmail.textContent = safeText(user.email);
  elements.humanAvatar.textContent = safeText(user.display_name, "星").slice(0, 1);
  elements.topHumanName.textContent = safeText(user.display_name, "AgentPost 用户");
  elements.topHumanAvatar.textContent = "我";
  elements.profileName.textContent = safeText(user.display_name, "未设置");
  if (document.activeElement !== elements.profileUsernameInput) {
    elements.profileUsernameInput.value = safeText(user.username, "");
  }
  elements.profileEmail.textContent = safeText(user.email);
  elements.profileTimezone.textContent = safeText(
    Intl.DateTimeFormat().resolvedOptions().timeZone,
    "此设备未提供",
  );
  const pendingApprovals = Number(dashboard.metrics?.pending_approval_count || 0);
  elements.approvalMobileCount.textContent = String(pendingApprovals);
  const pendingTasks = Number(dashboard.metrics?.pending_task_count || 0);
  elements.taskMobileCount.textContent = String(pendingTasks);
  renderAgents(agents);
  renderTasks(tasks);
  renderApprovals(approvals);
}

async function updateProfileUsername(event) {
  event.preventDefault();
  const username = elements.profileUsernameInput.value.trim().toLowerCase();
  elements.profileUsernameInput.value = username;
  if (username === state.dashboard?.user?.username) {
    elements.profileUsernameResult.textContent = "用户名没有变化。";
    elements.profileUsernameResult.className = "form-status";
    return;
  }
  elements.profileUsernameSave.disabled = true;
  elements.profileUsernameResult.textContent = "正在保存…";
  elements.profileUsernameResult.className = "form-status";
  try {
    const user = await requestJson("/api/v1/orbit/me/username", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ username }),
    });
    state.dashboard = { ...state.dashboard, user };
    renderDashboard(state.dashboard);
    elements.profileUsernameResult.textContent = `用户名已修改为 ${user.username}。`;
    elements.profileUsernameResult.className = "form-status success";
  } catch (error) {
    elements.profileUsernameResult.textContent = error.message;
    elements.profileUsernameResult.className = "form-status error";
  } finally {
    elements.profileUsernameSave.disabled = false;
  }
}

async function loadDashboard() {
  elements.refresh.disabled = true;
  setConnection("正在同步数据", "loading", "同步中");
  try {
    const [dashboard, connectors, security, threads, archivedThreads, contactSummary] = await Promise.all([
      requestJson("/api/v1/orbit/dashboard"),
      requestJson("/api/v1/orbit/connectors"),
      requestJson("/api/v1/orbit/security"),
      requestJson(threadListEndpoint()),
      requestJson("/api/v1/orbit/threads?limit=200&archived=true"),
      requestJson("/api/v1/contacts/summary").catch(() => null),
    ]);
    state.connectors = Array.isArray(connectors.items) ? connectors.items : [];
    state.threads = Array.isArray(threads) ? threads : [];
    state.archivedThreads = Array.isArray(archivedThreads) ? archivedThreads : [];
    document.querySelectorAll("[data-first-contact]").forEach((link) => {
      link.textContent = contactSummary?.pending_count > 0
        ? `首次联系（${contactSummary.pending_count} 待处理）` : "首次联系";
    });
    renderDashboard(dashboard);
    renderConnectors(state.connectors);
    renderSecurity(security);
    renderThreadList();
    renderSettingsArchiveList();
    if (state.selectedThreadId) {
      await loadThreadDetail(state.selectedThreadId);
    } else {
      setThreadDetailEmpty("选择一条协作对话", "选择一个对话后，这个话题下的全部往来会在这里显示，最新内容排在最上面。");
    }
    elements.welcomeView.hidden = true;
    elements.workspaceView.hidden = false;
    await Promise.all([loadProjects(), loadFriends()]);
    const readyAgentCount = (dashboard.agents || []).filter(
      (agent) => agent.work_availability === "ready",
    ).length;
    const workingAgentCount = (dashboard.agents || []).filter(
      (agent) => agent.work_availability === "working",
    ).length;
    setConnection(
      `我的 AI：${readyAgentCount} 个可接任务 · ${workingAgentCount} 个执行中`,
      readyAgentCount + workingAgentCount > 0 ? "success" : "",
      `我的 AI：${readyAgentCount} 可接 · ${workingAgentCount} 执行`,
    );
    await maybeOpenRequestedPairing();
  } catch (error) {
    setConnection("数据同步失败", "error", "同步失败");
    throw error;
  } finally {
    elements.refresh.disabled = false;
  }
}

async function loadAuthConfig() {
  try {
    state.authConfig = await requestJson("/api/v1/auth/config");
  } catch (_error) {
    state.authConfig = {
      self_service_enabled: false,
      open_registration_enabled: false,
      codex_setup_platforms: [],
      connector_release: FALLBACK_CONNECTOR_RELEASE,
      managed_agent_domain: "agents.local",
    };
  }
  elements.pairingAddressDomain.textContent = `@${managedAgentDomain()}`;
  const selfService = Boolean(state.authConfig.self_service_enabled);
  elements.loginForm.hidden = !selfService;
  elements.openRecovery.hidden = !selfService;
  elements.openRegister.hidden = !Boolean(state.authConfig.open_registration_enabled);
  if (!selfService) {
    setFormStatus("当前环境尚未开通邮箱登录，请联系管理员。", "error");
  }
}

function resumeContactAfterLogin() {
  if (new URLSearchParams(location.search).get("return") !== "contact") return false;
  location.assign("/contact");
  return true;
}

async function loginHuman(event) {
  event.preventDefault();
  const submit = elements.loginForm.querySelector("button[type='submit']");
  const email = elements.loginEmail.value.trim();
  const password = elements.loginPassword.value;
  const proof = mfaProof(elements.loginMfa.value);
  submit.disabled = true;
  setFormStatus("正在验证邮箱、密码和双重验证码…");
  try {
    const browserSession = await requestJson("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, ...proof, remember_me: document.querySelector("#login-remember").checked }),
    });
    state.csrfToken = browserSession.csrf_token;
    elements.loginPassword.value = "";
    elements.loginMfa.value = "";
    if (resumeContactAfterLogin()) return;
    await loadDashboard();
    setFormStatus("身份验证成功，敏感输入已从页面清除。", "success");
  } catch (error) {
    setFormStatus(error.message, "error");
  } finally {
    elements.loginPassword.value = "";
    elements.loginMfa.value = "";
    submit.disabled = false;
  }
}

function closeRegisterDialog() {
  elements.registerCode.value = "";
  elements.registerUsername.value = "";
  elements.registerPassword.value = "";
  elements.registerResult.textContent = "";
  state.registerChallengeId = "";
  if (elements.registerDialog.open) {
    elements.registerDialog.close();
  }
}

function closeRecoveryDialog() {
  elements.recoveryCode.value = "";
  elements.recoveryPassword.value = "";
  elements.recoveryMfa.value = "";
  elements.recoveryResult.textContent = "";
  state.recoveryChallengeId = "";
  if (elements.recoveryDialog.open) {
    elements.recoveryDialog.close();
  }
}

async function sendEmailChallenge(purpose) {
  const isRegister = purpose === "register";
  const emailInput = isRegister ? elements.registerEmail : elements.recoveryEmail;
  const codeInput = isRegister ? elements.registerCode : elements.recoveryCode;
  const result = isRegister ? elements.registerResult : elements.recoveryResult;
  const button = isRegister ? elements.registerSendCode : elements.recoverySendCode;
  button.disabled = true;
  result.textContent = "正在发送邮箱验证码…";
  result.className = "form-status";
  try {
    const challenge = await requestJson("/api/v1/auth/email/challenges", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: emailInput.value.trim(), purpose }),
    });
    if (isRegister) {
      state.registerChallengeId = challenge.challenge_id;
    } else {
      state.recoveryChallengeId = challenge.challenge_id;
    }
    if (challenge.test_verification_code) {
      codeInput.value = challenge.test_verification_code;
      result.textContent = "验证码已经填入，请继续完成操作。";
    } else {
      result.textContent = "验证码已发送，请检查邮箱。";
    }
    result.className = "form-status success";
    codeInput.focus();
  } catch (error) {
    result.textContent = error.message;
    result.className = "form-status error";
  } finally {
    button.disabled = false;
  }
}

async function registerHuman(event) {
  event.preventDefault();
  if (!state.registerChallengeId) {
    elements.registerResult.textContent = "请先获取邮箱验证码。";
    elements.registerResult.className = "form-status error";
    return;
  }
  const submit = elements.registerForm.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const browserSession = await requestJson("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challenge_id: state.registerChallengeId,
        code: elements.registerCode.value.trim(),
        username: elements.registerUsername.value.trim().toLowerCase(),
        display_name: elements.registerName.value.trim(),
        password: elements.registerPassword.value,
      }),
    });
    state.csrfToken = browserSession.csrf_token;
    closeRegisterDialog();
    if (resumeContactAfterLogin()) return;
    await loadDashboard();
    setFormStatus("账户已创建。建议现在开启双重验证。", "success");
  } catch (error) {
    elements.registerResult.textContent = error.message;
    elements.registerResult.className = "form-status error";
  } finally {
    elements.registerCode.value = "";
    elements.registerPassword.value = "";
    submit.disabled = false;
  }
}

async function recoverHuman(event) {
  event.preventDefault();
  if (!state.recoveryChallengeId) {
    elements.recoveryResult.textContent = "请先获取邮箱验证码。";
    elements.recoveryResult.className = "form-status error";
    return;
  }
  const submit = elements.recoveryForm.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const browserSession = await requestJson("/api/v1/auth/recover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challenge_id: state.recoveryChallengeId,
        code: elements.recoveryCode.value.trim(),
        new_password: elements.recoveryPassword.value,
        ...mfaProof(elements.recoveryMfa.value),
      }),
    });
    state.csrfToken = browserSession.csrf_token;
    closeRecoveryDialog();
    await loadDashboard();
    setFormStatus("密码已重设，其他浏览器会话和旧版集成凭证已失效。", "success");
  } catch (error) {
    elements.recoveryResult.textContent = error.message;
    elements.recoveryResult.className = "form-status error";
  } finally {
    elements.recoveryCode.value = "";
    elements.recoveryPassword.value = "";
    elements.recoveryMfa.value = "";
    submit.disabled = false;
  }
}

function closeMfaDialog() {
  elements.mfaPassword.value = "";
  elements.mfaCurrentProof.value = "";
  elements.mfaConfirmCode.value = "";
  elements.mfaProvisioning.textContent = "";
  elements.mfaProvisioning.hidden = true;
  elements.mfaResult.textContent = "";
  state.mfaSetupStarted = false;
  if (elements.mfaDialog.open) {
    elements.mfaDialog.close();
  }
}

async function startMfaSetup() {
  if (!state.csrfToken || elements.mfaPassword.value.length < 12) {
    elements.mfaResult.textContent = "请输入当前密码。";
    elements.mfaResult.className = "form-status error";
    return;
  }
  elements.mfaCreate.disabled = true;
  try {
    const setup = await requestJson("/api/v1/orbit/security/totp/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({
        password: elements.mfaPassword.value,
        ...mfaProof(elements.mfaCurrentProof.value),
      }),
    });
    state.mfaSetupStarted = true;
    elements.mfaProvisioning.hidden = false;
    elements.mfaProvisioning.textContent = `手工密钥：${setup.secret}\n认证器 URI：${setup.provisioning_uri}`;
    elements.mfaResult.textContent = "请将密钥加入认证器，再输入一枚新的 6 位动态码。";
    elements.mfaResult.className = "form-status success";
    elements.mfaConfirmCode.focus();
  } catch (error) {
    elements.mfaResult.textContent = error.message;
    elements.mfaResult.className = "form-status error";
  } finally {
    elements.mfaPassword.value = "";
    elements.mfaCurrentProof.value = "";
    elements.mfaCreate.disabled = false;
  }
}

async function confirmMfaSetup(event) {
  event.preventDefault();
  if (!state.mfaSetupStarted) {
    elements.mfaResult.textContent = "请先生成认证器密钥。";
    elements.mfaResult.className = "form-status error";
    return;
  }
  const submit = elements.mfaForm.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const enabled = await requestJson("/api/v1/orbit/security/totp/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ code: elements.mfaConfirmCode.value.trim() }),
    });
    elements.mfaProvisioning.textContent = `恢复码（仅显示一次，请离线保存）：\n${enabled.recovery_codes.join("\n")}`;
    elements.mfaResult.textContent = "双重验证已开启。恢复码每枚只能使用一次，请保存后再关闭窗口。";
    elements.mfaResult.className = "form-status success";
    state.mfaSetupStarted = false;
    elements.mfaConfirmCode.value = "";
    await loadDashboard();
  } catch (error) {
    elements.mfaResult.textContent = error.message;
    elements.mfaResult.className = "form-status error";
  } finally {
    elements.mfaConfirmCode.value = "";
    submit.disabled = false;
  }
}

function closeKeyDialog() {
  elements.keyPassword.value = "";
  elements.keyMfa.value = "";
  elements.keyOutput.textContent = "";
  elements.keyOutput.hidden = true;
  elements.keyResult.textContent = "";
  if (elements.keyDialog.open) {
    elements.keyDialog.close();
  }
}

async function rotateHumanKey(event) {
  event.preventDefault();
  const submit = elements.keyForm.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const rotated = await requestJson("/api/v1/orbit/security/human-keys/rotate", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({
        password: elements.keyPassword.value,
        ...mfaProof(elements.keyMfa.value),
        label: elements.keyLabel.value.trim(),
      }),
    });
    elements.keyOutput.hidden = false;
    elements.keyOutput.textContent = rotated.access_key;
    elements.keyResult.textContent = "新凭证仅显示一次；以前的旧版集成凭证已全部失效。";
    elements.keyResult.className = "form-status success";
    elements.keyPassword.value = "";
    elements.keyMfa.value = "";
    await loadDashboard();
  } catch (error) {
    elements.keyResult.textContent = error.message;
    elements.keyResult.className = "form-status error";
  } finally {
    elements.keyPassword.value = "";
    elements.keyMfa.value = "";
    submit.disabled = false;
  }
}

async function signOut() {
  let revoked = false;
  try {
    await requestJson("/api/v1/orbit/session", {
      method: "DELETE",
      headers: state.csrfToken ? { "X-CSRF-Token": state.csrfToken } : {},
    });
    revoked = true;
  } catch (_error) {
    // Closing the local view does not prove that the server revoked the session.
  } finally {
    closeApprovalDialog();
    closePairingDialog();
    closeRevokeDialog();
    closeMfaDialog();
    closeKeyDialog();
    closeAttachmentPreview();
    closeProjectCreateDialog();
    closeProjectInviteDialog();
    state.dashboard = null;
    state.projects = [];
    state.selectedProject = null;
    state.selectedProjectId = "";
    state.projectsLoaded = false;
    state.friends = [];
    state.selectedFriendId = "";
    state.friendsLoaded = false;
    state.csrfToken = "";
    clearSensitiveInputs();
    elements.workspaceView.hidden = true;
    elements.welcomeView.hidden = false;
    if (revoked) {
      setFormStatus("浏览器会话已撤销。", "success");
      setConnection("已退出 AgentPost");
    } else {
      setFormStatus("当前视图已关闭，但服务器会话撤销未确认。恢复网络后请再次退出。", "error");
      setConnection("会话撤销未确认", "error");
    }
    if (state.authConfig?.self_service_enabled) {
      elements.loginEmail.focus();
    }
  }
}

async function decideApproval(event) {
  event.preventDefault();
  const approvalId = elements.approvalId.value;
  const decision = elements.approvalDecision.value;
  const candidate = elements.approvalAccessKey.value.trim();
  const mfa = elements.approvalMfa.value.trim();
  if (!state.csrfToken || !approvalId || !["approved", "rejected"].includes(decision)) {
    elements.approvalResult.textContent = "审批上下文已失效，请关闭窗口并刷新 AgentPost。";
    elements.approvalResult.className = "form-status error";
    return;
  }
  if (!validReauthenticationCandidate(candidate)) {
    elements.approvalResult.textContent = "请输入当前密码（或有效的旧版集成凭证）。";
    elements.approvalResult.className = "form-status error";
    return;
  }
  elements.approvalSubmit.disabled = true;
  elements.approvalResult.textContent = "正在重新验证身份并签发一次性确认…";
  elements.approvalResult.className = "form-status";
  try {
    let confirmation;
    try {
      const proof = reauthentication(candidate, mfa, {
        intent: decision === "approved" ? "approve" : "reject",
      });
      confirmation = await requestJson(
        `/api/v1/orbit/approval-requests/${encodeURIComponent(approvalId)}/confirmation`,
        {
          method: "POST",
          headers: proof.headers,
          body: JSON.stringify(proof.payload),
        },
      );
    } finally {
      elements.approvalAccessKey.value = "";
      elements.approvalMfa.value = "";
    }
    elements.approvalResult.textContent = "身份已确认，正在原子写入审批决定…";
    const note = elements.approvalNote.value.trim();
    await requestJson(
      `/api/v1/orbit/approval-requests/${encodeURIComponent(approvalId)}/decision`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `xinggui-${crypto.randomUUID()}`,
          "X-CSRF-Token": state.csrfToken,
          "X-Human-Confirmation": confirmation.confirmation_token,
        },
        body: JSON.stringify({ decision, note: note || null }),
      },
    );
    closeApprovalDialog();
    await loadDashboard();
    setConnection("审批决定已记录，等待 Agent 轮询", "success");
  } catch (error) {
    elements.approvalAccessKey.value = "";
    elements.approvalMfa.value = "";
    elements.approvalResult.textContent = error.message;
    elements.approvalResult.className = "form-status error";
  } finally {
    elements.approvalSubmit.disabled = false;
  }
}

async function restoreSession() {
  try {
    const browserSession = await requestJson("/api/v1/orbit/session");
    state.csrfToken = browserSession.csrf_token;
    await loadDashboard();
  } catch (error) {
    state.csrfToken = "";
    elements.workspaceView.hidden = true;
    elements.welcomeView.hidden = false;
    if (error.status === 401) {
      setConnection("等待进入 AgentPost");
      return;
    }
    setFormStatus("暂时无法恢复 AgentPost 会话，请稍后重试。", "error");
  }
}

elements.loginForm.addEventListener("submit", loginHuman);
elements.taskFileSearch.addEventListener("input", () => {
  state.taskFileQuery = elements.taskFileSearch.value.trim();
  if (currentTaskForAction()) renderTaskFiles(currentTaskForAction());
});
elements.taskFileUploader.addEventListener("change", () => {
  state.taskFileUploader = elements.taskFileUploader.value;
  if (currentTaskForAction()) renderTaskFiles(currentTaskForAction());
});
elements.taskFileType.addEventListener("change", () => {
  state.taskFileType = elements.taskFileType.value;
  if (currentTaskForAction()) renderTaskFiles(currentTaskForAction());
});
elements.taskFileMine.addEventListener("change", () => {
  state.taskFileMine = elements.taskFileMine.checked;
  if (currentTaskForAction()) renderTaskFiles(currentTaskForAction());
});
elements.taskFileClear.addEventListener("click", () => {
  state.taskFileQuery = "";
  state.taskFileUploader = "";
  state.taskFileType = "";
  state.taskFileMine = false;
  elements.taskFileSearch.value = "";
  elements.taskFileUploader.value = "";
  elements.taskFileType.value = "";
  elements.taskFileMine.checked = false;
  if (currentTaskForAction()) renderTaskFiles(currentTaskForAction());
});
elements.attachmentPreviewClose.addEventListener("click", closeAttachmentPreview);
elements.attachmentPreviewDone.addEventListener("click", closeAttachmentPreview);
elements.attachmentPreviewDialog.addEventListener("close", () => {
  elements.attachmentPreviewFrame.removeAttribute("src");
  elements.attachmentPreviewDownload.removeAttribute("href");
  elements.attachmentPreviewMeta.textContent = "";
});
elements.openRegister.addEventListener("click", () => {
  elements.registerResult.textContent = "邮箱验证码有效期有限，请在收到后及时完成注册。";
  elements.registerDialog.showModal();
  elements.registerEmail.focus();
});
elements.registerForm.addEventListener("submit", registerHuman);
elements.registerSendCode.addEventListener("click", () => sendEmailChallenge("register"));
elements.registerClose.addEventListener("click", closeRegisterDialog);
elements.registerCancel.addEventListener("click", closeRegisterDialog);
elements.registerDialog.addEventListener("close", closeRegisterDialog);
elements.openRecovery.addEventListener("click", () => {
  elements.recoveryResult.textContent = "重设密码将退出其他浏览器，并使所有旧版集成凭证失效。";
  elements.recoveryDialog.showModal();
  elements.recoveryEmail.focus();
});
elements.recoveryForm.addEventListener("submit", recoverHuman);
elements.recoverySendCode.addEventListener("click", () => sendEmailChallenge("recover"));
elements.recoveryClose.addEventListener("click", closeRecoveryDialog);
elements.recoveryCancel.addEventListener("click", closeRecoveryDialog);
elements.recoveryDialog.addEventListener("close", closeRecoveryDialog);
elements.refresh.addEventListener("click", async () => {
  try {
    await loadDashboard();
  } catch (error) {
    setConnection(error.message, "error");
  }
});
elements.signOut.addEventListener("click", signOut);
elements.profileRefresh.addEventListener("click", async () => {
  try {
    await loadDashboard();
  } catch (error) {
    setConnection(error.message, "error");
  }
});
elements.profileSignOut.addEventListener("click", signOut);
elements.profileUsernameForm.addEventListener("submit", updateProfileUsername);
elements.threadSearchInput.addEventListener("input", () => {
  state.threadQuery = elements.threadSearchInput.value.trim();
  state.selectedThreadId = "";
  state.selectedThread = null;
  updateThreadWorkspaceMode();
  setThreadDetailEmpty("选择一条协作对话", "搜索结果只包含你有权查看的内容。");
  history.replaceState(
    { module: "orbit", section: "communications" },
    "",
    threadRouteUrl(),
  );
  window.clearTimeout(state.threadSearchTimer);
  state.threadSearchTimer = window.setTimeout(async () => {
    try {
      await loadThreads({ loadSelection: false });
    } catch (_error) {
      elements.threadList.replaceChildren(emptyState("搜索暂时不可用，请稍后重试。"));
    }
  }, 260);
});
elements.threadFilters.forEach((button) => {
  button.addEventListener("click", async () => {
    if (button.getAttribute("aria-disabled") === "true") {
      return;
    }
    const requestedFilter = button.dataset.threadFilter || "all";
    state.threadFilter = requestedFilter === "archived" && state.threadFilter === "archived"
      ? "all"
      : requestedFilter;
    syncThreadFilterControls();
    state.selectedThreadId = "";
    state.selectedThread = null;
    setThreadDetailEmpty(
      "选择一条协作对话",
      state.threadFilter === "archived"
        ? "这里集中保存你从“我的对话”移出的完整对话，可随时恢复。"
        : "当前列表已按所选范围筛选。",
    );
    updateThreadWorkspaceMode();
    if (requestedFilter === "archived" && isMobileWorkspace()) {
      activateRoute("orbit", "communications", { focusContent: true });
    }
    try {
      await loadThreads({ loadSelection: false });
    } catch (_error) {
      elements.threadList.replaceChildren(emptyState("对话列表读取失败，请稍后重试。"));
    }
    history.replaceState(
      { module: "orbit", section: "communications", thread: state.selectedThreadId || null },
      "",
      threadRouteUrl(),
    );
  });
});
elements.threadList.addEventListener("keydown", (event) => {
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) {
    return;
  }
  const items = Array.from(elements.threadList.querySelectorAll(".thread-list-item"));
  const index = items.indexOf(document.activeElement);
  if (index < 0 || items.length < 2) {
    return;
  }
  event.preventDefault();
  const direction = event.key === "ArrowDown" ? 1 : -1;
  items[(index + direction + items.length) % items.length].focus();
});
elements.threadMobileBack.addEventListener("click", () => clearThreadSelection());
elements.threadArchive.addEventListener("click", async () => {
  if (!state.selectedThreadId || !state.selectedThread) {
    return;
  }
  if (Boolean(state.selectedThread.archived_at) || state.threadFilter === "archived") {
    try {
      await restoreThread(state.selectedThreadId);
    } catch (_error) {
      setThreadDetailEmpty("暂时无法恢复", "请稍后重试，这条对话仍保留在已归档对话中。");
    }
    return;
  }
  openThreadArchiveDialog(state.selectedThread);
});
elements.threadArchiveForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const threadId = elements.threadArchiveId.value;
  if (!threadId) {
    return;
  }
  elements.threadArchiveSubmit.disabled = true;
  elements.threadArchiveResult.textContent = "正在整理…";
  try {
    await archiveThread(threadId);
    closeThreadArchiveDialog();
  } catch (_error) {
    elements.threadArchiveResult.textContent = "暂时无法移出，请稍后重试。";
  } finally {
    elements.threadArchiveSubmit.disabled = false;
  }
});
[elements.threadArchiveClose, elements.threadArchiveCancel].forEach((button) => {
  button.addEventListener("click", () => closeThreadArchiveDialog());
});
elements.threadLatest.addEventListener("click", () => {
  elements.messageList.firstElementChild?.scrollIntoView({ behavior: "smooth", block: "start" });
});
elements.agentSearchInput.addEventListener("input", () => {
  state.agentQuery = elements.agentSearchInput.value.trim();
  renderAgentBrowser(state.dashboard?.agents || []);
  history.replaceState(
    { module: "relay", section: "agents", agent: state.selectedAgentId || null },
    "",
    agentRouteUrl(),
  );
});
[elements.agentBrowserNew, elements.agentOverviewNew].forEach((button) => {
  button.addEventListener("click", () => openPairingDialog());
});
elements.agentMobileBack.addEventListener("click", () => clearAgentSelection());
elements.agentDetailTabs.forEach((button) => {
  button.addEventListener("click", () => {
    state.agentTab = button.dataset.agentTab || "summary";
    renderAgentTab();
    history.replaceState(
      { module: "relay", section: "agents", agent: state.selectedAgentId, agentTab: state.agentTab },
      "",
      agentRouteUrl(),
    );
  });
});
elements.agentBrowserList.addEventListener("keydown", (event) => {
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
  const items = Array.from(elements.agentBrowserList.querySelectorAll(".agent-browser-item"));
  const index = items.indexOf(document.activeElement);
  if (index < 0 || items.length < 2) return;
  event.preventDefault();
  const direction = event.key === "ArrowDown" ? 1 : -1;
  items[(index + direction + items.length) % items.length].focus();
});
elements.agentReturnThread.addEventListener("click", () => {
  const threadId = new URLSearchParams(window.location.search).get("returnThread");
  if (threadId) openRelatedThread(threadId);
});
elements.agentReconnect.addEventListener("click", () => {
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner") return;
  const connector = state.connectors.find(
    (item) => String(item.agent?.id) === String(agent.id) && item.is_current,
  ) || state.connectors.find((item) => String(item.agent?.id) === String(agent.id));
  openPairingDialog("", "", agent, safeText(connector?.connector_type, agent.current_connector_type || ""));
});
elements.agentRename.addEventListener("click", () => {
  if (state.selectedAgent?.role === "owner") openHandleDialog(state.selectedAgent);
});
elements.agentSetDefault.addEventListener("click", setSelectedAgentAsDefault);
elements.agentDisconnect.addEventListener("click", () => {
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner") return;
  const connector = state.connectors.find(
    (item) => String(item.agent?.id) === String(agent.id)
      && item.is_current && item.status === "active",
  );
  if (connector) openRevokeDialog(connector);
});
elements.agentDelete.addEventListener("click", () => {
  if (state.selectedAgent?.role === "owner") openDeleteAgentDialog(state.selectedAgent);
});
elements.agentWakeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner") {
    elements.agentWakeResult.textContent = "当前 Agent 不存在或你没有配置权限。";
    elements.agentWakeResult.className = "form-status error";
    return;
  }
  const isAily = agent.current_connector_type === "feishu_aily";
  elements.agentWakeSave.disabled = true;
  elements.agentWakeResult.textContent = isAily
    ? "正在加密保存自动唤醒配置…"
    : "正在加密保存飞书消息提醒…";
  elements.agentWakeResult.className = "form-status";
  try {
    const endpoint = isAily
      ? `/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/wake-channel/feishu-aily`
      : `/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/notification-channel/feishu`;
    const channel = await requestJson(endpoint, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({
        webhook_url: elements.agentWakeUrl.value.trim(),
        bearer_token: elements.agentWakeToken.value,
        auth_scheme: elements.agentWakeAuth.value,
      }),
    });
    renderAgentWakeChannel(agent, channel);
    elements.agentWakeResult.textContent = isAily
      ? "配置已保存。请发送一次测试唤醒，确认 aily 工作流可以接收。"
      : "配置已保存。请发送一次测试提醒，并在飞书工作流记录中核对是否收到。";
  } catch (error) {
    elements.agentWakeToken.value = "";
    elements.agentWakeResult.textContent = error.message;
    elements.agentWakeResult.className = "form-status error";
  } finally {
    elements.agentWakeSave.disabled = false;
  }
});
elements.agentWakeTest.addEventListener("click", async () => {
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner") return;
  if (!elements.agentWakeTestConsent.checked) {
    elements.agentWakeResult.textContent = "请先勾选测试额度确认。每次点击只发一次；结果不明时请先查飞书执行记录。";
    return;
  }
  elements.agentWakeTestConsent.checked = false;
  elements.agentWakeTest.disabled = true;
  const isAily = agent.current_connector_type === "feishu_aily";
  elements.agentWakeResult.textContent = isAily ? "正在发送测试唤醒…" : "正在发送测试提醒…";
  elements.agentWakeResult.className = "form-status";
  try {
    const result = await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/wake-channel/test`, {
      method: "POST",
      headers: { "X-CSRF-Token": state.csrfToken },
    });
    await loadAgentWakeChannel(agent);
    elements.agentWakeResult.textContent = result.delivered
      ? isAily
        ? "工作流已接受测试请求；仍需验证 Agent 实际启动、领取工作并回传结果。"
        : "飞书工作流已接受测试请求。请核对接收人收到消息；这不代表 Agent 已开始执行。"
      : `测试未完成：${wakeErrorCopy(result.error_code)}（请求编号：${safeText(result.request_id)}）`;
    elements.agentWakeResult.className = result.delivered ? "form-status success" : "form-status error";
  } catch (error) {
    elements.agentWakeResult.textContent = error.message;
    elements.agentWakeResult.className = "form-status error";
  } finally {
    elements.agentWakeTest.disabled = false;
  }
});
elements.agentWakeDisable.addEventListener("click", async () => {
  const agent = state.selectedAgent;
  if (!agent || agent.role !== "owner") return;
  elements.agentWakeDisable.disabled = true;
  elements.agentWakeResult.textContent = "正在停用…";
  try {
    await requestJson(`/api/v1/orbit/agents/${encodeURIComponent(agent.id)}/wake-channel`, {
      method: "DELETE",
      headers: { "X-CSRF-Token": state.csrfToken },
    });
    renderAgentWakeChannel(agent);
    elements.agentWakeResult.textContent = agent.current_connector_type === "feishu_aily"
      ? "自动唤醒已停用。aily 的 AgentPost 身份和历史任务仍保留。"
      : "飞书消息提醒已停用。Agent 的连接、任务权限和历史记录不受影响。";
    elements.agentWakeResult.className = "form-status success";
  } catch (error) {
    elements.agentWakeResult.textContent = error.message;
    elements.agentWakeResult.className = "form-status error";
    elements.agentWakeDisable.disabled = false;
  }
});
elements.approvalForm.addEventListener("submit", decideApproval);
elements.approvalClose.addEventListener("click", closeApprovalDialog);
elements.approvalCancel.addEventListener("click", closeApprovalDialog);
elements.approvalDialog.addEventListener("close", closeApprovalDialog);
elements.openPairing.addEventListener("click", () => openPairingDialog());
elements.pairingHostCards.forEach((button) => {
  button.addEventListener("click", () => selectPairingHost(button.dataset.connectorType));
});
elements.pairingCopyPrompt.addEventListener("click", copyPairingPrompt);
elements.pairingGuideBack.addEventListener("click", () => showPairingGuide());
elements.pairingGuideCancel.addEventListener("click", () => closePairingDialog());
elements.pairingForm.addEventListener("submit", decidePairing);
elements.pairingDeny.addEventListener("click", (event) => decidePairing(event, "denied"));
elements.pairingClose.addEventListener("click", () => closePairingDialog());
elements.pairingCancel.addEventListener("click", () => closePairingDialog());
elements.pairingDialog.addEventListener("close", () => closePairingDialog());
elements.handleForm.addEventListener("submit", saveAgentHandle);
elements.handleClose.addEventListener("click", closeHandleDialog);
elements.handleCancel.addEventListener("click", closeHandleDialog);
elements.handleDialog.addEventListener("close", closeHandleDialog);
elements.pairingId.addEventListener("change", loadPairingPreview);
elements.pairingTargetMode.addEventListener("change", updatePairingTargetMode);
elements.pairingHandle.addEventListener("input", updatePairingHandleHelp);
elements.pairingExistingAgent.addEventListener("change", () => {
  if (state.pairingTargetResolution !== "ambiguous") {
    return;
  }
  state.pairingCreateNewAutomatically = elements.pairingExistingAgent.value === "__create_new__";
  elements.pairingTargetMode.value = state.pairingCreateNewAutomatically ? "new" : "existing";
  if (state.pairingCreateNewAutomatically) {
    elements.pairingTargetSummary.textContent = "将创建另一个独立 Agent。它会拥有新的身份、任务参与记录和连接；重新连接或升级时不要选择这一项。";
    setSuggestedPairingHandle(state.pairingConnectorType || "agent");
  } else {
    const selected = (state.dashboard?.agents || []).find(
      (agent) => String(agent.id) === elements.pairingExistingAgent.value,
    );
    elements.pairingTargetSummary.textContent = `将重新连接 ${safeText(selected?.handle, selected?.display_name)}；原身份、权限、任务和历史保持不变。`;
    elements.pairingHandle.value = safeText(selected?.handle, "");
    state.pairingSuggestedHandle = elements.pairingHandle.value;
    updatePairingHandleHelp();
  }
});
elements.pairingLocalId.addEventListener("change", () => {
  elements.pairingLocalId.value = canonicalPairingLocalId(elements.pairingLocalId.value);
});
elements.revokeForm.addEventListener("submit", revokeConnector);
elements.revokeClose.addEventListener("click", closeRevokeDialog);
elements.revokeCancel.addEventListener("click", closeRevokeDialog);
elements.revokeDialog.addEventListener("close", closeRevokeDialog);
elements.deleteAgentForm.addEventListener("submit", deleteAgent);
elements.deleteAgentClose.addEventListener("click", closeDeleteAgentDialog);
elements.deleteAgentCancel.addEventListener("click", closeDeleteAgentDialog);
elements.deleteAgentDialog.addEventListener("close", closeDeleteAgentDialog);
elements.openMfa.addEventListener("click", () => {
  elements.mfaResult.textContent = "重新验证后生成只在当前窗口显示的认证器密钥。";
  elements.mfaDialog.showModal();
  elements.mfaPassword.focus();
});
elements.mfaCreate.addEventListener("click", startMfaSetup);
elements.mfaForm.addEventListener("submit", confirmMfaSetup);
elements.mfaClose.addEventListener("click", closeMfaDialog);
elements.mfaCancel.addEventListener("click", closeMfaDialog);
elements.mfaDialog.addEventListener("close", closeMfaDialog);
elements.openKeyRotation.addEventListener("click", () => {
  elements.keyResult.textContent = "更换后，以前的旧版集成凭证将立即失效。";
  elements.keyDialog.showModal();
  elements.keyPassword.focus();
});
elements.keyForm.addEventListener("submit", rotateHumanKey);
elements.keyClose.addEventListener("click", closeKeyDialog);
elements.keyCancel.addEventListener("click", closeKeyDialog);
elements.keyDialog.addEventListener("close", closeKeyDialog);

window.addEventListener("popstate", () => {
  const parameters = new URLSearchParams(window.location.search);
  const previousQuery = state.threadQuery;
  const previousFilter = state.threadFilter;
  applyThreadRouteParameters(parameters);
  applyAgentRouteParameters(parameters);
  activateRoute(parameters.get("module") || "orbit", parameters.get("view") || "", {
    updateHistory: false,
  });
  renderThreadList();
  if (state.activeModule === "orbit" && state.activeSection === "communications") {
    if (
      previousQuery !== state.threadQuery
      || previousFilter !== state.threadFilter
    ) {
      void loadThreads();
    } else if (state.selectedThreadId) {
      void loadThreadDetail(state.selectedThreadId);
    } else {
      setThreadDetailEmpty("选择一条协作对话", "选择一个对话后，这个话题下的全部往来会按时间显示在这里。");
    }
  } else if (state.activeModule === "relay" && state.activeSection === "agents") {
    renderAgents(state.dashboard?.agents || []);
  } else if (state.activeModule === "projects") {
    void selectTask(parameters.get("task") || "", { updateHistory: false });
  }
});

window.addEventListener("pagehide", () => {
  clearSensitiveInputs();
  state.csrfToken = "";
});

async function initializeOrbit() {
  initializeWorkspaceNavigation();
  initializeCollaborationModules();
  history.replaceState(
    { module: state.activeModule, section: state.activeSection },
    "",
    routeUrl(state.activeModule, state.activeSection),
  );
  await loadAuthConfig();
  await restoreSession();
}

initializeOrbit();


function updateTaskNavDot() {
  const nav = document.querySelector('button[data-module="projects"]');
  if (!nav) return;
  nav.querySelector(".task-new-dot")?.remove();
  if (state.projects.some((p) => p.unread_count > 0 && (!p.personal_state || p.personal_state === "active"))) {
    const dot = document.createElement("span");
    dot.className = "task-new-dot";
    dot.setAttribute("role", "img");
    dot.setAttribute("aria-label", "任务有新消息");
    nav.querySelector("strong")?.append(dot);
  }
}

function renderTaskPreferences(project) {
  const personalState = project.personal_state || "active";
  document.querySelector("#task-personal-archive").hidden = personalState !== "active";
  document.querySelector("#task-personal-delete").hidden = personalState === "deleted";
  document.querySelector("#task-personal-restore").hidden = !["archived", "deleted"].includes(personalState);
  document.querySelector("#task-leave").disabled = project.membership_role === "owner";
  document.querySelector("#task-leave-hint").textContent = project.membership_role === "owner"
    ? "你是负责人，不能直接退出；可使用个人归档。" : "退出后，你及你的 AI 将失去任务访问权，未结束的工作将取消。";
  document.querySelector("#task-personal-feedback").textContent = "";
}

function positionTaskPersonalMenu() {
  const menu = document.querySelector("#task-personal-menu");
  const panel = menu.querySelector(".task-personal-actions");
  const summary = menu.querySelector("summary");
  if (!menu.open) return;
  const margin = 12;
  const gap = 8;
  const trigger = summary.getBoundingClientRect();
  const width = Math.min(330, window.innerWidth - margin * 2);
  const availableBelow = window.innerHeight - trigger.bottom - gap - margin;
  const availableAbove = trigger.top - gap - margin;
  const openBelow = availableBelow >= Math.min(panel.scrollHeight, 280) || availableBelow >= availableAbove;
  const availableHeight = Math.max(160, openBelow ? availableBelow : availableAbove);
  const height = Math.min(panel.scrollHeight, availableHeight);
  panel.style.width = `${width}px`;
  panel.style.left = `${Math.max(margin, Math.min(trigger.right - width, window.innerWidth - width - margin))}px`;
  panel.style.top = `${openBelow ? trigger.bottom + gap : Math.max(margin, trigger.top - gap - height)}px`;
  panel.style.maxHeight = `${availableHeight}px`;
}

async function markTaskSnapshotViewed(project) {
  const ids = (project.activities || []).map((item) => item.activity_id);
  if (!ids.length) return;
  try {
    const pref = await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/preferences`, {
      method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      body: JSON.stringify({ seen_activity_ids: ids }),
    });
    const row = state.projects.find((p) => p.task_id === project.task_id);
    if (row) Object.assign(row, pref);
    renderProjectBrowser({ detail: false });
  } catch (_) { /* A failed Human view write must not hide unread messages. */ }
}

async function changeTaskPreference(action) {
  const project = currentTaskForAction();
  if (!project) return;
  const menu = document.querySelector("#task-personal-menu");
  const buttons = [...menu.querySelectorAll("button")];
  if (buttons.some((button) => button.dataset.busy)) return;
  if (action === "leave" && !window.confirm("退出此任务？你及你的 AI 将失去访问权限，未结束的工作将取消。需负责人重新邀请才能加入。")) return;
  const payload = { list_state: action };
  buttons.forEach((button) => { button.dataset.busy = "true"; button.disabled = true; });
  try {
    await requestJson(`/api/v1/tasks/${encodeURIComponent(project.task_id)}/${action === "leave" ? "leave" : "preferences"}`, {
      method: action === "leave" ? "POST" : "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": state.csrfToken },
      ...(action === "leave" ? {} : { body: JSON.stringify(payload) }),
    });
    if (state.selectedProjectId !== project.task_id) return;
    const nextFilter = action === "deleted" ? "deleted" : action === "archived" ? "archived" : "active";
    setProjectFilter(nextFilter);
    await loadProjects();
    if (action !== "leave") {
      await selectTask(project.task_id);
      elements.projectActionResult.textContent = action === "deleted"
        ? "已移到“已删除”。当前页面可直接选择“恢复到任务列表”。"
        : action === "archived"
          ? "已移到“我的归档”。当前页面可直接恢复。"
          : "已恢复到任务列表。";
    } else {
      await selectTask("");
    }
  } catch (error) {
    if (state.selectedProjectId === project.task_id) document.querySelector("#task-personal-feedback").textContent = error.message;
  } finally {
    buttons.forEach((button) => { delete button.dataset.busy; button.disabled = false; });
    document.querySelector("#task-leave").disabled = currentTaskForAction()?.membership_role === "owner";
  }
}

for (const [id, action] of [["task-personal-archive", "archived"], ["task-personal-delete", "deleted"], ["task-personal-restore", "active"], ["task-leave", "leave"]]) {
  document.getElementById(id).addEventListener("click", () => void changeTaskPreference(action));
}
document.getElementById("task-open-deleted").addEventListener("click", () => {
  document.querySelector("#task-personal-menu").open = false;
  setProjectFilter("deleted");
  const projects = filteredProjects();
  void selectTask(isMobileWorkspace() ? "" : (projects[0]?.task_id || ""));
  document.querySelector('[data-project-filter="deleted"]')?.focus({ preventScroll: true });
  resetMobileLayerScroll();
});
document.querySelector("#task-personal-menu").addEventListener("toggle", (event) => {
  if (event.currentTarget.open) window.requestAnimationFrame(positionTaskPersonalMenu);
});
window.addEventListener("resize", positionTaskPersonalMenu);
window.addEventListener("scroll", positionTaskPersonalMenu, { passive: true });
const backToTop = document.querySelector("#back-to-top");
window.addEventListener("scroll", () => { backToTop.hidden = window.scrollY < 400; }, { passive: true });
backToTop.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
});
let taskIndicatorLoading = false;
setInterval(async () => {
  if (!state.dashboard || !state.csrfToken || document.visibilityState !== "visible" || taskIndicatorLoading) return;
  taskIndicatorLoading = true;
  try {
    const payload = await requestJson("/api/v1/tasks");
    if (!state.dashboard) return;
    state.projects = payload.items || [];
    renderProjectBrowser({ detail: false });
  } catch (_) { /* Keep the last known indicators on transient failure. */ }
  finally { taskIndicatorLoading = false; }
}, 30000);
