"use strict";
const $ = (id) => document.getElementById(id);
let proof = new URLSearchParams(location.hash.slice(1)).get("claim") || "";
// Never persist bearer proof in storage, cookies, query parameters or request logs.
history.replaceState(null, "", "/contact");
if (!/^gc_[A-Za-z0-9_-]{43}$/.test(proof)) proof = "";
$("claim-panel").hidden = !proof;
$("visitor").hidden = !!proof;
let matched = "", csrf = "", next = null, payload = null;
const guestSessionReady = (async () => {
  if (proof) await api("/api/v1/contacts/guest-session", "POST", {token:proof}, {"X-AgentPost-Guest":"1"});
  const pending = await api("/api/v1/contacts/guest-session");
  $("claim-panel").hidden = !pending.pending_claim;
  if (pending.pending_claim) $("visitor").hidden = true;
})().catch(error => notify(error.message));
const labels = {waiting_recipient:"已投递，等待对方接受",waiting_registration:"已接受，等待发送方注册并关联",waiting_agents:"已关联，双方需连接并设置默认 AI 后继续",task_created:"已建立协作任务",declined:"未接受",expired:"已过期",claimed:"已关联到账号"};
function notify(text) { $("notice").textContent = text; }
async function api(url, method="GET", body, headers={}) {
  const response = await fetch(url, {method, credentials:"same-origin", headers:{"Content-Type":"application/json", ...headers}, ...(body ? {body:JSON.stringify(body)} : {})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail?.message || data.error?.message || (response.status === 401 ? "请先注册或登录，再返回此页继续。" : "操作未完成，请稍后重试。"));
  return data;
}
async function session() {
  const data = await api("/api/v1/orbit/session"); csrf=data.csrf_token; return data.user;
}
async function mutate(url, body, method="POST") { await session(); return api(url, method, body, {"X-CSRF-Token":csrf}); }
function run(fn) { return async (event) => { event?.preventDefault(); try { await fn(); } catch (error) { notify(error.message); } }; }
$("username").addEventListener("input", () => { matched=""; $("send").disabled=true; $("target").textContent=""; });
$("resolve").onclick=run(async()=>{
  const result=await api(`/api/v1/public/contact/resolve?username=${encodeURIComponent($("username").value.trim())}`);
  matched=result.username; $("target").textContent=`收件人：${result.display_name}（@${matched}）`;
  $("send").disabled=false;
});
$("intro").onsubmit=run(async()=>{
  if (!matched) throw new Error("请先查找并确认收件人。");
  const draft={username:matched,sender_name:$("sender").value.trim(),subject:$("subject").value.trim(),body:$("body").value.trim()};
  if (payload && JSON.stringify(payload)!==JSON.stringify(draft)) throw new Error("上次投递结果尚不明确，请保持原内容重试，避免重复发送。");
  payload=draft;
  if (!proof) proof="gc_"+btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
  $("send").disabled=true;
  try {
    const result=await api("/api/v1/public/contact/requests","POST",payload,{Authorization:`Bearer ${proof}`});
    await api("/api/v1/contacts/guest-session", "POST", {token:proof}, {"X-AgentPost-Guest":"1"});
    notify(`${labels[result.status] || result.status}。本次投递不会直接启动 AI 执行。`);
    $("visitor").hidden=true; $("claim-panel").hidden=false;
  } finally { $("send").disabled=false; }
});
$("claim").onclick=run(async()=>{
  await guestSessionReady;
  const result=await mutate("/api/v1/contacts/claim", proof ? {token:proof} : {});
  proof=""; $("claim-panel").hidden=true;
  notify(labels[result.status] || result.status); await refresh();
});
$("preferences").onsubmit=run(async()=>{
  await mutate("/api/v1/contacts/preferences",{enabled:$("enabled").checked},"PUT"); notify("联系设置已保存。");
});
function render(items) {
  for (const item of items) {
    const article=document.createElement("article");
    const title=document.createElement("h2"); title.textContent=item.subject;
    const meta=document.createElement("p"); meta.className="meta";
    meta.textContent=`${item.incoming?"收到":"发出"} · ${item.sender_name}${item.sender_verified?"（已关联账号）":"（未注册访客，称呼未验证）"} → @${item.recipient_username} · ${new Date(item.created_at).toLocaleString()}`;
    const status=document.createElement("p"); status.textContent=labels[item.status]||item.status;
    const body=document.createElement("p"); body.className="content"; body.textContent=item.body;
    article.append(title,meta,status,body);
    function action(text,value) { const button=document.createElement("button");button.textContent=text;button.className="secondary";button.onclick=run(async()=>{button.disabled=true;try {await mutate(`/api/v1/contacts/${item.request_id}/decision`,{action:value});await refresh();}finally{button.disabled=false;}});article.append(button); }
    if (item.incoming && item.decision==="pending" && item.status!=="expired") {action("接受并建立后续协作","accept");action("不接受","decline");}
    if (item.status==="waiting_agents") {const a=document.createElement("a");a.href="/orbit?module=relay&view=agents";a.target="_blank";a.rel="noopener";a.textContent="连接并设置默认 AI ↗";article.append(a);action("已设置，继续建立任务","continue");}
    if (item.task_id) {const a=document.createElement("a");a.href=`/orbit?module=projects&view=board&task=${encodeURIComponent(item.task_id)}`;a.textContent="进入协作任务";article.append(a);}
    $("items").append(article);
  }
}
async function refresh() {
  const user=await session();
  $("account-state").textContent=`当前账号：${user.display_name || user.username}`; $("login").hidden=true; $("preferences").hidden=false;
  const pref=await api("/api/v1/contacts/preferences");$("enabled").checked=pref.enabled;
  $("account-state").textContent+=` · 公开用户名 @${pref.username}`;
  const list=await api("/api/v1/contacts"); $("items").replaceChildren();render(list.items);next=list.next_cursor;$("more").hidden=!next;
  if (!list.items.length) {const p=document.createElement("p");p.textContent="还没有首次联系请求。";$("items").append(p);}
}
$("refresh").onclick=run(refresh);
$("more").onclick=run(async()=>{if(!next)return;const list=await api(`/api/v1/contacts?before=${next}`);render(list.items);next=list.next_cursor;$("more").hidden=!next;});
refresh().catch(()=>{$("account-state").textContent="注册或登录后，可以管理收到的联系和接续已发送的内容。";});
