"use strict";
const $ = (id) => document.getElementById(id);
const publicUsername=new URLSearchParams(location.search).get("to") || "";
let proof = new URLSearchParams(location.hash.slice(1)).get("claim") || "";
// Never persist bearer proof in storage, cookies, query parameters or request logs.
history.replaceState(null, "", publicUsername ? `/contact?to=${encodeURIComponent(publicUsername)}` : "/contact");
if (!/^gc_[A-Za-z0-9_-]{43}$/.test(proof)) proof = "";
$("claim-panel").hidden = !proof;
$("visitor").hidden = !!proof;
let matched = "", csrf = "", next = null, payload = null;
const guestSessionReady = (async () => {
  if (proof) await api("/api/v1/contacts/guest-session", "POST", {token:proof}, {"X-AgentPost-Guest":"1"});
  const pending = await api("/api/v1/contacts/guest-session");
  $("claim-panel").hidden = !pending.pending_claim;
  if (pending.pending_claim) {
    $("visitor").hidden = true;
    $("guest-status").textContent=labels[pending.receipt.status] || pending.receipt.status;
    $("guest-reply").hidden=!pending.receipt.reply;
    $("guest-reply").textContent=pending.receipt.reply || "";
  }
  if (pending.expired) notify("接续链接已过期，无法再认领；已关联账号的联系可登录后查看。");
})().catch(error => notify(error.message));
const labels = {waiting_recipient:"联系已提交，等待对方处理",waiting_registration:"已接受，等待发送方注册并关联",waiting_agents:"已关联，双方需连接并设置默认 AI 后继续",task_created:"已建立协作任务",declined:"未接受",expired:"已过期",claimed:"已关联到账号",replied:"对方已回复，登录后可申请进一步协作"};
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
  matched=result.username; $("target").textContent=`收件人：${result.display_name}（@${matched}） ${result.introduction || ""}`;
  $("send").disabled=false;
});
$("intro").onsubmit=run(async()=>{
  if (!matched) throw new Error("请先查找并确认收件人。");
  const draft={username:matched,sender_name:$("sender").value.trim(),subject:$("subject").value.trim(),body:$("body").value.trim(),intent:$("intent").value};
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
  await mutate("/api/v1/contacts/preferences",{enabled:$("enabled").checked,introduction:$("introduction").value.trim()},"PUT"); notify("联系设置已保存。"); await refresh();
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
    if(item.reply) {const reply=document.createElement("blockquote");reply.className="content";reply.textContent=`对方回复：${item.reply}`;article.append(reply);}
    if(item.reported) {const p=document.createElement("p");p.textContent="举报已记录，本次联系已屏蔽。";article.append(p);}
    function action(text,value) { const button=document.createElement("button");button.textContent=text;button.className="secondary";button.onclick=run(async()=>{button.disabled=true;try {await mutate(`/api/v1/contacts/${item.request_id}/decision`,{action:value});await refresh();}finally{button.disabled=false;}});article.append(button); }
    if (item.incoming && item.decision==="pending" && item.status!=="expired" && !item.blocked) {
      if(item.intent==="collaboration") action("接受并开始协作","accept");
      if(!item.reply) {
        const form=document.createElement("form");form.className="reply-form";
        const label=document.createElement("label");label.textContent="回复一次（不会添加好友或创建任务）";
        const input=document.createElement("textarea");input.required=true;input.maxLength=10000;label.append(input);
        const button=document.createElement("button");button.textContent="发送回复";
        form.append(label,button);form.onsubmit=run(async()=>{button.disabled=true;try{await mutate(`/api/v1/contacts/${item.request_id}/decision`,{action:"reply",body:input.value});await refresh();}finally{button.disabled=false;}});
        article.append(form);
      }
      action("不接受","decline");action("屏蔽本次联系","block");action("举报并屏蔽本次联系","report");
    }
    if(item.next_action==="request_collaboration") action("申请好友并发起首次协作","request_collaboration");
    if (item.next_action==="setup_agent") {const a=document.createElement("a");a.href="/orbit?module=relay&view=agents";a.target="_blank";a.rel="noopener";a.textContent="连接并设置默认 AI ↗";article.append(a);action("已设置，继续建立任务","continue");}
    if (item.task_id) {const a=document.createElement("a");a.href=`/orbit?module=projects&view=board&task=${encodeURIComponent(item.task_id)}`;a.textContent="进入协作任务";article.append(a);}
    $("items").append(article);
  }
}
async function refresh() {
  const user=await session();
  $("account-state").textContent=`当前账号：${user.display_name || user.username}`; $("login").hidden=true; $("preferences").hidden=false;
  const pref=await api("/api/v1/contacts/preferences");$("enabled").checked=pref.enabled;
  $("introduction").value=pref.introduction || ""; $("share").hidden=!pref.enabled;
  $("share-link").value=`${location.origin}/contact?to=${encodeURIComponent(pref.username)}`;
  if(pref.enabled) $("share-qr").src=`/api/v1/public/contact/qr?username=${encodeURIComponent(pref.username)}`;
  $("account-state").textContent+=` · 公开用户名 @${pref.username}`;
  const list=await api("/api/v1/contacts");
  for(let i=0;i<list.items.length;i++) {
    const item=list.items[i];
    if(item.intent==="collaboration" && item.status==="waiting_agents")
      list.items[i]=await api(`/api/v1/contacts/${item.request_id}/decision`,"POST",{action:"continue"},{"X-CSRF-Token":csrf});
  }
  $("items").replaceChildren();render(list.items);next=list.next_cursor;$("more").hidden=!next;
  if (!list.items.length) {const p=document.createElement("p");p.textContent="还没有首次联系请求。";$("items").append(p);}
}
$("refresh").onclick=run(refresh);
$("more").onclick=run(async()=>{if(!next)return;const list=await api(`/api/v1/contacts?before=${next}`);render(list.items);next=list.next_cursor;$("more").hidden=!next;});
$("copy-link").onclick=run(async()=>{try{await navigator.clipboard.writeText($("share-link").value);notify("公开联系链接已复制。");}catch{$("share-link").select();notify("请复制已选中的公开联系链接。");}});
$("intent").onchange=()=>{$("send").textContent=$("intent").value==="collaboration"?"申请好友并发起首次协作":"发送首次联系";$("intent-note").textContent=$("intent").value==="collaboration"?"对方接受且双方完成接入后，将建立好友关系和一个任务。":"对方可以回复一次。注册或登录后，可申请进一步协作。";};
if(publicUsername) {$("username").value=publicUsername;$("resolve").click();}
window.addEventListener("focus",()=>{refresh().catch(()=>{});});
refresh().catch(()=>{$("account-state").textContent="注册或登录后，可以管理收到的联系和接续已发送的内容。";});
