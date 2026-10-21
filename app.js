const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ICONS={
 pin:'<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/>',
 database:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
 alert:'<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
 cloud:'<line x1="16" y1="13" x2="16" y2="21"/><line x1="8" y1="13" x2="8" y2="21"/><line x1="12" y1="15" x2="12" y2="23"/><path d="M20 16.58A5 5 0 0018 7h-1.26A8 8 0 104 15.25"/>',
 map:'<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>',
 home:'<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
 chart:'<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
 layers:'<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
 book:'<path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>',
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>',
 play:'<polygon points="6 3 20 12 6 21 6 3"/>',
 back:'<polyline points="15 18 9 12 15 6"/>',
 user:'<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
 check:'<polyline points="20 6 9 17 4 12"/>',
 bell:'<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>',
 siren:'<path d="M7 18v-6a5 5 0 0110 0v6"/><path d="M5 21h14"/><path d="M12 3V2M4.2 6.2l-.7-.7M19.8 6.2l.7-.7M2 12H1M23 12h-1"/>',
 chev:'<polyline points="9 18 15 12 9 6"/>'};
const ic=(n,s=22,c="#fff",f="none")=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="${f}" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n]}</svg>`;
function hydrateIcons(root=document){$$('[data-ic]',root).forEach(e=>{const s=+(e.dataset.size||18);e.innerHTML=ic(e.dataset.ic,s,e.dataset.color||"#fff",e.dataset.fill||"none");if(e.dataset.bg)e.style.background=e.dataset.bg;});}
const COL={Low:"#34c759",Medium:"#ff9500",High:"#ff3b30"};
const S={loc:null,places:[],ds:null,train:null,chosen:null,tgt:null,mapping:{},feats:[],riskFor:null,map:null,lg:null,cfg:null};

const apiBase=()=>(localStorage.getItem("fs_api")||window.FS_DEFAULT_API||"").replace(/\/+$/,"");
async function api(url,opt={}){const r=await fetch(url.startsWith("/")?apiBase()+url:url,opt);let j=null;try{j=await r.json()}catch(e){}
 if(!r.ok)throw new Error(j&&j.detail?(typeof j.detail==="string"?j.detail:JSON.stringify(j.detail)):`Request failed (${r.status})`);return j;}
const post=(u,b)=>api(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
const upload=(u,f)=>{const fd=new FormData();fd.append("file",f);return api(u,{method:"POST",body:fd});};
let tt;function toast(msg,kind="ok"){const t=$("#toast");t.innerHTML=`<span>${kind==="err"?"⚠️":"✅"}</span><span>${esc(msg)}</span>`;t.classList.add("show");clearTimeout(tt);tt=setTimeout(()=>t.classList.remove("show"),kind==="err"?5200:2800);}
async function run(btn,fn){const h=btn.innerHTML;btn.disabled=true;btn.textContent="Working…";try{return await fn()}catch(e){toast(e.message,"err")}finally{btn.disabled=false;btn.innerHTML=h;hydrateIcons(btn)}}
const runPlain=async fn=>{try{return await fn()}catch(e){toast(e.message,"err")}};
const km=(a,b,c,d)=>{const R=6371,r=x=>x*Math.PI/180,h=Math.sin(r(c-a)/2)**2+Math.cos(r(a))*Math.cos(r(c))*Math.sin(r(d-b)/2)**2;return 2*R*Math.asin(Math.sqrt(h))};

/* ---------- navigation ---------- */
function tab(n){$$(".tab").forEach(t=>t.classList.toggle("active",t.id==="tab-"+n));$$(".tabbar button").forEach(b=>b.classList.toggle("on",b.dataset.tab===n));window.scrollTo(0,0);
 if(n==="map"){initMap();setTimeout(()=>S.map.invalidateSize(),60);}if(n==="insights")renderInsights();}
$$(".tabbar button").forEach(b=>b.onclick=()=>tab(b.dataset.tab));
const openScr=id=>{if(id==="risk")buildRisk();$("#scr-"+id).classList.add("open");$("#scr-"+id).scrollTop=0;};
const closeScr=id=>$("#scr-"+id).classList.remove("open");
$$("[data-close]").forEach(b=>b.onclick=()=>closeScr(b.dataset.close));
function openSheet(html){$("#sheetBody").innerHTML=html;hydrateIcons($("#sheet"));$("#sheet").scrollTop=0;$("#sheet").classList.add("open");$("#backdrop").classList.add("open");}
function closeSheet(){$("#sheet").classList.remove("open");$("#backdrop").classList.remove("open");}
$("#backdrop").onclick=closeSheet;
document.addEventListener("click",e=>{const b=e.target.closest(".seg button");if(!b)return;const seg=b.parentElement;$$("button",seg).forEach(x=>x.classList.toggle("on",x===b));seg.dataset.value=b.dataset.v;seg.dispatchEvent(new Event("change"));});

/* ---------- home ---------- */
const TILES=[
 {n:"Set Region",s:"Any place",i:"pin",c:["#5ac8fa","#007aff"],a:()=>openScr("region")},
 {n:"Load Data",s:"Any CSV",i:"database",c:["#7ee08a","#2fb350"],a:()=>openScr("data")},
 {n:"Check Flood Risk",s:"Run",i:"alert",c:["#ff9f0a","#ff3b30"],a:()=>openScr("risk")},
 {n:"Live Weather",s:"Rain & forecast",i:"cloud",c:["#64d2ff","#2aa5c0"],a:weatherSheet},
 {n:"Govt Safe Houses",s:"Nearby shelters",i:"home",c:["#7d7aff","#5856d6"],a:placesSheet},
 {n:"Alerts",s:"Auto notifications",i:"bell",c:["#ff8a65","#e8431f"],a:()=>{openScr("alerts");renderAlerts()}},
 {n:"SOS Dispatch",s:"Nearest stations",i:"siren",c:["#ff5e57","#c4122f"],a:()=>{openScr("sos");renderSOS()}},
 {n:"Batch Risk Map",s:"Many areas",i:"layers",c:["#da8fff","#af52de"],a:()=>openScr("batch")},
 {n:"Model Insights",s:"Accuracy & recall",i:"chart",c:["#ff6482","#ff2d55"],a:()=>tab("insights")},
 {n:"Emergency Guide",s:"What to do",i:"book",c:["#ffd60a","#ff9500"],a:guideSheet}];
$("#tiles").innerHTML=TILES.map((t,i)=>`<button class="tile" data-i="${i}" style="--c1:${t.c[0]};--c2:${t.c[1]}"><div class="top">${ic(t.i,28)}<span class="dots">•••</span></div><div><div class="name">${t.n}</div><div class="ts">${t.s}</div></div></button>`).join("");
$$(".tile").forEach(b=>b.onclick=()=>TILES[+b.dataset.i].a());
function renderStatus(){
 const rows=[["Region",S.loc?S.loc.name:"Not set",!!S.loc,"region"],["Dataset",S.ds?`${S.ds.name} · ${S.ds.rows} rows`:"None loaded",!!S.ds,"data"],["Model",S.train?`${S.chosen}`:"Not trained",!!S.train,"data"],["Safe places",S.places.length?`${S.places.filter(p=>p.govt).length} govt · ${S.places.length} total`:"None",S.places.length>0,"region"],
  ["Alerts",S.cfg?`${S.cfg.subscribers.length} subscribers · ${S.cfg.live?"LIVE":"simulation"}`:"…",!!(S.cfg&&S.cfg.subscribers.length),"alerts"],
  ["SOS",S.cfg?`${S.cfg.settings.auto_sos?"Auto":"Manual"} · ${S.cfg.live?"LIVE":"simulation"}`:"…",!!(S.cfg&&S.cfg.settings.auto_sos),"sos"],
  ["Server",apiBase()||"This device",true,"server"],
  ["App",appState(),isStandalone(),"install"]];
 $("#status").innerHTML=rows.map(r=>`<div class="row" data-go="${r[3]}" style="cursor:pointer"><label><span class="dot ${r[2]?"on":""}"></span>${r[0]}</label><span class="val">${esc(r[1])}</span></div>`).join("");
 $$("#status .row").forEach(r=>r.onclick=()=>statusGo(r.dataset.go));}

/* ---------- region ---------- */
$("#rad").oninput=e=>$("#radV").textContent=e.target.value+" km";
$("#srcSeg").onchange=()=>$("#csvBox").style.display=$("#srcSeg").dataset.value==="csv"?"block":"none";
async function getPos(){
 const G=nat("Geolocation");
 if(G){try{await G.requestPermissions()}catch(e){}const p=await G.getCurrentPosition({enableHighAccuracy:true,timeout:12000});return{lat:p.coords.latitude,lon:p.coords.longitude};}
 if(!navigator.geolocation)throw new Error("Location is not available here.");
 return new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(p=>res({lat:p.coords.latitude,lon:p.coords.longitude}),()=>rej(new Error("Location permission denied.")),{enableHighAccuracy:true,timeout:12000}));}
$("#geoBtn").onclick=async()=>{try{const p=await getPos();$("#lat").value=p.lat.toFixed(5);$("#lon").value=p.lon.toFixed(5);$("#q").value="";toast("Location filled in.");}catch(e){toast(e.message||"Could not get location.","err")}};
$("#regionBtn").onclick=e=>run(e.currentTarget,async()=>{
 const src=$("#srcSeg").dataset.value,file=$("#shelterFile").files[0];
 if(src==="csv"&&!file)throw new Error("Choose a shelters CSV first.");
 let r=await post("/api/region",{query:$("#q").value,lat:+$("#lat").value,lon:+$("#lon").value,radius:+$("#rad").value,source:src==="csv"?"none":src});
 S.loc=r.loc;S.places=r.places;
 if(src==="csv"){const u=await upload("/api/places/upload",file);S.places=u.places;}
 $("#lat").value=S.loc.lat.toFixed(5);$("#lon").value=S.loc.lon.toFixed(5);
 renderStatus();try{drawPlaces(true)}catch(e){console.warn(e)}closeScr("region");
 r.warning?toast(r.warning,"err"):toast(`Region set · ${S.places.length} safe places`);});

/* ---------- data & training ---------- */
$("#dsSeg").onchange=()=>{const d=$("#dsSeg").dataset.value==="demo";$("#upBox").style.display=d?"none":"block";$("#demoBox").style.display=d?"block":"none";};
$("#demoBtn").onclick=e=>run(e.currentTarget,async()=>onDataset(await api("/api/dataset/demo",{method:"POST"})));
$("#dataFile").onchange=e=>{const f=e.target.files[0];if(f)runPlain(async()=>onDataset(await upload("/api/dataset/upload",f)));};
async function onDataset(d){
 S.ds={name:d.name,rows:d.rows};S.train=null;S.chosen=null;S.riskFor=null;renderStatus();
 $("#dsInfo").textContent=`${d.name}: ${d.rows} rows, ${d.cols.length} columns, ${d.missing} missing values.`;
 const pv=$("#preview");pv.style.display="block";
 pv.innerHTML=`<table><tr>${d.cols.map(c=>`<th>${esc(c)}</th>`).join("")}</tr>${d.preview.map(r=>`<tr>${d.cols.map(c=>`<td>${esc(typeof r[c]==="number"?+r[c].toFixed(3):r[c])}</td>`).join("")}</tr>`).join("")}</table>`;
 $("#target").innerHTML=d.cols.map(c=>`<option ${c===d.target?"selected":""}>${esc(c)}</option>`).join("");
 $("#cfg").style.display="block";await loadTarget();}
$("#target").onchange=()=>run($("#trainBtn"),loadTarget);
async function loadTarget(){
 S.tgt=$("#target").value;$("#tgtPill").textContent=S.tgt;
 const t=await api("/api/target?name="+encodeURIComponent(S.tgt));
 if(t.continuous){S.mapping=null;
  $("#tgtDetail").innerHTML=`<div class="note" style="margin:0 0 8px">Continuous values: split into risk levels by percentile.</div>
  <div class="list"><div class="row"><label>Medium starts at <b id="q1V">P50</b></label></div><div class="row"><input type="range" id="q1" min="5" max="90" step="5" value="50"></div>
  <div class="row"><label>High starts at <b id="q2V">P80</b></label></div><div class="row"><input type="range" id="q2" min="10" max="95" step="5" value="80"></div></div>`;
  $("#q1").oninput=e=>$("#q1V").textContent="P"+e.target.value;$("#q2").oninput=e=>$("#q2V").textContent="P"+e.target.value;
 }else{
  $("#tgtDetail").innerHTML=`<div class="note" style="margin:0 0 8px">Map each value to a risk level.</div><div class="list">${t.mapping.map(m=>`<div class="row"><label>${esc(m.value)}</label><select class="in mapSel" data-v="${esc(m.value)}">${["Low","Medium","High"].map(l=>`<option ${l===m.level?"selected":""}>${l}</option>`).join("")}</select></div>`).join("")}</div>`;}
 S.feats=[...t.features];
 $("#featChips").innerHTML=$("#target").options.length?[...$("#target").options].map(o=>o.value).filter(c=>c!==S.tgt).map(c=>`<button class="chip ${S.feats.includes(c)?"on":""}" data-f="${esc(c)}">${esc(c)}</button>`).join(""):"";
 $$("#featChips .chip").forEach(c=>c.onclick=()=>{c.classList.toggle("on");});}
$("#ts").oninput=e=>$("#tsV").textContent=e.target.value+"%";
$("#trainBtn").onclick=e=>run(e.currentTarget,async()=>{
 const feats=$$("#featChips .chip.on").map(c=>c.dataset.f);
 const body={target:S.tgt,features:feats,test_size:+$("#ts").value/100};
 if($("#q1")){body.q_low=+$("#q1").value/100;body.q_high=+$("#q2").value/100;}
 else{body.mapping={};$$(".mapSel").forEach(s=>body.mapping[s.dataset.v]=s.value);}
 const r=await post("/api/train",body);S.train=r;S.chosen=r.best;S.riskFor=null;
 renderStatus();closeScr("data");tab("insights");toast(`Trained 5 models · best: ${r.best}`);});

/* ---------- insights ---------- */
function renderInsights(){
 const box=$("#insBody"),t=S.train;
 if(!t){box.innerHTML=`<div class="empty"><i class="ico" style="background:#ff2d55">${ic("chart",30)}</i><div style="font-size:19px;font-weight:600;color:var(--text)">No model yet</div><p>Load a dataset and train models to see how they perform.</p><button class="btn" style="max-width:260px;margin:0 auto" onclick="openScr('data')">Load Data</button></div>`;return;}
 const m=t.results.find(r=>r.Model===S.chosen),f=v=>v==null?"–":(v*100).toFixed(1)+"%";
 const cm=t.cms[S.chosen],mx=Math.max(...cm.flat(),1),n=t.classes.length,imp=t.importance[S.chosen];
 box.innerHTML=`
 <div class="sec">Model used for predictions</div>
 <div class="scroll">${t.results.map(r=>`<button class="chip model ${r.Model===S.chosen?"on":""}" data-m="${esc(r.Model)}">${esc(r.Model)}${r.Model===t.best?" ★":""}</button>`).join("")}</div>
 <div class="sec">Performance</div>
 <div class="stats">${[["Accuracy",m.Accuracy],["Precision",m.Precision],["Recall",m.Recall],["F1 score",m.F1],["High-risk recall",m["High-risk recall"]]].map(x=>`<div class="stat"><span>${x[0]}</span><b>${f(x[1])}</b></div>`).join("")}</div>
 <p class="note" style="margin:8px 2px">High-risk recall matters most: a missed flood costs more than a false alarm.</p>
 <div class="sec">All models (F1)</div>
 <div class="list">${t.results.map(r=>`<div class="prow" style="grid-template-columns:130px 1fr 52px"><span style="font-size:14px">${esc(r.Model)}</span><div class="bar"><i style="width:${(r.F1*100).toFixed(0)}%;background:var(--blue)"></i></div><b>${f(r.F1)}</b></div>`).join("")}</div>
 <div class="sec">Confusion matrix (rows actual, columns predicted)</div>
 <div class="list"><div class="cm" style="grid-template-columns:50px repeat(${n},1fr)"><div class="h"></div>${t.classes.map(c=>`<div class="h">${c}</div>`).join("")}${cm.map((row,i)=>`<div class="h" style="align-self:center">${t.classes[i]}</div>${row.map((v,j)=>`<div style="background:rgba(0,122,255,${(.08+.8*v/mx).toFixed(2)});color:${v/mx>.5?"#fff":"inherit"};font-weight:600">${v}</div>`).join("")}`).join("")}</div></div>
 <div class="sec">What drives the prediction</div>
 <div class="list">${imp?imp.map(x=>`<div class="prow" style="grid-template-columns:120px 1fr 44px"><span style="font-size:13px;overflow:hidden;text-overflow:ellipsis">${esc(x.name)}</span><div class="bar"><i style="width:${(x.value/imp[0].value*100).toFixed(0)}%;background:#af52de"></i></div><b style="font-size:12px">${x.value.toFixed(2)}</b></div>`).join(""):`<div class="row"><span class="val">This model does not expose feature importance.</span></div>`}</div>
 <div class="sec">Training data risk classes</div>
 <div class="list">${Object.entries(t.label_counts).map(([k,v])=>`<div class="row"><label><span class="dot" style="background:${COL[k]}"></span>${k}</label><span class="val">${v} samples</span></div>`).join("")}</div>`;
 $$("#insBody .chip.model").forEach(c=>c.onclick=async()=>{try{await post("/api/model",{name:c.dataset.m});S.chosen=c.dataset.m;renderStatus();renderInsights();}catch(e){toast(e.message,"err")}});}

/* ---------- risk shortcut ---------- */
function buildRisk(){
 const b=$("#riskBody"),t=S.train;
 if(!t){$("#runbar").style.display="none";b.innerHTML=`<div class="empty"><i class="ico" style="background:#ff3b30">${ic("alert",30)}</i><div style="font-size:19px;font-weight:600;color:var(--text)">Train a model first</div><p>This shortcut needs a trained model.</p><button class="btn" style="max-width:260px;margin:0 auto" id="goData">Load Data</button></div>`;$("#goData").onclick=()=>{closeScr("risk");openScr("data")};return;}
 $("#runbar").style.display="block";const pl=$("#rgPill");if(pl)pl.textContent=S.loc?S.loc.name.split(",")[0]:"Set a region";if(S.riskFor===t)return;S.riskFor=t;
 b.innerHTML=`
 <div class="action"><div class="ahead"><i class="ico" data-ic="cloud" data-bg="#30b0c7"></i><span>Get weather for <span class="pill" id="rgPill">${esc(S.loc?S.loc.name.split(",")[0]:"Set a region")}</span></span></div>
  <div class="abody"><button class="btn gray" id="wxBtn">Fill from live weather</button><p class="note" id="wxNote">Fills rainfall, temperature and humidity if your data has them. Check the units match.</p></div></div>
 <div class="action"><div class="ahead"><i class="ico" data-ic="database" data-bg="#34c759"></i>Set conditions</div>
  <div class="abody"><div class="list">${t.features.map(c=>{const s=t.inputs[c];return s.type==="num"
   ?`<div class="row"><label>${esc(c)}<small>data range ${+s.min.toFixed(2)} to ${+s.max.toFixed(2)}</small></label><input class="in" type="number" step="any" data-f="${esc(c)}" value="${+s.default.toFixed(3)}"></div>`
   :`<div class="row"><label>${esc(c)}</label><select class="in" data-f="${esc(c)}">${s.options.map(o=>`<option ${o===s.default?"selected":""}>${esc(o)}</option>`).join("")}</select></div>`}).join("")}</div></div></div>
 <div class="action"><div class="ahead"><i class="ico" data-ic="user" data-bg="#ff9500"></i>Assess exposure</div>
  <div class="abody"><div class="seg" id="dens" data-value="Medium"><button data-v="Low">Low density</button><button class="on" data-v="Medium">Medium</button><button data-v="High">High</button></div>
  <div class="list" style="margin-top:10px">${["Elderly","Children","Disabled","Medical dependence"].map((g,i)=>`<div class="row"><label>${g}${i===3?"<small>dialysis, oxygen, etc.</small>":" present"}</label><span class="sw"><input type="checkbox" class="grp" data-g="${i}"><i></i></span></div>`).join("")}</div></div></div>`;
 hydrateIcons(b);
 $("#wxBtn").onclick=e=>run(e.currentTarget,async()=>{const r=await api("/api/weather"),w=r.weather;
  $$("#riskBody [data-f]").forEach(el=>{if(r.suggestions[el.dataset.f]!=null)el.value=+r.suggestions[el.dataset.f].toFixed(2)});
  $("#wxNote").textContent=`Applied: ${w.temperature}°C, ${w.humidity}% humidity, rain last 3 days ${w.rain_past3d.toFixed(1)} mm, next 3 days ${w.rain_next3d.toFixed(1)} mm.`;toast("Live weather applied");});}
$("#runBtn").onclick=e=>run(e.currentTarget,async()=>{
 const inputs={};$$("#riskBody [data-f]").forEach(el=>inputs[el.dataset.f]=el.type==="number"?+el.value:el.value);
 const gs=$$(".grp");const r=await post("/api/predict",{inputs,density:$("#dens").dataset.value,groups:gs.slice(0,3).filter(g=>g.checked).length,group_names:["Elderly","Children","Disabled"].filter((n,i)=>gs[i].checked),medical:gs[3].checked});
 if(r.alert&&r.alert.triggered&&!r.alert.skipped||(r.sos&&r.sos.auto_sent))loadCfg().catch(()=>{});
 showResult(r);try{drawRisk(r)}catch(e){console.warn(e)}
 if(r.level==="High")notifyHigh(r);});
function showResult(r){
 const pc={Critical:"#ff3b30",High:"#ff9500",Moderate:"#d4a300",Routine:"#34c759"}[r.priority];
 openSheet(`
 <div class="badge"><div class="circle" style="background:${COL[r.level]}">${ic(r.level==="Low"?"check":"alert",30)}</div>
  <div><div class="sub">Flood risk</div><div class="big" style="color:${COL[r.level]}">${r.level}</div><span class="chip2" style="background:${pc}">Rescue priority: ${r.priority} · ${r.score}</span></div></div>
 ${alertBlock(r)}${sosBlock(r)}
 <div class="sec" style="margin-top:14px">Probability</div>
 <div class="list" style="padding:6px 0">${["Low","Medium","High"].map(l=>`<div class="prow"><span>${l}</span><div class="bar"><i style="width:${(r.probs[l]*100).toFixed(0)}%;background:${COL[l]}"></i></div><b>${(r.probs[l]*100).toFixed(0)}%</b></div>`).join("")}</div>
 <div class="sec">Emergency recommendations</div>
 <div class="list">${r.recommendations.map(x=>`<div class="check"><span style="flex:none">${ic("check",18,"#34c759")}</span><span>${esc(x)}</span></div>`).join("")}</div>
 <div class="sec">Evacuation guidance</div>
 <div class="list">${r.evacuation.map(x=>`<div class="check"><span style="flex:none">${ic("pin",18,"#007aff")}</span><span>${esc(x)}</span></div>`).join("")}</div>
 ${r.govt_nearest.length?`<div class="sec">Nearest government safe houses</div><div class="list">${r.govt_nearest.map(placeRow).join("")}</div>`:(r.loc?`<div class="banner gray">No government safe houses found nearby in the map data. Upload your district's shelter list (CSV with a govt column) for accurate results.</div>`:"")}
 ${r.nearest.length?`<div class="sec">Other safe locations</div><div class="list">${r.nearest.filter(p=>!r.govt_nearest.some(g=>g.name===p.name&&g.lat===p.lat)).map(placeRow).join("")}</div>`:""}
 <button class="btn" style="margin-top:18px" id="toMap">View on Map</button>
 <button class="btn gray" style="margin-top:10px" id="shClose">Done</button>`);
 $("#toMap").onclick=()=>{closeSheet();closeScr("risk");tab("map")};$("#shClose").onclick=closeSheet;
 const rv=$("#sosReview");if(rv)rv.onclick=()=>sosPreview();}

/* ---------- other sheets ---------- */
async function weatherSheet(){
 if(!S.loc){toast("Set a region first.","err");return openScr("region");}
 try{const w=(await api("/api/weather")).weather;
  openSheet(`<h2>Live weather</h2><div class="sub" style="margin:-6px 0 12px">${esc(S.loc.name)}</div><div class="stats">${[["Temperature",w.temperature+"°C"],["Humidity",w.humidity+"%"],["Rain now",w.rain_now+" mm"],["Rain, last 3 days",w.rain_past3d.toFixed(1)+" mm"],["Rain, next 3 days",w.rain_next3d.toFixed(1)+" mm"]].map(x=>`<div class="stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join("")}</div><p class="note">Source: Open-Meteo.</p>`);
 }catch(e){toast(e.message,"err")}}
const govtTag=g=>g==="verified"?'<span class="tag ok">Govt ✓</span>':g==="likely"?'<span class="tag mid">Likely govt</span>':"";
const dirLink=p=>`https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${S.loc.lat}%2C${S.loc.lon}%3B${p.lat}%2C${p.lon}`;
function placeRow(p){return `<a class="place" href="${esc(p.directions||dirLink(p))}" target="_blank" rel="noopener"><div><b>${esc(p.name)}</b>${govtTag(p.govt)}<small>${esc(p.type)} · ${p.distance_km.toFixed(1)} km · ${p.walk_min} min walk${p.higher_ground==="Yes"?" · higher ground":""}${p.phone?" · "+esc(p.phone):""}</small></div>${ic("chev",18,"var(--sub)")}</a>`;}
function placesSheet(mode){
 if(!S.loc){toast("Set a region first.","err");return openScr("region");}
 if(!S.places.length)return openSheet(`<h2>Government safe houses</h2><p class="sub">None loaded. Set the region with OpenStreetMap, or upload a shelters CSV.</p><button class="btn gap" onclick="closeSheet();openScr('region')">Set Region</button>`);
 mode=mode||"govt";
 const all=S.places.map(p=>({...p,distance_km:km(S.loc.lat,S.loc.lon,p.lat,p.lon)})).map(p=>({...p,walk_min:Math.round(p.distance_km/5*60)})).sort((a,b)=>a.distance_km-b.distance_km);
 const list=(mode==="govt"?all.filter(p=>p.govt):all).slice(0,20),nv=all.filter(p=>p.govt==="verified").length,nl=all.filter(p=>p.govt==="likely").length;
 openSheet(`<h2>Government safe houses</h2>
 <div class="seg" id="gSeg" data-value="${mode}"><button data-v="govt" class="${mode==="govt"?"on":""}">Government (${nv+nl})</button><button data-v="all" class="${mode==="all"?"on":""}">All places (${all.length})</button></div>
 <div class="list gap">${list.length?list.map(placeRow).join(""):`<div class="row"><span class="val">No government facilities found in this area's map data.</span></div>`}</div>
 <p class="note">“Govt ✓” means tagged government/public in OpenStreetMap (${nv} here). “Likely govt” is a name-based guess (${nl} here). Confirm with your district disaster management office before relying on a shelter. To use official data, upload a CSV with a <b>govt</b> column.</p>`);
 $("#gSeg").onchange=()=>placesSheet($("#gSeg").dataset.value);}
const GUIDE_FALLBACK={ // offline copy of the emergency guide (same as rescue_logic.py)
 Low:["Stay informed through official weather and flood bulletins.","Keep drains and nearby water channels clear of debris.","Review your family emergency plan and keep contacts handy."],
 Medium:["Prepare an emergency kit: water, food, medicines, torch, power bank, documents.","Move valuables and electronics to higher shelves or floors.","Identify your nearest shelter and the route to it.","Avoid low-lying roads, underpasses and river banks."],
 High:["Evacuate low-lying areas now toward the nearest higher-ground shelter.","Switch off electricity and gas at the mains before leaving.","Never walk or drive through flowing floodwater.","Help children, elderly and disabled people first; call emergency services if trapped.","Follow official evacuation orders and keep your phone charged."]};
async function guideSheet(){
 try{let off=false;const g=await api("/api/guide").catch(()=>{off=true;return GUIDE_FALLBACK});
  openSheet(`<h2>Emergency guide</h2>${off?'<p class="note">Offline copy</p>':""}${["High","Medium","Low"].map(l=>`<div class="sec"><span class="dot" style="background:${COL[l]}"></span>${l} risk</div><div class="list">${g[l].map(x=>`<div class="check"><span>•</span><span>${esc(x)}</span></div>`).join("")}</div>`).join("")}`);
 }catch(e){toast(e.message,"err")}}

/* ---------- batch ---------- */
$("#batchFile").onchange=e=>{const f=e.target.files[0];if(!f)return;runPlain(async()=>{
 const r=await upload("/api/batch",f);
 try{initMap();S.lg.batch.clearLayers();const pts=[];r.rows.forEach(x=>{L.circleMarker([x.lat,x.lon],{radius:10,color:COL[x.risk],fillColor:COL[x.risk],fillOpacity:.6}).bindTooltip(`${x.risk} (${(x.confidence*100).toFixed(0)}%)`).addTo(S.lg.batch);pts.push([x.lat,x.lon]);});if(pts.length)S.map.fitBounds(pts,{padding:[30,30]});}catch(e){console.warn(e)}
 const cnt={Low:0,Medium:0,High:0};r.rows.forEach(x=>cnt[x.risk]++);
 $("#batchOut").innerHTML=`<div class="sec">${r.rows.length} areas</div><div class="list">${Object.entries(cnt).map(([k,v])=>`<div class="row"><label><span class="dot" style="background:${COL[k]}"></span>${k}</label><span class="val">${v}</span></div>`).join("")}</div><button class="btn" style="margin-top:16px" id="bMap">View on Map</button>`;
 $("#bMap").onclick=()=>{closeScr("batch");tab("map")};toast(`Predicted ${r.rows.length} areas`);});};

/* ---------- map ---------- */
function initMap(){if(S.map)return;S.map=L.map("map").setView([20,78],4);
 L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"© OpenStreetMap"}).addTo(S.map);
 S.lg={risk:L.layerGroup().addTo(S.map),places:L.layerGroup().addTo(S.map),stations:L.layerGroup().addTo(S.map),batch:L.layerGroup().addTo(S.map)};}
function drawPlaces(center){initMap();S.lg.places.clearLayers();
 S.places.forEach(p=>{const g=!!p.govt;L.circleMarker([p.lat,p.lon],{radius:g?7:4,color:g?"#fff":"#007aff",weight:g?2:3,fillColor:g?"#1f9d45":"#007aff",fillOpacity:.9}).bindTooltip(`${p.name} (${p.type})${g?" · govt":""}`).addTo(S.lg.places)});
 if(center&&S.loc)S.map.setView([S.loc.lat,S.loc.lon],13);}
function drawRisk(r){initMap();const g=S.lg.risk;g.clearLayers();const loc=r.loc||S.loc;if(!loc)return;const c=COL[r.level];
 L.circle([loc.lat,loc.lon],{radius:(loc.radius||5)*500,color:c,fillColor:c,fillOpacity:.18}).addTo(g);
 L.circleMarker([loc.lat,loc.lon],{radius:9,color:"#fff",weight:2,fillColor:c,fillOpacity:1}).bindTooltip(`${r.level} flood risk`).addTo(g);
 r.nearest.forEach((p,i)=>{L.circleMarker([p.lat,p.lon],{radius:9,color:"#fff",weight:2,fillColor:"#34c759",fillOpacity:1}).bindTooltip(`#${i+1} ${p.name} · ${p.distance_km.toFixed(1)} km`).addTo(g);
  if(i===0)L.polyline([[loc.lat,loc.lon],[p.lat,p.lon]],{color:"#34c759",weight:4,dashArray:"8 8"}).addTo(g);});
 S.map.setView([loc.lat,loc.lon],13);$("#mapSub").textContent=`${r.level} risk at ${loc.name.split(",")[0]}`;}

/* ---------- alerts, SOS ---------- */
const loadCfg=async()=>{S.cfg=await api("/api/alerts/config");renderStatus();return S.cfg;};
const stChip=s=>`<span class="st ${esc(s)}">${esc(s)}</span>`;
const modeCard=c=>c.live?`<div class="banner red">🔴 LIVE MODE: messages are really sent to the contacts below.</div>`
 :`<div class="banner orange">🧪 Simulation mode: nothing is sent. Every alert and SOS is logged so you can see who would be contacted. Set FLOODSHIELD_LIVE=1 and provider keys to go live.</div>`;
const provRows=c=>`<div class="list">${[["Telegram","telegram"],["Email (SMTP)","email"],["SMS (Twilio)","sms"]].map(x=>`<div class="row"><label><span class="dot ${c.providers[x[1]]?"on":""}"></span>${x[0]}</label><span class="val">${c.providers[x[1]]?"configured":"not configured"}</span></div>`).join("")}</div>`;
function alertBlock(r){
 const a=r.alert;if(!a||!a.triggered)return "";
 const sim=r.mode==="simulation"?" (simulation)":"";
 if(a.skipped)return `<div class="banner gray">🔔 Alert not re-sent: ${esc(a.skipped)}</div>`;
 return `<div class="banner red">🚨 Alert dispatched to ${a.sent} subscriber${a.sent===1?"":"s"}${sim}</div>`;}
function sosBlock(r){
 const x=r.sos;if(!x||!x.recommended)return "";
 const call=`<a class="btn red sm gap" href="tel:${esc(r.emergency_number)}">📞 Call ${esc(r.emergency_number)} (emergency)</a>`;
 if(x.note)return `<div class="banner red">🆘 SOS recommended. ${esc(x.note)}</div>${call}`;
 if(x.auto_sent)return `<div class="banner red">🆘 SOS sent to ${x.results.length} nearby station${x.results.length===1?"":"s"}${r.mode==="simulation"?" (simulation)":""}</div>
  <div class="list">${x.results.map(q=>`<div class="place" style="cursor:default"><div><b>${esc(q.name)}</b><small>${esc(q.type.replace("_"," "))} · ${q.distance_km.toFixed(1)} km · via ${esc(q.channel)}</small></div>${stChip(q.status)}</div>`).join("")}</div>${call}`;
 return `<div class="banner red">🆘 ${x.skipped?esc(x.skipped):"SOS recommended for this risk level."}</div><button class="btn red sm" id="sosReview">Review &amp; send SOS</button>${call}`;}

async function saveSetting(patch,after){try{await post("/api/alerts/settings",patch);await loadCfg();if(after)after();}catch(e){toast(e.message,"err")}}
function fmtTime(ts){return new Date(ts*1000).toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});}
function logList(items,empty){
 if(!items.length)return `<div class="list"><div class="row"><span class="val">${empty}</span></div></div>`;
 return `<div class="list">${items.slice(0,12).map(e=>{const cnt={};e.results.forEach(r=>cnt[r.status]=(cnt[r.status]||0)+1);
  return `<div class="row" style="align-items:flex-start"><label style="min-width:0"><b style="color:${COL[e.level]}">${e.kind==="sos"?"SOS":"Alert"} · ${e.level}</b><small>${esc(e.place)}<br>${fmtTime(e.ts)} · ${e.results.length} recipient${e.results.length===1?"":"s"}</small></label><span style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end">${Object.entries(cnt).map(([k,v])=>`${stChip(k)}${v>1?"×"+v:""}`).join("")}</span></div>`}).join("")}</div>`;}

async function renderAlerts(){
 const b=$("#alertsBody");b.innerHTML='<p class="note">Loading…</p>';
 try{
  const c=await loadCfg(),log=(await api("/api/alerts/log")).filter(x=>x.kind==="alert"),st=c.settings;
  b.innerHTML=`${modeCard(c)}
  <div class="action"><div class="ahead"><i class="ico" data-ic="bell" data-bg="#e8431f"></i>Auto alerts</div><div class="abody">
   <div class="list"><div class="row"><label>Send automatically</label><span class="sw"><input type="checkbox" id="aAuto" ${st.auto_alert?"checked":""}><i></i></span></div></div>
   <div class="note" style="margin:12px 0 6px">Alert subscribers when predicted risk is at least</div>
   <div class="seg" id="aLevel" data-value="${st.alert_level}"><button data-v="Medium" class="${st.alert_level==="Medium"?"on":""}">Medium</button><button data-v="High" class="${st.alert_level==="High"?"on":""}">High</button></div>
   <p class="note">The same area is not re-alerted for ${st.cooldown_min} minutes.</p></div></div>
  <div class="action"><div class="ahead"><i class="ico" data-ic="user" data-bg="#007aff"></i>Subscribers <span class="pill">${c.subscribers.length}</span></div><div class="abody">
   ${c.subscribers.length?`<div class="list">${c.subscribers.map(s=>`<div class="row"><label style="min-width:0">${esc(s.name)}<small>${esc(s.channel)}: ${esc(s.target)}</small></label><button class="link" style="color:var(--red)" data-del="${s.id}">Remove</button></div>`).join("")}</div>`:`<p class="note" style="margin:0 0 8px">No subscribers yet. Add family, neighbours or local volunteers.</p>`}
   <div class="list gap"><div class="row"><input class="in left" id="sName" placeholder="Name"></div>
    <div class="row"><label>Channel</label><select class="in" id="sChan"><option value="telegram">Telegram chat ID</option><option value="email">Email</option><option value="sms">SMS</option></select></div>
    <div class="row"><input class="in left" id="sTarget" placeholder="Chat ID, email or +91… number"></div></div>
   <button class="btn gray gap" id="sAdd">Add subscriber</button></div></div>
  <div class="action"><div class="ahead"><i class="ico" data-ic="cloud" data-bg="#34c759"></i>Delivery channels</div><div class="abody">${provRows(c)}</div></div>
  <button class="btn" id="aTest">Send test alert</button>
  <button class="btn gray gap" id="aNotif">Enable notifications</button>
  <div class="sec">Recent alerts</div>${logList(log,"No alerts yet.")}`;
  hydrateIcons(b);
  $("#aAuto").onchange=e=>saveSetting({auto_alert:e.target.checked});
  $("#aLevel").onchange=()=>saveSetting({alert_level:$("#aLevel").dataset.value});
  $("#sAdd").onclick=e=>run(e.currentTarget,async()=>{await post("/api/subscribers",{name:$("#sName").value,channel:$("#sChan").value,target:$("#sTarget").value});toast("Subscriber added");await renderAlerts();});
  $$("[data-del]",b).forEach(x=>x.onclick=async()=>{await api("/api/subscribers/"+x.dataset.del,{method:"DELETE"});renderAlerts();});
  $("#aTest").onclick=e=>run(e.currentTarget,async()=>{const r=await api("/api/alerts/test",{method:"POST"});toast(`Test alert: ${r.sent} recipient(s)${r.mode==="simulation"?" (simulation)":""}`);await renderAlerts();});
  $("#aNotif").onclick=async()=>{try{const N=nat("LocalNotifications");
   if(N){const p=await N.requestPermissions();return toast(p.display==="granted"?"Notifications enabled":"Notifications were not allowed",p.display==="granted"?"ok":"err");}
   if(!("Notification" in window))return toast("Notifications are not supported here.","err");
   const p=await Notification.requestPermission();toast(p==="granted"?"Notifications enabled":"Notifications were not allowed",p==="granted"?"ok":"err");
  }catch(e){toast("Could not change notification settings.","err")}};
 }catch(e){b.innerHTML=`<div class="banner red">${esc(e.message)}</div>`}}

async function renderSOS(){
 const b=$("#sosBody");b.innerHTML='<p class="note">Loading…</p>';
 try{
  const c=await loadCfg(),log=(await api("/api/alerts/log")).filter(x=>x.kind==="sos"),st=c.settings;
  let sta=null,err="";try{sta=await api("/api/stations")}catch(e){err=e.message}
  const chName={telegram:"Telegram",email:"Email",sms:"SMS"};
  b.innerHTML=`${modeCard(c)}
  <a class="btn red" href="tel:${esc(st.emergency_number)}">📞 Call ${esc(st.emergency_number)} (emergency services)</a>
  <p class="note" style="margin:8px 4px">FloodShield supports, but never replaces, official emergency services. In immediate danger, call first.</p>
  <div class="action"><div class="ahead"><i class="ico" data-ic="siren" data-bg="#c4122f"></i>Auto SOS</div><div class="abody">
   <div class="list"><div class="row"><label>Send SOS automatically<small>when risk is too high</small></label><span class="sw"><input type="checkbox" id="xAuto" ${st.auto_sos?"checked":""}><i></i></span></div></div>
   <div class="note" style="margin:12px 0 6px">Trigger when</div>
   <div class="seg" id="xTrig" data-value="${st.sos_trigger}"><button data-v="critical" class="${st.sos_trigger==="critical"?"on":""}">Critical priority</button><button data-v="high" class="${st.sos_trigger==="high"?"on":""}">Any High risk</button></div>
   <div class="note" style="margin:12px 0 6px">Notify nearest stations</div>
   <div class="seg" id="xN" data-value="${st.sos_stations}">${[1,2,3,5].map(n=>`<button data-v="${n}" class="${st.sos_stations===n?"on":""}">${n}</button>`).join("")}</div>
   <p class="note">With 3 or more, the nearest police, fire and medical station are included first.</p></div></div>
  <div class="action"><div class="ahead"><i class="ico" data-ic="pin" data-bg="#ff3b30"></i>Stations that would receive the SOS</div><div class="abody">
   ${sta&&sta.stations.length?`<div class="list">${sta.stations.map(x=>`<div class="row" style="align-items:flex-start"><label style="min-width:0"><b>${esc(x.name)}</b><small>${esc(x.type.replace("_"," "))} · ${x.distance_km.toFixed(1)} km · ${x.channel?"via "+chName[x.channel]:"call only"}</small></label>${x.phone?`<a class="link" href="tel:${esc(x.phone)}">Call</a>`:""}</div>`).join("")}</div>`
    :`<div class="banner gray">${esc(err||"No stations found for this region yet.")}</div>`}
   <p class="note">${sta?`${sta.osm_found} found on the map, ${sta.directory_size} in your directory. `:""}Real messages go only to stations in your own directory (or map contacts if you enabled that). Others are call-only.</p>
   <div class="list gap"><div class="row"><input class="in left" type="file" id="dirFile" accept=".csv"></div></div>
   <p class="note">Station directory CSV: name, type, lat, lon, phone, email, telegram_chat_id</p></div></div>
  <button class="btn red" id="xSend">Review &amp; send SOS now</button>
  <div class="sec">SOS history</div>${logList(log,"No SOS sent yet.")}`;
  hydrateIcons(b);
  $("#xAuto").onchange=e=>saveSetting({auto_sos:e.target.checked});
  $("#xTrig").onchange=()=>saveSetting({sos_trigger:$("#xTrig").dataset.value},renderSOS);
  $("#xN").onchange=()=>saveSetting({sos_stations:+$("#xN").dataset.value},renderSOS);
  $("#dirFile").onchange=e=>{const f=e.target.files[0];if(f)runPlain(async()=>{const r=await upload("/api/stations/upload",f);toast(`${r.count} stations added to your directory`);renderSOS();});};
  $("#xSend").onclick=()=>sosPreview();
  if(sta)try{drawStations(sta.stations)}catch(e){}
 }catch(e){b.innerHTML=`<div class="banner red">${esc(e.message)}</div>`}}

function drawStations(list){initMap();S.lg.stations.clearLayers();
 list.forEach(x=>L.circleMarker([x.lat,x.lon],{radius:8,color:"#fff",weight:2,fillColor:"#af52de",fillOpacity:.95}).bindTooltip(`${x.name} (${x.type.replace("_"," ")}) · ${x.distance_km.toFixed(1)} km`).addTo(S.lg.stations));}

async function sosPreview(){
 try{const pv=await api("/api/sos/preview");
  openSheet(`<h2>Review SOS</h2>${pv.mode==="simulation"?'<div class="banner orange">Simulation mode: nothing will actually be sent.</div>':'<div class="banner red">LIVE: this will message the stations below.</div>'}
  <div class="sec" style="margin-top:6px">Message</div><div class="msg">${esc(pv.text)}</div>
  <div class="sec">Recipients</div><div class="list">${pv.plan.map(x=>`<div class="place" style="cursor:default"><div><b>${esc(x.name)}</b><small>${esc(x.type.replace("_"," "))} · ${x.distance_km.toFixed(1)} km</small></div><span class="st ${x.channel?"simulated":"call-only"}" style="${x.channel?"background:var(--fill);color:var(--text)":""}">${x.channel||"call only"}</span></div>`).join("")}</div>
  <button class="btn red gap" id="xConfirm">Send SOS</button>
  <a class="btn gray gap" href="tel:${esc(pv.emergency_number)}">📞 Call ${esc(pv.emergency_number)} instead</a>
  <button class="btn gray gap" onclick="closeSheet()">Cancel</button>`);
  $("#xConfirm").onclick=e=>run(e.currentTarget,async()=>{const r=await api("/api/sos/send",{method:"POST"});closeSheet();
   toast(`SOS ${r.mode==="simulation"?"simulated":"sent"} to ${r.results.length} station(s)`);loadCfg().catch(()=>{});
   if($("#scr-sos").classList.contains("open"))renderSOS();});
 }catch(e){toast(e.message,"err")}}

/* ---------- mobile app: install, server address, offline ---------- */
const nat=n=>(window.Capacitor&&window.Capacitor.Plugins&&window.Capacitor.Plugins[n])||null; // native plugin or null
async function notifyHigh(r){
 const nm=r.loc&&!/^[-\d.\s]+,/.test(r.loc.name)?r.loc.name.split(",")[0]:"Your area";
 const title="High flood risk",body=`${nm}: rescue priority ${r.priority}`;
 try{const N=nat("LocalNotifications");
  if(N){const p=await N.checkPermissions();if(p.display==="granted")await N.schedule({notifications:[{id:Date.now()%2147483647,title,body}]});return;}
  if("Notification" in window&&Notification.permission==="granted")new Notification(title,{body});
 }catch(e){}}
function nativeBack(){ // Android back button: close the top layer first, exit only from Home
 if($("#sheet").classList.contains("open"))return closeSheet();
 const sc=document.querySelector(".screen.open");if(sc)return closeScr(sc.id.replace("scr-",""));
 const tb=document.querySelector(".tab.active");if(tb&&tb.id!=="tab-home")return tab("home");
 const A=nat("App");if(A&&A.exitApp)A.exitApp();}
let deferredPrompt=null;
const isNative=!!(window.Capacitor&&window.Capacitor.isNativePlatform&&window.Capacitor.isNativePlatform());
const isStandalone=()=>isNative||window.matchMedia("(display-mode: standalone)").matches||navigator.standalone===true;
const isIOS=/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);
function appState(){return isStandalone()?"Installed":deferredPrompt?"Tap to install":isIOS?"Add to Home Screen":"Install from browser menu";}
window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferredPrompt=e;renderStatus();});
window.addEventListener("appinstalled",()=>{deferredPrompt=null;renderStatus();toast("FloodShield installed");});
function statusGo(g){if(g==="server")return serverSheet();if(g==="install")return installApp();openScr(g);if(g==="alerts")renderAlerts();if(g==="sos")renderSOS();}
async function installApp(){
 if(isStandalone())return toast("Already running as an app.");
 if(deferredPrompt){deferredPrompt.prompt();try{await deferredPrompt.userChoice}catch(e){}deferredPrompt=null;return renderStatus();}
 openSheet(`<h2>Install FloodShield</h2>
 <div class="sec">iPhone / iPad (Safari)</div><div class="list"><div class="check"><span>1.</span><span>Tap the Share button.</span></div><div class="check"><span>2.</span><span>Choose “Add to Home Screen”, then “Add”.</span></div></div>
 <div class="sec">Android (Chrome)</div><div class="list"><div class="check"><span>1.</span><span>Tap the ⋮ menu.</span></div><div class="check"><span>2.</span><span>Choose “Install app” or “Add to Home screen”.</span></div></div>
 <p class="note">Full install, offline mode and “Use my location” need HTTPS (or localhost). Over plain http on Wi-Fi the app still opens from the home screen but cannot work offline.</p>`);}
function serverSheet(){
 openSheet(`<h2>Server</h2><p class="sub">Address of the FloodShield server this app talks to. Leave it empty when the page is opened from the server itself.</p>
 <div class="list"><div class="row"><input class="in left" id="srvUrl" placeholder="https://your-server or http://192.168.1.5:8000" value="${esc(apiBase())}" autocapitalize="off" autocorrect="off" spellcheck="false"></div></div>
 <button class="btn gap" id="srvSave">Save &amp; test</button>
 <button class="btn gray gap" id="srvClear">Use this device’s server</button>
 <p class="note">Use your computer’s address on the same Wi-Fi (http://&lt;computer-ip&gt;:8000) or an HTTPS address from a tunnel or hosting. Your computer and phone must be able to reach each other.</p>`);
 $("#srvSave").onclick=e=>run(e.currentTarget,async()=>{let u=$("#srvUrl").value.trim().replace(/\/+$/,"");if(!u)throw new Error("Enter a server address, or tap “Use this device’s server”.");
  if(!/^https?:\/\//i.test(u))u="http://"+u;
  const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),7000);
  try{const r=await fetch(u+"/api/status",{signal:ctl.signal});if(!r.ok)throw new Error("Server answered with an error ("+r.status+").")}catch(err){throw new Error("Could not reach "+u+". Check the address, Wi-Fi, and that the server is running.")}finally{clearTimeout(t)}
  localStorage.setItem("fs_api",u);toast("Connected to "+u);setTimeout(()=>location.reload(),700);});
 $("#srvClear").onclick=()=>{localStorage.removeItem("fs_api");toast("Using this device’s server");setTimeout(()=>location.reload(),500);};}
window.addEventListener("offline",()=>toast("You’re offline. The Emergency Guide still works.","err"));
window.addEventListener("online",()=>toast("Back online"));
if("serviceWorker" in navigator&&!isNative&&(location.protocol==="https:"||location.hostname==="localhost"||location.hostname==="127.0.0.1"))
 window.addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));
if(isNative&&!apiBase())setTimeout(serverSheet,500);
if(isNative){const A=nat("App");if(A&&A.addListener)A.addListener("backButton",nativeBack);}

/* ---------- init ---------- */
hydrateIcons();renderStatus();loadCfg().catch(()=>{});
api("/api/status").then(s=>{S.loc=s.loc;S.places=s.places||[];S.ds=s.dataset;S.train=s.train;S.chosen=s.chosen;renderStatus();
 if(S.loc){$("#lat").value=S.loc.lat.toFixed(5);$("#lon").value=S.loc.lon.toFixed(5);}}).catch(()=>{});
