const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  inbox: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 13h5l2 3h4l2-3h5"/>',
  chart: '<path d="M4 20V10m6 10V4m6 16v-7m4 7V8"/>',
  rotate: '<path d="M3 11a9 9 0 1 1 2.5 6.2M3 17v-6h6"/>',
  truck: '<path d="M3 6h11v11H3zM14 9h4l3 3v5h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  wrench: '<path d="M14 7a5 5 0 0 0-6 6l-5 5a2 2 0 0 0 3 3l5-5a5 5 0 0 0 6-6l-3 3-3-3 3-3Z"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  back: '<path d="m15 18-6-6 6-6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  bolt: '<path d="m13 2-9 12h7l-1 8 10-12h-7l1-8"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  alert: '<path d="M12 3 2 21h20L12 3Zm0 7v4m0 3h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  sparkle: '<path d="m12 2 2.3 7.7L22 12l-7.7 2.3L12 22l-2.3-7.7L2 12l7.7-2.3L12 2Z"/>',
  send: '<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
  activity: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
};
const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.grid}</svg>`;
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const state = { view:'overview', domain:'All', query:'', caseId:null, caseTab:'overview', messageTab:'customer', cases:[], metrics:null, business:null, current:null };
const content = document.getElementById('content');
let toastTimer;

async function api(path, options={}) {
  const response = await fetch(path, { ...options, headers:{'Content-Type':'application/json',...(options.headers||{})} });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Something went wrong');
  return body;
}
const post = (path, body={}) => api(path, {method:'POST',body:JSON.stringify(body)});
function toast(message) {
  const node=document.getElementById('toast');node.textContent=message;node.classList.add('show');
  clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.classList.remove('show'),3500);
}
async function load() {
  try {
    [state.cases,state.metrics,state.business]=await Promise.all([api('/api/cases'),api('/api/metrics'),api('/api/business')]);
    if(state.caseId) state.current=await api('/api/cases/'+encodeURIComponent(state.caseId));
    render();
  } catch(error) { content.innerHTML=`<div class="empty">Could not reach the local demo server. ${escapeHTML(error.message)}<br><br><button class="button" data-action="reload">Try again</button></div>`; }
}
function navigate(view, domain='All') {
  state.view=view;state.domain=domain;state.caseId=null;state.current=null;state.query='';
  history.replaceState(null,'',view==='overview' ? '/' : '#'+view.toLowerCase());
  render();window.scrollTo({top:0,behavior:'smooth'});
}
async function openCase(id) {
  state.caseId=id;state.view='detail';state.caseTab='overview';state.messageTab='customer';
  content.innerHTML='<div class="empty">Opening investigation…</div>';
  try{state.current=await api('/api/cases/'+encodeURIComponent(id));render();window.scrollTo({top:0,behavior:'smooth'});}
  catch(error){toast(error.message);navigate('cases');}
}
function setNav() {
  const view=['detail','new'].includes(state.view)?'cases':state.view;
  document.querySelectorAll('[data-view]').forEach(node=>node.classList.toggle('active',node.dataset.view===view));
  document.getElementById('breadcrumb').textContent=state.view==='detail'?'Investigation':state.view==='new'?'New case':state.view==='analytics'?'Insights':state.view==='brand'?'Your brand':state.view==='cases'?'Cases':'Overview';
  document.getElementById('navCount').textContent=state.metrics?.active??0;
  const name=state.business?.name||'Your business';
  document.getElementById('workspaceName').textContent=name;
  document.getElementById('workspaceInitials').textContent=name.split(/\s+/).slice(0,2).map(word=>word[0]).join('').toUpperCase();
}
function heading(label,title,description,actions='') {return `<div class="page-heading"><div><div class="eyebrow">${label}</div><h1>${title}</h1><p>${description}</p></div>${actions?`<div class="heading-actions">${actions}</div>`:''}</div>`;}
function metric(label,value,foot,kind,glyph){return `<div class="metric-card"><div class="metric-head"><span>${label}</span><span class="metric-icon ${kind}">${icon(glyph)}</span></div><div class="metric-value">${value}</div><div class="metric-foot">${foot}</div></div>`;}
function caseIcon(domain){const kind=domain==='Music'?'music':domain==='Delivery'?'delivery':domain==='Service'?'service':'customer';return `<span class="case-icon ${kind}">${icon(domain==='Music'?'music':domain==='Delivery'?'truck':domain==='Service'?'wrench':'inbox')}</span>`;}
function badge(priority){return `<span class="badge ${escapeHTML(priority)}">${escapeHTML(priority)}</span>`;}
function row(c){return `<button class="case-row" data-case="${escapeHTML(c.id)}" aria-label="Open ${escapeHTML(c.account)} case">${caseIcon(c.domain)}<span class="case-summary"><strong>${escapeHTML(c.title)}</strong><small>${escapeHTML(c.account)} <span aria-hidden="true">·</span> ${escapeHTML(c.id)}</small></span><span class="case-right">${badge(c.priority)}<time>${escapeHTML(c.updated)}</time></span></button>`;}
function renderOverview(){
  const m=state.metrics;
  return heading('GOOD MORNING, JASIJAH','Your operations, in focus','A clear view of customer issues that need your attention.',`<button class="button subtle" data-action="reset">${icon('rotate')} Reset demo</button><button class="button primary" data-view="new">${icon('plus')} New case</button>`)+
    `<div class="metric-grid">${metric('Active cases',m.active,'Across all customer queues','blue','inbox')}${metric('Critical priority',m.critical,'Needs immediate attention','red','alert')}${metric('Resolved',m.resolved,'In this demo workspace','green','check')}${metric('Queues',3,'Partner operations + customer care','purple','activity')}</div>`+
    `<div class="panel-grid"><section class="panel"><div class="panel-header"><div><h2>Needs attention</h2><p>Prioritized customer conversations</p></div><button class="text-link" data-view="cases">View all ${icon('arrow')}</button></div>${state.cases.filter(c=>c.status!=='resolved').slice(0,3).map(row).join('')||'<div class="empty">All cases resolved.</div>'}</section>`+
    `<section class="panel"><div class="panel-header"><div><h2>Today’s focus</h2><p>One investigation at a time</p></div>${icon('sparkle')}</div><div class="focus-card"><span class="focus-overline">PRIORITY 01 · DELIVERY</span><h3>A completed delivery.<br>An outdated customer view.</h3><p>Follow the event trail to find where MetroMart’s status update stopped.</p><button class="button primary" data-case="SD-1042">Investigate case ${icon('arrow')}</button><div class="focus-stat"><span><strong>82</strong><small>orders affected</small></span><span><strong>504</strong><small>callback timeout</small></span></div></div><div class="scenario-list"><button class="scenario" data-case="SD-1043">${caseIcon('Music')}<span><strong>Explore music distribution</strong><small>Investigate a rejected release payload</small></span><span class="scenario-arrow">→</span></button><button class="scenario" data-case="SD-1046">${caseIcon('Service')}<span><strong>Explore a service follow-up</strong><small>SMS complaint and payment note</small></span><span class="scenario-arrow">→</span></button><button class="scenario" data-case="SD-1047">${caseIcon('Commerce')}<span><strong>Explore retail support</strong><small>Damaged order reported through web chat</small></span><span class="scenario-arrow">→</span></button></div></section></div>`;
}
function renderCases(){
  const filtered=state.cases.filter(c=>(state.domain==='All'||(state.domain==='Partner'?['Delivery','Music'].includes(c.domain):state.domain==='Customer'?!['Delivery','Music'].includes(c.domain):c.domain===state.domain))&&(!state.query||`${c.title} ${c.account} ${c.id} ${c.subtitle}`.toLowerCase().includes(state.query.toLowerCase())));
  return heading('CASE WORKSPACE','Customer cases','Email, text, chat, social and partner alerts in one organized queue.',`<button class="button primary" data-view="new">${icon('plus')} New case</button>`)+
    `<div class="list-toolbar"><div class="segmented" aria-label="Filter by workflow">${['All','Partner','Customer'].map(d=>`<button data-filter="${d}" class="${state.domain===d?'selected':''}">${d==='All'?'All cases':d}</button>`).join('')}</div><label class="search">${icon('search')}<input id="caseSearch" type="search" placeholder="Search cases or accounts" value="${escapeHTML(state.query)}" aria-label="Search cases"></label></div>`+
    `<section class="panel"><div class="panel-header"><div><h2>${state.domain==='All'?'All conversations':state.domain+' cases'}</h2><p>${filtered.length} fictional case${filtered.length===1?'':'s'} · live demo state</p></div></div>${filtered.map(c=>`<button class="full-case" data-case="${escapeHTML(c.id)}">${caseIcon(c.domain)}<span><h3>${escapeHTML(c.title)}</h3><p>${escapeHTML(c.account)} · ${escapeHTML(c.id)} · ${escapeHTML(c.channel||'Partner API')}</p></span><span class="case-meta">${badge(c.priority)}<small>${escapeHTML(c.status)} · ${escapeHTML(c.updated)}</small></span></button>`).join('')||'<div class="empty">No cases match this search.</div>'}</section>`;
}
function trace(c){return `<div class="trace-list">${c.events.map(e=>`<div class="trace-item"><span class="trace-symbol ${escapeHTML(e.tone)}">${e.tone==='success'?'✓':e.tone==='warning'?'!':'×'}</span><div class="trace-copy"><strong>${escapeHTML(e.title)}</strong><small>${escapeHTML(e.time)}</small><p>${escapeHTML(e.detail)} · ${escapeHTML(e.source)}</p></div><span class="trace-code ${escapeHTML(e.tone)}">${escapeHTML(e.code)}</span></div>`).join('')}</div>`;}
function diagnosis(c){const d=c.diagnosis;return d?`<div class="finding"><div class="finding-label">CONFIRMED FINDING</div><h3>${escapeHTML(d.label)}</h3><span class="confidence">● ${escapeHTML(d.confidence)}</span><p>${escapeHTML(d.cause)}</p><strong style="font-size:11px">Recommended next step</strong><p>${escapeHTML(d.action)}</p><ul class="evidence">${d.evidence.map(e=>`<li>${escapeHTML(e)}</li>`).join('')}</ul>${c.kind==='callback_timeout'?`<div style="margin-top:16px"><button class="button primary" data-action="replay" ${c.replayed?'disabled':''}>${icon('rotate')} ${c.replayed?'Replay acknowledged':'Simulate replay'}</button></div>`:''}</div>`:`<div class="diagnostic-empty"><div class="circle-icon">${icon('sparkle')}</div><strong>Connect the signals</strong><p>Check the event sequence and surface a trace-based finding.</p><button class="button primary" data-action="diagnose">${icon('activity')} Run diagnostics</button></div>`;}
function message(c, audience){
  const d=c.diagnosis;
  if(audience==='engineering') return `Case ${c.id} · ${c.account}\nRequest ID: ${c.request_id}\nPriority: ${c.priority}\n\nObserved: ${d?d.cause:'Investigation pending. See event trace for observed behavior.'}\n\nEvidence: ${d?d.evidence.join('; '):c.events.filter(e=>e.tone==='error').map(e=>e.code+' '+e.detail).join('; ')||'No error event recorded.'}\n\nNext step: ${d?d.action:'Run diagnostics, confirm the failure, and attach the request trace.'}`;
  if(c.kind==='callback_timeout') return `Hi MetroMart team,\n\nWe confirmed that the dropoffs were completed and their proof of delivery is safely recorded. The status update sent to your system timed out, which is why your order page still shows “picked up.”\n\n${c.replayed?'We replayed the original update and received a successful acknowledgement. Please confirm that the delivered status now appears on your side.':'We are validating a safe replay of the original update and will confirm once your system acknowledges it.'}\n\nWe’ll keep this case open until the status is verified together.\n\n— Partner Support`;
  if(c.kind==='metadata_rejection') return `Hi Northstar team,\n\nWe found why the release is missing from the partner catalog. The files were sent, but the partner rejected a metadata value on Track 07. The “delivered” label reflected dispatch, not final acceptance.\n\nWe are correcting the field and will confirm the partner’s acceptance before treating this as complete. We’ll share the next update as soon as validation finishes.\n\n— Distribution Operations`;
  if(c.domain==='Service') return `Hi ${c.account},\n\nThanks for reaching out about ${c.kind==='manual_intake'?'your service request':'the car not starting after the visit'}. I have your concern recorded and will follow up to confirm the details and agree on the next step.\n\n${c.tags.includes('payment reported')?'You mentioned a Cash App payment; I will check the payment record directly before confirming it.':'If payment is relevant, I will verify it separately before confirming its status.'}\n\n— Your service provider`;
  if(!['Delivery','Music'].includes(c.domain)) return `Hi ${c.account},\n\nThanks for reaching out about ${c.title}. We have your message and will review the details before confirming the next step.\n\n${d?d.action:'We will follow up through this business channel.'}\n\n— Customer Care`;
  return `Hi ${c.account} team,\n\nWe’ve reviewed your report and are tracing the relevant partner events. ${d?d.cause:'We will confirm what happened before recommending a fix.'}\n\n${d?d.action:'We will send a clear update once the investigation is complete.'}\n\n— Partner Support`;
}
function renderDetail(){const c=state.current;if(!c)return '<div class="empty">Loading case…</div>';
  const actions=`<button class="button" data-action="copy-id">${icon('copy')} Copy request ID</button><button class="button primary" data-tab="communications">${icon('send')} Draft update</button>`;
  let body;
  if(state.caseTab==='trace')body=`<div class="section"><h3>Event trace</h3><p class="diagnostic-intro">Read the sequence before drawing a conclusion. All timestamps and events are fictional.</p>${trace(c)}<div class="notice">Request ID ${escapeHTML(c.request_id)} · This view represents a simulated partner integration.</div></div>`;
  else if(state.caseTab==='communications'){const text=message(c,state.messageTab);body=`<div class="section"><h3>Customer communication</h3><p class="diagnostic-intro">A starting draft based on the case record. Review and edit before sending through your own channel.</p><div class="segmented" style="display:inline-flex;margin-bottom:16px"><button data-message="customer" class="${state.messageTab==='customer'?'selected':''}">Customer update</button><button data-message="engineering" class="${state.messageTab==='engineering'?'selected':''}">Engineering handoff</button></div><div class="message-card" id="messageText">${escapeHTML(text)}</div><div class="copy-row"><button class="button primary" data-action="copy-message">${icon('copy')} Copy draft</button></div></div>`;}
  else body=`<div class="section"><h3>What the customer reported</h3><div class="quote">“${escapeHTML(c.customer)}”</div></div><hr class="section-divider"><div class="section"><h3>Event timeline</h3>${trace({...c,events:c.events.slice(-4)})}<button class="text-link" data-tab="trace">Explore full trace →</button></div><hr class="section-divider"><div class="section"><h3>Diagnostic assessment</h3>${diagnosis(c)}</div>`;
  return `<div class="detail-top"><button class="back-button" data-view="cases">${icon('back')} All cases</button><span class="detail-id">${escapeHTML(c.id)} / ${escapeHTML(c.domain)} operations</span></div>`+
    `<div class="page-heading detail-heading"><div><div class="eyebrow">${escapeHTML(c.account.toUpperCase())} · ${escapeHTML(c.domain.toUpperCase())}</div><h1>${escapeHTML(c.title)}</h1><div class="detail-subline">${badge(c.priority)} <span>${escapeHTML(c.channel||'Partner API')}</span><span class="sep">·</span><span>Updated ${escapeHTML(c.updated)}</span></div></div><div class="heading-actions">${actions}</div></div>`+
    `<div class="detail-layout"><section class="panel"><div class="tabbar" role="tablist" aria-label="Case details">${[['overview','Overview'],['trace','Event trace'],['communications','Communication']].map(([key,label])=>`<button role="tab" aria-selected="${state.caseTab===key}" data-tab="${key}" class="${state.caseTab===key?'active':''}">${label}</button>`).join('')}</div>${body}</section>`+
    `<aside class="panel side-panel"><div class="side-section"><h3>Case details</h3><div class="info-line"><span>Case ID</span><strong>${escapeHTML(c.id)}</strong></div><div class="info-line"><span>Account</span><strong>${escapeHTML(c.account)}</strong></div><div class="info-line"><span>Channel</span><strong>${escapeHTML(c.channel||'Partner API')}</strong></div><div class="info-line"><span>Owner</span><strong>${escapeHTML(c.owner)}</strong></div><div class="info-line"><span>Status</span><select class="status-select" id="statusSelect" aria-label="Case status">${['open','investigating','resolved'].map(s=>`<option value="${s}" ${s===c.status?'selected':''}>${s[0].toUpperCase()+s.slice(1)}</option>`).join('')}</select></div><div class="info-line"><span>SLA</span><strong>${escapeHTML(c.sla)}</strong></div></div><div class="side-section"><h3>Impact</h3><p style="font-size:12px;color:#51607a;margin:0 0 14px">${escapeHTML(c.impact)}</p><div class="tag-list">${c.tags.map(t=>`<span class="tag">${escapeHTML(t)}</span>`).join('')}</div></div><div class="side-section"><h3>Internal notes</h3><form class="note-form" id="noteForm"><input name="body" maxlength="500" placeholder="Add an investigation note" aria-label="Internal note" required><button aria-label="Save note">${icon('plus')}</button></form>${c.notes.length?c.notes.map(n=>`<div class="note">${escapeHTML(n.body)}<small>${escapeHTML(n.created)} · local demo</small></div>`).join(''):'<p style="font-size:10px;color:#a0abba">No notes yet.</p>'}</div></aside></div>`;
}
function renderInsights(){const m=state.metrics,all=state.cases.length,percent=n=>Math.round(n/Math.max(all,1)*100);return heading('WORKFLOW INTELLIGENCE','A clearer view of the work','A small, honest snapshot of this fictional demo dataset.')+
  `<div class="metric-grid">${metric('Total cases',all,'Fictional seed records','blue','inbox')}${metric('Delivery queue',m.delivery,'Currently active','blue','truck')}${metric('Customer queue',m.customer,'Currently active','purple','inbox')}${metric('Resolved',m.resolved,'In this session','green','check')}</div>`+
  `<div class="insight-grid"><section class="panel"><div class="panel-header"><div><h2>Case mix</h2><p>Across partner and customer queues</p></div></div><div class="section">${[['Partner',''],['Customer','purple']].map(([domain,color])=>`<div class="bar-row"><span>${domain}</span><div class="bar-track"><div class="bar-fill ${color}" style="width:${percent(state.cases.filter(c=>domain==='Partner'?['Delivery','Music'].includes(c.domain):!['Delivery','Music'].includes(c.domain)).length)}%"></div></div><strong>${state.cases.filter(c=>domain==='Partner'?['Delivery','Music'].includes(c.domain):!['Delivery','Music'].includes(c.domain)).length}</strong></div>`).join('')}</div></section><section class="panel"><div class="panel-header"><div><h2>What to look for</h2><p>Different intake, same clear follow-up</p></div></div><div class="section"><div class="insight-callout"><strong>Delivery:</strong> Compare an internal completion with the failed outbound callback.<br><br><strong>Music:</strong> Distinguish payload dispatch from partner acceptance.<br><br><strong>Customer care:</strong> Track a repair complaint or retail replacement request, verify the details, and send a clear follow-up.</div></div></section></div>`;}
function renderNew(){return `<div class="detail-top"><button class="back-button" data-view="cases">${icon('back')} All cases</button><span class="detail-id">UNIFIED INBOX DEMO</span></div>`+heading('CUSTOMER INBOX','Capture a customer request','Organize questions, complaints, orders, bookings, and follow-ups in one business workspace.')+`<section class="panel"><form class="intake-form" id="intakeForm"><label>Customer name<input name="account" maxlength="200" minlength="2" placeholder="e.g. Avery Brooks" required></label><label>Where did it arrive?<select name="channel"><option>Email</option><option>SMS</option><option>Web chat</option><option>Social DM</option><option>Private form</option><option>Phone note</option></select></label><label>What is this about?<input name="subject" maxlength="200" minlength="2" placeholder="e.g. Replacement for a damaged order" required></label><label>Type of request<select name="category"><option>Request</option><option>Complaint</option><option>Order issue</option><option>Appointment</option><option>Billing</option><option>Other</option></select></label><label>Customer message<textarea name="issue" maxlength="200" minlength="2" placeholder="Capture the request or complaint in their words" required></textarea></label><label>Payment context<select name="payment"><option>Not discussed</option><option>Unpaid</option><option>Customer reports paid</option><option>Owner verified paid</option></select></label><p class="form-hint">This local demo simulates channel intake. It does not receive real texts, email, chats, or social DMs, or verify Cash App payments. A production version would connect a dedicated business number and inbox.</p><button class="button primary" type="submit">${icon('plus')} Create case</button></form><div class="side-section"><strong style="font-size:12px">Move complaints off social media</strong><p class="diagnostic-intro" style="margin:8px 0">Reply with a private request link so the customer can explain the issue away from a public comment thread.</p><a class="button" href="/intake.html" target="_blank" rel="noopener">Preview customer form →</a></div></section>`;}
function renderBrand(){const b=state.business||{name:'Your business',tagline:'Thoughtful service, every time.',accent:'#3567e9',industry:'Any business'};return heading('YOUR FRONT DESK','Make it feel like your business','A polished request page gives customers a private place to ask for help.')+`<div class="brand-layout"><section class="panel"><div class="panel-header"><div><h2>Business identity</h2><p>Three simple details, no full website required</p></div></div><form class="intake-form" id="brandForm"><label>Business name<input name="name" maxlength="50" minlength="2" value="${escapeHTML(b.name)}" required></label><label>Short welcome line<input name="tagline" maxlength="100" value="${escapeHTML(b.tagline)}" placeholder="Thoughtful service, every time."></label><label>Business type<select name="industry">${['Any business','Retail','Services','Beauty','Auto','Device repair','Studio','Agency','Professional services','Creator','Other'].map(v=>`<option ${v===b.industry?'selected':''}>${v}</option>`).join('')}</select></label><fieldset class="color-picker"><legend>Signature color</legend>${[['#3567e9','Blue'],['#885ec7','Violet'],['#187e76','Teal'],['#b9744e','Copper']].map(([color,label])=>`<label><input type="radio" name="accent" value="${color}" ${color===b.accent?'checked':''}><span style="background:${color}"></span><small>${label}</small></label>`).join('')}</fieldset><button class="button primary" type="submit">Save business page</button></form></section><section class="panel brand-preview-panel"><div class="panel-header"><div><h2>Customer view</h2><p>Preview your private request page</p></div></div><div class="brand-preview"><div class="preview-mark" style="background:${b.accent}">${escapeHTML(b.name.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase())}</div><small>WELCOME TO</small><h2>${escapeHTML(b.name)}</h2><p>${escapeHTML(b.tagline||'How can we help you today?')}</p><div class="preview-input">Your name</div><div class="preview-input">How can we help?</div><span class="preview-button" style="background:${b.accent}">Send request →</span></div><div class="side-section"><a class="button" href="/intake.html" target="_blank" rel="noopener">Open customer page ↗</a><p class="form-hint" style="margin:12px 0 0">This preview runs locally. Hosting, a custom domain, and real messaging connectors are future production steps.</p></div></section></div>`;}
function render(){setNav();content.innerHTML=state.view==='detail'?renderDetail():state.view==='cases'?renderCases():state.view==='new'?renderNew():state.view==='analytics'?renderInsights():state.view==='brand'?renderBrand():renderOverview();}

document.querySelectorAll('[data-icon]').forEach(node=>node.innerHTML=icon(node.dataset.icon));
document.addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.case){return openCase(button.dataset.case);}
  if(button.dataset.domain){return navigate('cases',button.dataset.domain);}
  if(button.dataset.view){return navigate(button.dataset.view);}
  if(button.dataset.filter){state.domain=button.dataset.filter;return render();}
  if(button.dataset.tab){state.caseTab=button.dataset.tab;return render();}
  if(button.dataset.message){state.messageTab=button.dataset.message;return render();}
  const action=button.dataset.action;
  if(!action)return;
  try{
    if(action==='reload')return load();
    if(action==='reset'){if(!confirm('Reset all fictional cases and notes to their original state?'))return;await post('/api/reset');state.caseId=null;state.view='overview';toast('Demo restored');return load();}
    if(action==='copy-id'){await navigator.clipboard.writeText(state.current.request_id);return toast('Request ID copied');}
    if(action==='copy-message'){await navigator.clipboard.writeText(message(state.current,state.messageTab));return toast('Draft copied. Review before sending.');}
    if(action==='diagnose'||action==='replay'){
      button.disabled=true;state.current=await post(`/api/cases/${state.caseId}/${action}`);
      toast(action==='diagnose'?'Diagnostic finding ready':'Simulated callback acknowledged');
      await load();return;
    }
  }catch(error){button.disabled=false;toast(error.message);}
});
document.getElementById('resetButton').addEventListener('click',resetFromHeader);
async function resetFromHeader(){if(!confirm('Reset all fictional cases and notes to their original state?'))return;try{await post('/api/reset');state.caseId=null;state.view='overview';toast('Demo restored');await load();}catch(error){toast(error.message);}}
document.addEventListener('change',async event=>{if(event.target.id==='statusSelect'){try{state.current=await post(`/api/cases/${state.caseId}/status`,{status:event.target.value});toast('Case status updated');await load();}catch(error){toast(error.message);}}});
document.addEventListener('submit',async event=>{if(event.target.id==='noteForm'){event.preventDefault();const note=new FormData(event.target).get('body');try{state.current=await post(`/api/cases/${state.caseId}/notes`,{body:note});toast('Internal note saved');render();}catch(error){toast(error.message);}return;}
  if(event.target.id==='brandForm'){event.preventDefault();const data=Object.fromEntries(new FormData(event.target));try{state.business=await post('/api/business',data);toast('Business page updated');render();}catch(error){toast(error.message);}return;}
  if(event.target.id==='intakeForm'){event.preventDefault();const data=Object.fromEntries(new FormData(event.target));try{const created=await post('/api/cases',data);toast('Case created from phone intake');await load();await openCase(created.id);}catch(error){toast(error.message);}}});
document.addEventListener('input',event=>{if(event.target.id==='caseSearch'){const position=event.target.selectionStart;state.query=event.target.value;render();const input=document.getElementById('caseSearch');input.focus();input.setSelectionRange(position,position);}});
load();
