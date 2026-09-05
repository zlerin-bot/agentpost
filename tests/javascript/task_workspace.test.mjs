import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const script = await readFile(new URL("../../src/agentpost/orbit_ui/app.js", import.meta.url), "utf8");
const section = (start, end) => script.slice(script.indexOf(start), script.indexOf(end));

test("late task responses, including failures and A-B-A races, cannot replace current detail", async () => {
  const state = { selectedProjectId: "A", selectedProject: null, taskRequestSequence: 0, taskActivityLimit: 200 };
  const requests = [];
  const request = () => new Promise((resolve, reject) => requests.push({ resolve, reject }));
  let renders = 0;
  const load = new Function("state", "requestJson", "renderProjectDetail", "window", "history", "taskRouteUrl",
    section("async function loadProjectDetail(", "function taskRouteUrl(") + ";return loadProjectDetail;")(
    state, request, () => { renders++; }, { location: { href: "https://example.test/orbit?task=A" } }, {}, () => "");
  const first = load("A");
  state.selectedProjectId = "B";
  const second = load("B");
  state.selectedProjectId = "A";
  const third = load("A");
  requests[2].resolve({ task_id: "A", title: "fresh" });
  await third;
  requests[0].resolve({ task_id: "A", title: "stale" });
  requests[1].reject(Object.assign(new Error("not found"), { status: 404 }));
  await Promise.all([first, second]);
  assert.equal(state.selectedProject.title, "fresh");
  assert.equal(renders, 1);
  const failure = load("A");
  requests[3].reject(Object.assign(new Error("not found"), { status: 404 }));
  await failure;
  assert.equal(state.selectedProject, null);
  assert.match(state.taskLoadError, /任务不可用/);
  assert.equal(requests.length, 4, "404 must not recursively reload the task list");
});

test("in-flight mutations cannot update a different selected task", () => {
  const state = { selectedProjectId: "B", selectedProject: { task_id: "A" }, taskRequestSequence: 1 };
  const { currentTaskForAction, acceptTaskUpdate } = new Function("state",
    section("function currentTaskForAction(", "function bindTaskAction(") + ";return { currentTaskForAction, acceptTaskUpdate };")(state);
  assert.equal(currentTaskForAction(), null);
  assert.equal(acceptTaskUpdate("A", { task_id: "A" }), false);
  assert.equal(acceptTaskUpdate("B", { task_id: "B" }), true);
  assert.equal(currentTaskForAction().task_id, "B");
  assert.equal(state.taskRequestSequence, 2);
});

test("task URLs explicitly identify the selected task and drop stale record anchors", () => {
  const route = new Function("window", section("function taskRouteUrl(", "function currentTaskForAction(")
    + ";return taskRouteUrl;")({ location: { href: "https://example.test/orbit?module=projects&view=board&task=A#old" } });
  assert.equal(route("B"), "/orbit?module=projects&view=board&task=B");
  assert.equal(route(""), "/orbit?module=projects&view=board");
});

test("loading a different task makes the entire old action surface hidden and inert", () => {
  const item = () => ({ hidden: false, inert: false, textContent: "old", setAttribute() {} });
  const content = item();
  const loading = { ...item(), querySelector: () => item() };
  const elements = { projectEmpty: item(), projectDetail: item(), projectDetailTitle: item(), projectDetailDescription: item() };
  const document = { querySelector: selector => selector === "#task-detail-content" ? content : loading };
  const state = { selectedProjectId: "B", selectedProject: { task_id: "A" }, taskLoadError: "" };
  new Function("state", "elements", "document",
    section("function renderProjectDetail()", "  const owner = project.members.find") + "};renderProjectDetail();")(
    state, elements, document);
  assert.equal(content.hidden, true);
  assert.equal(content.inert, true);
  assert.equal(loading.hidden, false);
});

test("refresh after task creation keeps the new selection instead of the old URL task", async () => {
  const state = { dashboard: {}, selectedProjectId: "B", projectsLoaded: true };
  const load = new Function("state", "requestJson", "window", "projectById", "isMobileWorkspace",
    "renderProjectBrowser", "updateCollaborationWorkspaceMode", "loadProjectDetail", "renderFriendDetail", "elements",
    section("async function loadProjects(", "async function loadProjectDetail(") + ";return loadProjects;")(
    state, async () => ({ items: [{ task_id: "A" }, { task_id: "B" }] }),
    { location: { href: "https://example.test/orbit?task=A" } }, id => state.projects.find(item => item.task_id === id),
    () => false, () => {}, () => {}, async id => { assert.equal(id, "B"); }, () => {}, {});
  await load();
  assert.equal(state.selectedProjectId, "B");
});

test("submission diagnostics include every server blocker, even deduplicated participation", () => {
  const blockers = new Function(section("function taskSubmissionBlockers(", "function renderTaskAttention(")
    + ";return taskSubmissionBlockers;")();
  assert.deepEqual(blockers({ assignments: [
    { assignment_id: "a", assignment_kind: "participant_start", status: "queued" },
    { assignment_id: "b", assignment_kind: "participant_start", status: "queued" },
    { assignment_id: "c", assignment_kind: "human_directed", status: "partial" },
    { assignment_id: "d", status: "completed" }, { assignment_id: "e", status: "cancelled" },
  ] }).map(item => item.assignment_id), ["a", "b", "c"]);
});

test("participation questions stay actionable without treating ordinary participation as work", () => {
  const visible = new Function(section("function operationalTaskAssignments(", "function humanColorTone(")
    + ";return visibleTaskAssignments;")();
  const project = { assignments: [
    { assignment_id: "question", assignee_agent_id: "one", assignment_kind: "participant_start", status: "waiting_human", run_status: "waiting_human" },
    { assignment_id: "ordinary", assignee_agent_id: "two", assignment_kind: "participant_start", status: "queued", run_status: "queued" },
  ] };
  assert.deepEqual(visible(project).map(item => item.assignment_id), ["question"]);
});

class TextNode {
  constructor(tag = "#text") { this.tagName = tag.toUpperCase(); this.children = []; this.textContent = ""; this.events = {}; }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute() {}
  addEventListener(event, handler) { this.events[event] = handler; }
}
test("readable content only constructs safe text elements, never HTML or remote links", () => {
  const document = {
    createElement: tag => new TextNode(tag),
    createTextNode: text => Object.assign(new TextNode(), { textContent: text }),
  };
  const render = new Function("document", section("function appendSafeTaskInline(", "function createTaskActivityAttachment(")
    + ";return createSafeTaskReading;")(document);
  const root = render("# 标题\n\n- **重要** 内容\n- `标识`\n<script>alert(1)</script>\n![外部图片](https://example.test/x)\n[坏链接](javascript:alert(1))\n```\n<img onerror=alert(1)>\n```");
  const flatten = node => [node, ...node.children.flatMap(flatten)];
  const nodes = flatten(root);
  assert(nodes.some(node => node.tagName === "H3"));
  assert(nodes.some(node => node.tagName === "STRONG" && node.textContent === "重要"));
  assert(nodes.some(node => node.textContent.includes("<script>")));
  assert(nodes.every(node => !["SCRIPT", "IMG", "A", "IFRAME", "FORM"].includes(node.tagName)));
});

test("uncertain reply retries preserve both original content and the idempotency key", async () => {
  const document = { createElement: tag => new TextNode(tag) };
  const state = { dashboard: { user: { display_name: "Human" } }, selectedProjectId: "task",
    csrfToken: "test-csrf", taskReplyDrafts: new Map() };
  const source = section('      const form = document.createElement("form");\n      form.className = "task-reply-form";',
    "      reply.append(replyLabel, form);");
  const calls = [];
  const { input, form } = new Function("document", "state", "project", "activity", "actorHuman", "crypto",
    "taskContentTitle", "requestJson", "loadProjectDetail", "revealTaskRecord", "reply", "replyLabel",
    source + ";return {input, form};")(
    document, state, { task_id: "task" }, { activity_id: "original" }, "Author",
    { randomUUID: () => "stable-test-key" }, () => "Original message",
    async (_path, options) => { calls.push(options); if (calls.length === 1) throw new Error("timeout"); },
    async () => {}, () => {}, {}, {});
  input.value = "Original reply";
  await form.events.submit({ preventDefault() {} });
  assert.equal(input.disabled, true);
  assert.equal(state.taskReplyDrafts.size, 1);
  input.value = "Edited after timeout";
  await form.events.submit({ preventDefault() {} });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].body, calls[1].body);
  assert.equal(calls[0].headers["Idempotency-Key"], calls[1].headers["Idempotency-Key"]);
  assert.equal(JSON.parse(calls[1].body).reply_to_activity_id, "original");
  assert.equal(state.taskReplyDrafts.size, 0);
});

test("one form cannot issue duplicate submissions while its request is pending", async () => {
  let listener;
  const element = { addEventListener: (_event, handler) => { listener = handler; } };
  let resolve;
  let calls = 0;
  const bind = new Function(section("function bindTaskAction(", "async function selectTask(") + ";return bindTaskAction;")();
  bind(element, "submit", () => { calls++; return new Promise(done => { resolve = done; }); });
  const first = listener({ preventDefault() {} });
  await listener({ preventDefault() {} });
  assert.equal(calls, 1);
  resolve();
  await first;
});
