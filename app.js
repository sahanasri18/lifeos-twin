import * as THREE from 'three';

const API = (window.LIFEOS_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const districts = [
  {id:'CENTRAL',name:'Central District',short:'CENTRAL',population:26000,green:9,load:58,kind:'Mixed-use core',description:"The city's mixed-use core, with civic services and commercial activity."},
  {id:'NORTH',name:'North Quarter',short:'NORTH',population:18000,green:18,load:43,kind:'Residential',description:'A growing residential district with schools, parks and local services.'},
  {id:'EAST',name:'East Gardens',short:'EAST',population:15000,green:27,load:51,kind:'Residential',description:'A residential district with community facilities and green space.'},
  {id:'SOUTH',name:'South Works',short:'SOUTH',population:21000,green:12,load:32,kind:'Industrial',description:'A mixed employment district with industrial activity and supporting services.'},
  {id:'WEST',name:'West Riverside',short:'WEST',population:12000,green:31,load:76,kind:'Residential',description:'A smaller district with residential activity and riverside connections.'}
];
let selected = 0;
const $ = (id) => document.getElementById(id);
const fmt = (n) => Math.round(n).toLocaleString('en-IN');
let authToken = sessionStorage.getItem('lifeos_access_token') || '';
let currentUser = null;
let authMode = 'login';
async function authFetch(path, options={}) {
  const headers = new Headers(options.headers || {});
  if (authToken) headers.set('Authorization', `Bearer ${authToken}`);
  return fetch(`${API}${path}`, {...options, headers});
}
function setAuthVisible(visible) { $('auth-gate').hidden = !visible; $('app-shell').classList.toggle('workspace-locked', visible); }
function showAuthError(message='') { $('auth-error').textContent = message; }
function renderAuthMode() {
  $('auth-title').textContent = authMode === 'login' ? 'Welcome to LifeOS Twin' : 'Create your workspace';
  $('auth-submit').textContent = authMode === 'login' ? 'Sign in →' : 'Create account →';
  $('auth-switch').textContent = authMode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in';
  $('auth-password').autocomplete = authMode === 'login' ? 'current-password' : 'new-password';
  $('auth-password').minLength = authMode === 'login' ? 1 : 10;
  showAuthError();
}
async function establishSession(payload) {
  authToken = payload.access_token;
  sessionStorage.setItem('lifeos_access_token', authToken);
  currentUser = payload.user;
  $('user-email').textContent = currentUser.email;
  setAuthVisible(false);
  await refreshScenarioHistory();
  await refreshPrivateDocuments();
}
async function validateSession() {
  if (!authToken) { setAuthVisible(true); return; }
  try {
    const response = await authFetch('/auth/me');
    if (!response.ok) throw new Error('Session expired');
    const data = await response.json(); currentUser = data.user;
    $('user-email').textContent = currentUser.email;
    setAuthVisible(false);
    await refreshScenarioHistory(); await refreshPrivateDocuments();
  } catch (_) {
    authToken = ''; currentUser = null; sessionStorage.removeItem('lifeos_access_token'); setAuthVisible(true);
  }
}

function setDistrict(index){
  selected = index; const d = districts[index];
  $('district-title').textContent=d.name; $('district-index').textContent=`0${index+1} / 05`;
  $('district-pop').textContent=fmt(d.population); $('green-space').textContent=`${d.green}%`;
  $('green-bar').style.width=`${d.green}%`; $('infra-load').textContent=d.load>65?'High':d.load>45?'Moderate':'Low';
  $('infra-bar').style.width=`${d.load}%`; $('district-description').textContent=d.description;
  $('district-strip').querySelectorAll('button').forEach((b,i)=>b.classList.toggle('active',i===index));
  if(window.cityMeshes) window.cityMeshes.forEach((m,i)=>m.material.emissive.setHex(i===index?0x164d59:0x000000));
}
$('district-strip').innerHTML=districts.map((d,i)=>`<button class="district-chip ${i===0?'active':''}" data-index="${i}">${d.short}</button>`).join('');
$('district-strip').addEventListener('click',e=>{const b=e.target.closest('button[data-index]');if(b)setDistrict(Number(b.dataset.index));});

// Three.js city: low-poly, interactive, fully synthetic geometry.
const stage=$('city-stage');
let scene,camera,renderer,cityGroup,raycaster,mouse,dragging=false,lastX=0,lastY=0,zoom=1;
const pickables=[];
function building(x,z,w,d,h,color,districtIndex){
  const geo=new THREE.BoxGeometry(w,h,d); const mat=new THREE.MeshStandardMaterial({color,roughness:.82,metalness:.05,emissive:0x000000});
  const mesh=new THREE.Mesh(geo,mat);mesh.position.set(x,h/2,z);mesh.userData={districtIndex};cityGroup.add(mesh);pickables.push(mesh);
  const roof=new THREE.Mesh(new THREE.BoxGeometry(w*1.03,.08,d*1.03),new THREE.MeshStandardMaterial({color:0x9eb8c5,roughness:1}));roof.position.set(x,h+.04,z);cityGroup.add(roof);
}
function initCity(){
  scene=new THREE.Scene();scene.background=new THREE.Color(0x0a1727);scene.fog=new THREE.Fog(0x0a1727,24,55);
  camera=new THREE.PerspectiveCamera(42,stage.clientWidth/stage.clientHeight,.1,100);camera.position.set(13,16,18);camera.lookAt(0,0,0);
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));renderer.setSize(stage.clientWidth,stage.clientHeight);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;stage.prepend(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0x9fc9e0,0x142336,2));const sun=new THREE.DirectionalLight(0xc7e8ff,2.4);sun.position.set(-8,16,9);sun.castShadow=true;scene.add(sun);
  cityGroup=new THREE.Group();scene.add(cityGroup);
  const ground=new THREE.Mesh(new THREE.BoxGeometry(23,.35,18),new THREE.MeshStandardMaterial({color:0x193247,roughness:1}));ground.position.y=-.22;ground.receiveShadow=true;cityGroup.add(ground);
  // Road grid
  for(let x=-9;x<=9;x+=4.5){const road=new THREE.Mesh(new THREE.BoxGeometry(.55,.04,17.5),new THREE.MeshStandardMaterial({color:0x344657}));road.position.set(x,-.015,0);cityGroup.add(road);}
  for(let z=-7;z<=7;z+=4.5){const road=new THREE.Mesh(new THREE.BoxGeometry(22,.04,.55),new THREE.MeshStandardMaterial({color:0x344657}));road.position.set(0,-.012,z);cityGroup.add(road);}
  // District zones and block clusters
  const zones=[[-5.7,-3.9],[-5.7,4.1],[0,0],[5.7,-3.9],[5.7,4.1]];
  const colors=[0x4b8f9b,0x568eaa,0x6e9b9b,0x477f75,0xb58a5c];
  zones.forEach(([cx,cz],di)=>{
    const park=new THREE.Mesh(new THREE.BoxGeometry(3.4,.08,3.0),new THREE.MeshStandardMaterial({color:di===3?0x2e745f:0x254c4c,roughness:1}));park.position.set(cx,-.01,cz);cityGroup.add(park);
    for(let ix=0;ix<3;ix++)for(let iz=0;iz<3;iz++){
      const h=1.0+((ix*7+iz*5+di*3)%5)*.48+(di===4?.55:0);
      const w=.62+((ix+iz)%2)*.18;const depth=.62+((ix*2+iz)%2)*.16;
      building(cx+(ix-1)*1.02,cz+(iz-1)*.88,w,depth,h,colors[di],di);
    }
  });
  // Water channel and civic landmark
  const river=new THREE.Mesh(new THREE.BoxGeometry(1.05,.035,17),new THREE.MeshStandardMaterial({color:0x287a9a,metalness:.25,roughness:.28}));river.position.set(2.25,.01,0);cityGroup.add(river);
  const tower=new THREE.Mesh(new THREE.CylinderGeometry(.32,.48,3.6,8),new THREE.MeshStandardMaterial({color:0x9db5d0,metalness:.2,roughness:.4}));tower.position.set(0,1.8,0);cityGroup.add(tower);
  raycaster=new THREE.Raycaster();mouse=new THREE.Vector2();window.cityMeshes=districts.map(()=>null);
  $('stage-loading').style.display='none';
  renderer.domElement.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;renderer.domElement.setPointerCapture(e.pointerId);});
  renderer.domElement.addEventListener('pointermove',e=>{if(dragging){cityGroup.rotation.y+=(e.clientX-lastX)*.006;cityGroup.rotation.x=Math.max(-.3,Math.min(.3,cityGroup.rotation.x+(e.clientY-lastY)*.003));lastX=e.clientX;lastY=e.clientY;return;}const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects(pickables);if(hit.length){const d=districts[hit[0].object.userData.districtIndex];$('scene-tooltip').textContent=d.name;$('scene-tooltip').classList.add('show');}else $('scene-tooltip').classList.remove('show');});
  renderer.domElement.addEventListener('pointerup',e=>{dragging=false;const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects(pickables);if(hit.length)setDistrict(hit[0].object.userData.districtIndex);});
  const animate=()=>{requestAnimationFrame(animate);if(!dragging)cityGroup.rotation.y+=.00035;renderer.render(scene,camera);};animate();
  new ResizeObserver(()=>{if(!renderer)return;camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix();renderer.setSize(stage.clientWidth,stage.clientHeight);}).observe(stage);
  $('reset-view').onclick=()=>{cityGroup.rotation.set(0,0,0);camera.position.set(13,16,18);camera.lookAt(0,0,0);};
  $('zoom-in').onclick=()=>{camera.position.multiplyScalar(.88);};$('zoom-out').onclick=()=>{camera.position.multiplyScalar(1.12);};
}
try{initCity();}catch(err){$('stage-loading').textContent='3D view unavailable in this browser. Try a WebGL-enabled browser.';console.error(err);}
setDistrict(0);

$('growth').addEventListener('input',e=>$('growth-label').textContent=`+${e.target.value}%`);
$('run-scenario').addEventListener('click',async()=>{
  const district=$('scenario-district').value;const growth=Number($('growth').value);const btn=$('run-scenario');btn.disabled=true;btn.textContent='Calculating…';
  try{
    const response=await fetch(`${API}/simulate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({district_id:district,population_change_percent:growth})});
    if(!response.ok)throw new Error(`API returned ${response.status}`);const data=await response.json();
    const metrics=data.metrics||data.impacts||data;const items=Object.entries(metrics).filter(([,v])=>typeof v==='number').slice(0,3);
    const metricCards=[['TRAFFIC',data.traffic],['WATER',data.water],['ELECTRICITY',data.electricity]];
    $('scenario-output').innerHTML=`<div class="risk-line">Impact level: <strong>${escapeHtml(data.risk_level)}</strong></div><div class="result-grid">${metricCards.map(([label,m])=>`<div class="result-item"><span>${label} · ${escapeHtml(m.unit)}</span><strong>${fmt(m.projected)}</strong><em>${m.change_percent>=0?'+':''}${m.change_percent}% vs baseline</em></div>`).join('')}</div><p class="assumption-note">${data.assumptions.map(escapeHtml).join(' ')}</p>`;
  }catch(err){$('scenario-output').innerHTML=`<div class="output-placeholder">Could not reach the simulation API. Start the backend at <code>${API}</code>. Details: ${err.message}</div>`;}
  finally{btn.disabled=false;btn.innerHTML='Run simulation <span>→</span>';}
});
// Personal scenario history is isolated by the authenticated workspace API.
let cachedWorkspaceScenarios = [];
async function refreshScenarioHistory(){
  const host=$('scenario-history');
  if (!authToken) { host.innerHTML='<div class="auth-required-note">Sign in to save and view your private scenarios.</div>'; return; }
  try{
    const response=await authFetch('/workspace/scenarios');if(!response.ok)throw new Error(`API returned ${response.status}`);
    const payload=await response.json();cachedWorkspaceScenarios=payload.scenarios||[];
    if(!cachedWorkspaceScenarios.length){host.innerHTML='<div class="output-placeholder">No saved scenarios in your workspace yet.</div>';return;}
    host.innerHTML=cachedWorkspaceScenarios.map(item=>`<div class="saved-scenario"><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.request.district_id)} · +${item.request.population_change_percent}% population · ${new Date(item.created_at*1000).toLocaleString()}</small></div><div class="saved-actions"><label title="Select for comparison"><input type="checkbox" class="compare-choice" value="${escapeHtml(item.id)}" aria-label="Select ${escapeHtml(item.name)} for comparison"></label><a class="secondary-button report-link" href="${API}/workspace/scenarios/${encodeURIComponent(item.id)}/report.pdf" target="_blank" rel="noopener" data-private-report="${escapeHtml(item.id)}">PDF report</a><button class="secondary-button" data-delete-scenario="${escapeHtml(item.id)}">Delete</button></div></div>`).join('');
  }catch(err){host.innerHTML=`<div class="output-placeholder">Could not load your workspace history: ${escapeHtml(err.message)}</div>`;}
}
$('save-scenario').addEventListener('click',async()=>{
  const button=$('save-scenario');button.disabled=true;
  try{
    if(!authToken)throw new Error('Sign in to save a private scenario.');
    const response=await authFetch('/workspace/scenarios',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('scenario-name').value,request:{district_id:$('scenario-district').value,population_change_percent:Number($('growth').value)}})});
    const data=await response.json();if(!response.ok)throw new Error(data.detail||`API returned ${response.status}`);
    $('scenario-output').insertAdjacentHTML('beforeend',`<p class="caveat">Saved privately as ${escapeHtml(data.name)}.</p>`);await refreshScenarioHistory();
  }catch(err){$('scenario-output').insertAdjacentHTML('beforeend',`<p class="caveat">Save failed: ${escapeHtml(err.message)}</p>`);}
  finally{button.disabled=false;}
});
$('scenario-history').addEventListener('click',async e=>{
  const report=e.target.closest('[data-private-report]');
  if(report){e.preventDefault();try{const response=await authFetch(`/workspace/scenarios/${encodeURIComponent(report.dataset.privateReport)}/report.pdf`);if(!response.ok)throw new Error(`API returned ${response.status}`);const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='lifeos-private-scenario.pdf';link.click();URL.revokeObjectURL(url);}catch(error){$('scenario-compare').textContent=`PDF export failed: ${error.message}`;}return;}
  const button=e.target.closest('[data-delete-scenario]');if(!button)return;
  button.disabled=true;
  try{const response=await authFetch(`/workspace/scenarios/${encodeURIComponent(button.dataset.deleteScenario)}`,{method:'DELETE'});if(!response.ok)throw new Error(`API returned ${response.status}`);$('scenario-compare').innerHTML='';await refreshScenarioHistory();}
  catch(err){button.disabled=false;button.textContent='Retry';console.error(err);}
});
$('scenario-history').addEventListener('change',e=>{
  if(!e.target.matches('.compare-choice'))return;
  const ids=[...$('scenario-history').querySelectorAll('.compare-choice:checked')].map(x=>x.value);
  if(ids.length<2){$('scenario-compare').innerHTML='<p class="caveat">Select at least two scenarios to compare.</p>';return;}
  if(ids.length>5){e.target.checked=false;$('scenario-compare').innerHTML='<p class="caveat">Compare up to five scenarios at a time.</p>';return;}
  const chosen=cachedWorkspaceScenarios.filter(item=>ids.includes(item.id));
  const metricKeys=['traffic','water','electricity'];
  const labels={traffic:'Traffic',water:'Water',electricity:'Electricity'};
  const cards=metricKeys.map(key=>{const values=chosen.map(item=>({name:item.name,value:item.result[key].projected,unit:item.result[key].unit}));const nums=values.map(v=>v.value);return `<div class="compare-card"><span>${labels[key]} · ${escapeHtml(values[0].unit)}</span><strong>${fmt(Math.min(...nums))} – ${fmt(Math.max(...nums))}</strong><small>Spread: ${fmt(Math.max(...nums)-Math.min(...nums))} · ${values.length} scenarios</small></div>`;}).join('');
  $('scenario-compare').innerHTML=`<div class="eyebrow">PRIVATE WORKSPACE COMPARISON</div><div class="compare-grid">${cards}</div><button class="secondary-button" id="download-private-comparison">Download comparison PDF</button>`;
  $('download-private-comparison').addEventListener('click',async()=>{try{const response=await authFetch('/workspace/scenarios/compare/report.pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario_ids:ids})});if(!response.ok)throw new Error(`API returned ${response.status}`);const blob=await response.blob();const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='lifeos-private-comparison.pdf';link.click();URL.revokeObjectURL(url);}catch(error){$('scenario-compare').insertAdjacentHTML('beforeend',`<p class="caveat">PDF export failed: ${escapeHtml(error.message)}</p>`);}});
});
$('export-scenarios').addEventListener('click',()=>{
  if(!cachedWorkspaceScenarios.length){$('scenario-compare').innerHTML='<p class="caveat">There are no private scenarios to export.</p>';return;}
  const rows=[['scenario_id','name','created_at','district_id','population_change_percent','traffic_projected','water_projected','electricity_projected'],...cachedWorkspaceScenarios.map(item=>[item.id,item.name,new Date(item.created_at*1000).toISOString(),item.request.district_id,item.request.population_change_percent,item.result.traffic.projected,item.result.water.projected,item.result.electricity.projected])];
  const csv=rows.map(row=>row.map(value=>`"${String(value??'').replaceAll('"','""')}"`).join(',')).join('\n');const blob=new Blob([csv],{type:'text/csv'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='lifeos-private-scenarios.csv';link.click();URL.revokeObjectURL(url);
});

async function refreshPrivateDocuments(){
  const host=$('private-document-list');if(!authToken){host.textContent='Sign in to view your notes.';return;}
  try{const response=await authFetch('/workspace/documents');if(!response.ok)throw new Error(`API returned ${response.status}`);const data=await response.json();const docs=data.documents||[];host.innerHTML=docs.length?docs.map(doc=>`<div class="private-document-item"><div><strong>${escapeHtml(doc.title)}</strong><small>${escapeHtml(doc.domain)} · ${doc.characters} characters</small></div><button class="secondary-button" data-delete-document="${escapeHtml(doc.id)}">Delete</button></div>`).join(''):'<span class="muted">No private notes saved.</span>';}
  catch(error){host.textContent=`Could not load private notes: ${error.message}`;}
}
$('private-document-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;
  try{const response=await authFetch('/workspace/documents',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('private-document-title').value,domain:$('private-document-domain').value,text:$('private-document-text').value})});const data=await response.json();if(!response.ok)throw new Error(data.detail||`API returned ${response.status}`);$('private-document-title').value='';$('private-document-text').value='';await refreshPrivateDocuments();}
  catch(error){$('private-document-list').textContent=`Could not save note: ${error.message}`;}
  finally{button.disabled=false;}
});
$('private-document-list').addEventListener('click',async e=>{const button=e.target.closest('[data-delete-document]');if(!button)return;button.disabled=true;try{const response=await authFetch(`/workspace/documents/${encodeURIComponent(button.dataset.deleteDocument)}`,{method:'DELETE'});if(!response.ok)throw new Error(`API returned ${response.status}`);await refreshPrivateDocuments();}catch(error){button.disabled=false;button.textContent='Retry';}});
$('private-knowledge-form').addEventListener('submit',async e=>{
  e.preventDefault();const question=$('private-knowledge-question').value.trim();const output=$('private-knowledge-output');if(!question)return;output.textContent='Searching only your private notes…';
  try{const response=await authFetch('/workspace/knowledge/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,limit:5})});const data=await response.json();if(!response.ok)throw new Error(data.detail||`API returned ${response.status}`);const sources=data.sources||[];output.innerHTML=`<div class="answer">${escapeHtml(data.answer)}</div>${sources.map(source=>`<div class="source">${escapeHtml(source.title)} · ${escapeHtml(source.domain)} · score ${source.score}</div>`).join('')}<p class="caveat">${escapeHtml(data.caveat)}</p>`;}
  catch(error){output.textContent=`Private search failed: ${error.message}`;}
});

async function refreshPrivateAgentMemories(){
  const target=$('private-agent-memory-list');if(!target)return;
  try{const response=await authFetch('/workspace/agents/memories');const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not load memory');
    target.innerHTML=(data.memories||[]).map(item=>`<div class="private-document-item"><div><strong>${escapeHtml(item.question)}</strong><span>${escapeHtml(item.district_id)} · ${item.verification_passed?'verified':'needs review'}</span><p>${escapeHtml(item.recommendation||'')}</p></div><button class="text-button" data-delete-agent-memory="${escapeHtml(item.id)}" type="button">Delete</button></div>`).join('')||'<span class="muted">No saved investigations yet.</span>';
  }catch(error){target.textContent=`Could not load agent memory: ${error.message}`;}
}
$('private-agent-memory-list')?.addEventListener('click',async e=>{const button=e.target.closest('[data-delete-agent-memory]');if(!button)return;button.disabled=true;try{const response=await authFetch(`/workspace/agents/memories/${encodeURIComponent(button.dataset.deleteAgentMemory)}`,{method:'DELETE'});if(!response.ok)throw new Error(`API returned ${response.status}`);await refreshPrivateAgentMemories();}catch(error){button.disabled=false;button.textContent='Retry';}});

$('private-investigation-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=$('private-investigate-button');const output=$('private-investigation-output');const question=$('private-investigation-question').value.trim();if(!question)return;
  button.disabled=true;button.textContent='Investigating privately…';output.textContent='Planning tasks, searching only your private notes and calculating city impacts…';
  try{
    const response=await authFetch('/workspace/agents/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,remember:$('private-investigation-remember').checked,scenario:{district_id:$('private-investigation-district').value,population_change_percent:Number($('private-investigation-growth').value)}})});
    const data=await response.json();if(!response.ok)throw new Error(data.detail||`API returned ${response.status}`);
    output.innerHTML=renderInvestigation(data,'Private evidence');await refreshPrivateAgentMemories();
  }catch(error){output.textContent=`Private investigation failed: ${error.message}`;}
  finally{button.disabled=false;button.textContent='Run private investigation →';}
});
$('private-investigation-growth').addEventListener('input',e=>$('private-investigation-growth-label').textContent=`+${e.target.value}%`);

$('knowledge-form').addEventListener('submit',async e=>{
  e.preventDefault();const q=$('knowledge-question').value.trim();if(!q)return;$('knowledge-output').textContent='Searching city knowledge…';
  try{const response=await fetch(`${API}/knowledge/query`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,limit:4})});if(!response.ok)throw new Error(`API returned ${response.status}`);const data=await response.json();const sources=data.sources||data.documents||[];const answer=data.answer||data.response||'No supported answer found.';$('knowledge-output').innerHTML=`<div class="answer">${escapeHtml(answer)}</div>${sources.map(s=>`<span class="source">${escapeHtml(s.id||s.title||'SOURCE')}</span>`).join('')}<p class="caveat">${escapeHtml(data.caveat||'')}</p>`;
  }catch(err){$('knowledge-output').textContent=`Could not reach the knowledge API. Start the backend at ${API}. ${err.message}`;}
});
function escapeHtml(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function addAuditExport(container, resultPayload, endpoint='/agents/investigate/report.pdf') {
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'secondary-button'; button.textContent = 'Download investigation audit PDF';
  button.addEventListener('click', async () => {
    button.disabled = true; button.textContent = 'Preparing audit PDF…';
    try {
      const response = await fetch(`${API}${endpoint}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(resultPayload)});
      if (!response.ok) { const err = await response.json().catch(()=>({})); throw new Error(err.detail || `API returned ${response.status}`); }
      const blob = await response.blob(); const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = 'lifeos-investigation-audit.pdf'; link.click(); URL.revokeObjectURL(url);
    } catch (error) { alert(`Could not export audit report: ${error.message}`); }
    finally { button.disabled = false; button.textContent = 'Download investigation audit PDF'; }
  });
  container.appendChild(button);
}
function renderInvestigation(data,evidenceLabel){
  const planner=data.planner||{};
  const checks=data.verification?.checks||{};
  const tasks=[...(data.execution_plan||[])].sort((a,b)=>(a.execution_order||0)-(b.execution_order||0));
  const execution=data.execution_run||{};
  const runtimeRows=(execution.trace||[]).map(item=>`<div><b>${escapeHtml(item.task_id)} · ${escapeHtml(item.agent)}</b><span>${escapeHtml(item.status)} · ${Number(item.duration_ms||0).toFixed(2)} ms</span><p>${escapeHtml((item.output_keys||[]).join(', ')||item.error||'No output')}</p></div>`).join('');
  const checkRows=Object.entries(checks).map(([name,passed])=>`<div><b>${escapeHtml(name.replaceAll('_',' '))}</b><span>${passed?'PASS':'FAIL'}</span></div>`).join('');
  const taskRows=tasks.map(task=>`<div><b>${escapeHtml(`${task.execution_order}. ${task.agent}`)}</b><span>${escapeHtml(task.tool||'analysis')}</span><p>${escapeHtml(task.objective)}</p></div>`).join('');
  const traceRows=(data.execution_trace||[]).map(step=>`<div><b>${escapeHtml(step.agent)}</b><span>${escapeHtml(step.status)}</span><p>${escapeHtml(step.summary)}</p></div>`).join('');
  const decisions=data.decision_analysis||{};
  const decisionRows=(decisions.ranking||[]).map(option=>`<div><b>#${Number(option.rank)} · ${escapeHtml(option.label)}</b><span>Score ${Number(option.score).toFixed(2)}/100 · ${escapeHtml(option.risk_level)} risk</span><p>Traffic ${Number(option.metrics?.traffic?.change_percent||0).toFixed(2)}% · Water ${Number(option.metrics?.water?.change_percent||0).toFixed(2)}% · Electricity ${Number(option.metrics?.electricity?.change_percent||0).toFixed(2)}%</p></div>`).join('');
  const debate=data.specialist_debate||{};
  const specialistRows=(debate.agents||[]).map(agent=>`<div><b>${escapeHtml(agent.label)}</b><span>Prefers ${escapeHtml(agent.preferred_option_id)} · score ${Number(agent.preferred_option_score).toFixed(2)}</span><p>${escapeHtml(agent.reason)} ${escapeHtml(agent.main_concern)}</p></div>`).join('');
  const dissentRows=(debate.dissent||[]).map(item=>`<p class="caveat">Dissent: ${escapeHtml(item.agent)} prefers ${escapeHtml(item.preferred_option)} — ${escapeHtml(item.reason)}</p>`).join('');
  return `<div class="answer"><strong>Recommendation</strong><p>${escapeHtml(data.recommendation)}</p></div>
    ${decisions.ranking?`<details class="investigation-details" open><summary>Decision options — recommended: ${escapeHtml(decisions.recommended_option||'not available')}</summary><p class="caveat">${escapeHtml(decisions.objective||'')} Score method: ${escapeHtml(decisions.method||'')}</p><div class="trace-list">${decisionRows}</div><p class="caveat">${escapeHtml(decisions.caveat||'')}</p>${(decisions.trade_offs||[]).map(item=>`<p class="caveat">${escapeHtml(item)}</p>`).join('')}</details>`:''}
    ${debate.agents?`<details class="investigation-details" open><summary>Multi-agent debate — ${escapeHtml(debate.consensus_option||'No consensus')} (${Number(debate.consensus_vote_count||0)}/${Number(debate.consensus_agent_count||0)} votes)</summary><p class="caveat">Consensus strength: ${escapeHtml(debate.consensus_strength||'not available')}. ${escapeHtml(debate.explanation||'')}</p><div class="trace-list">${specialistRows}</div>${dissentRows}${(debate.challenges||[]).map(item=>`<p class="caveat">${escapeHtml(item.from_agent)} challenged ${escapeHtml(item.to_agent)}: ${escapeHtml(item.challenge)} ${escapeHtml(item.resolution)}</p>`).join('')}<p class="caveat">${escapeHtml(debate.caveat||'')}</p></details>`:''}
    <div class="result-grid">${(data.findings||[]).map(f=>`<div class="result-item"><span>AGENT FINDING</span><strong>${escapeHtml(f)}</strong></div>`).join('')}</div>
    <div class="agent-meta"><strong>Verification: ${data.verification?.passed?'PASSED':'NEEDS REVIEW'}</strong><span>Intent: ${escapeHtml(planner.intent||'not reported')}</span><span>Focus: ${escapeHtml((planner.focus_domains||[]).join(', ')||'all domains')}</span><span>Evidence scope: ${escapeHtml(data.knowledge_scope)}</span><span>LLM: ${escapeHtml(data.llm_status||'not used')}</span></div>
    <div class="agent-meta"><strong>Task execution: ${escapeHtml(execution.status||'not reported')}</strong><span>${Number(execution.completed_count||0)}/${Number(execution.task_count||0)} tasks completed</span><span>${Number(execution.failed_count||0)} failed · ${Number(execution.skipped_count||0)} skipped</span></div>
    <details class="investigation-details"><summary>Execution plan (${tasks.length} tasks)</summary><div class="trace-list">${taskRows}</div></details>
    <details class="investigation-details"><summary>Task execution details</summary><div class="trace-list">${runtimeRows||'<p>No execution details available.</p>'}</div></details>
    <details class="investigation-details"><summary>Verification checks (${Object.values(checks).filter(Boolean).length}/${Object.keys(checks).length} passed)</summary><div class="trace-list">${checkRows}</div></details>
    <details class="investigation-details"><summary>Execution trace</summary><div class="trace-list">${traceRows}</div></details>
    ${data.memory_context?`<details class="investigation-details" open><summary>Agent memory (${Number(data.memory_context.count||0)} related prior investigations)</summary><p class="caveat">${escapeHtml(data.memory_context.note||'Historical context only.')}</p>${(data.memory_context.matches||[]).map(item=>`<div class="trace-list"><div><b>${escapeHtml(item.question)}</b><span>${escapeHtml(item.district_id)} · similarity ${Number(item.similarity||0).toFixed(2)}</span><p>${escapeHtml(item.recommendation||'No recommendation recorded.')}</p>${Object.entries(item.comparison||{}).map(([domain,values])=>`<p>${escapeHtml(domain)}: previous ${Number(values.previous_projected).toLocaleString()} → current ${Number(values.current_projected).toLocaleString()} (${Number(values.absolute_change)>=0?'+':''}${Number(values.absolute_change).toLocaleString()})</p>`).join('')}</div></div>`).join('')||'<p>No related previous investigation found.</p>'}<p class="caveat">${data.memory_saved?'This investigation was saved to your private memory.':'This investigation was not saved.'}</p></details>`:''}
    <div class="source-list" data-audit-run="${escapeHtml(data.audit_metadata?.run_id||'')}">Audit run ${escapeHtml(data.audit_metadata?.run_id||'not recorded')} · input SHA-256 ${escapeHtml(data.audit_metadata?.input_sha256||'not recorded')}</div>
    <div class="source-list">${escapeHtml(evidenceLabel)}: ${(data.evidence_ids||[]).map(escapeHtml).join(', ') || 'No matching source documents retrieved'}</div>
    <p class="caveat">${escapeHtml(data.knowledge_caveat||'')}</p><p class="caveat">${(data.limitations||[]).map(escapeHtml).join(' ')}</p>`;
}
$('focus-scenarios').onclick=()=>document.getElementById('scenario-section').scrollIntoView({behavior:'smooth'});$('focus-knowledge').onclick=()=>document.getElementById('knowledge-section').scrollIntoView({behavior:'smooth'});

// Agent investigation: combines the planner, knowledge retrieval, simulation and verification APIs.
$('investigation-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = $('investigation-question').value.trim();
  const district = $('investigation-district').value;
  const growth = Number($('investigation-growth').value);
  const output = $('investigation-output');
  const button = $('investigate-button');
  if (!question) return;
  button.disabled = true; button.textContent = 'Investigating…';
  output.textContent = 'Planning tasks, retrieving evidence and calculating impacts…';
  try {
    const response = await fetch(`${API}/agents/investigate`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({question, scenario:{district_id:district, population_change_percent:growth}})
    });
    if (!response.ok) { const err = await response.json().catch(()=>({})); throw new Error(err.detail || `API returned ${response.status}`); }
    const data = await response.json();
    output.innerHTML = renderInvestigation(data,'Evidence');
    addAuditExport(output, data);
  } catch (err) { output.textContent = `Investigation unavailable: ${err.message}. Check that the API is running at ${API}.`; }
  finally { button.disabled = false; button.textContent = 'Run investigation →'; }
});
$('investigation-growth').addEventListener('input', e => $('investigation-growth-label').textContent = `+${e.target.value}%`);

// Load baseline values from the API so the dashboard and backend share one source of truth.
(async function loadCityData(){
  try {
    const response = await fetch(`${API}/city`); if (!response.ok) throw new Error(`API returned ${response.status}`);
    const city = await response.json();
    const total = city.districts.reduce((sum, d) => sum + d.population, 0);
    $('population').textContent = fmt(total);
    $('city-api-status').textContent = 'API CONNECTED';
    $('scenario-district').value = 'CENTRAL'; $('investigation-district').value = 'CENTRAL';
  } catch (_) { $('city-api-status').textContent = 'API OFFLINE · DEMO VALUES'; }
})();

// Account controls: tokens live only for this browser tab/session.
$('auth-switch').addEventListener('click',()=>{authMode=authMode==='login'?'register':'login';renderAuthMode();});
$('auth-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=$('auth-submit');button.disabled=true;showAuthError();
  const path=authMode==='login'?'/auth/login':'/auth/register';
  try{const response=await fetch(`${API}${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:$('auth-email').value,password:$('auth-password').value})});const payload=await response.json();if(!response.ok)throw new Error(payload.detail||`API returned ${response.status}`);await establishSession(payload);$('auth-password').value='';}
  catch(error){showAuthError(error.message);}
  finally{button.disabled=false;}
});
$('logout-button').addEventListener('click',()=>{authToken='';currentUser=null;sessionStorage.removeItem('lifeos_access_token');cachedWorkspaceScenarios=[];$('user-email').textContent='SIGNED OUT';$('scenario-history').innerHTML='<div class="auth-required-note">Sign in to view your private scenarios.</div>';$('private-document-list').textContent='Sign in to view your notes.';$('scenario-compare').innerHTML='';setAuthVisible(true);});
renderAuthMode();validateSession();

// Milestone 22: transparent multi-option what-if exploration.
$('run-whatif').addEventListener('click', async () => {
  const button = $('run-whatif'); const host = $('whatif-output');
  const district = $('scenario-district').value;
  const specs = [
    ['a', 'reference', 'Current plan'],
    ['b', 'growth', 'Growth option'],
    ['c', 'green_focus', 'Green focus'],
  ];
  const options = specs.map(([key, option_id, label]) => ({
    option_id, label, scenario: {
      district_id: district,
      population_change_percent: Number($(`whatif-${key}-pop`).value),
      commercial_growth_percent: Number($(`whatif-${key}-com`).value),
      green_space_change_percent: Number($(`whatif-${key}-green`).value),
    },
  }));
  button.disabled = true; button.textContent = 'Comparing…';
  host.textContent = 'Calculating options with the deterministic city model…';
  try {
    const response = await fetch(`${API}/scenarios/explore`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({options})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API returned ${response.status}`);
    const rows = data.options.map(option => `<div class="whatif-result"><strong>${escapeHtml(option.label)}</strong><span>${escapeHtml(option.result.risk_level)} risk</span><div class="whatif-metrics">${['traffic','water','electricity'].map(key => `<div><small>${key}</small><b>${fmt(option.deltas[key].projected)}</b><em>${option.deltas[key].change_percent>=0?'+':''}${option.deltas[key].change_percent}% vs baseline</em><small>Δ ${option.deltas[key].difference_from_first>=0?'+':''}${fmt(option.deltas[key].difference_from_first)} vs reference</small></div>`).join('')}</div></div>`).join('');
    host.innerHTML = `<div class="whatif-results">${rows}</div><p class="caveat">${escapeHtml(data.comparison_note)}</p><p class="caveat">${data.limitations.map(escapeHtml).join(' ')}</p>`;
  } catch (error) { host.textContent = `Comparison failed: ${error.message}`; }
  finally { button.disabled = false; button.textContent = 'Compare options →'; }
});

// Milestone 23: transparent compound-growth forecasting from a simulated scenario.
$('run-forecast').addEventListener('click', async () => {
  const button = $('run-forecast'); const host = $('forecast-output');
  const values = {
    years: Number($('forecast-years').value),
    traffic_annual_growth_percent: Number($('forecast-traffic').value),
    water_annual_growth_percent: Number($('forecast-water').value),
    electricity_annual_growth_percent: Number($('forecast-electricity').value),
  };
  const scenario = {
    district_id: $('scenario-district').value,
    population_change_percent: Number($('growth').value),
    commercial_growth_percent: 0,
    green_space_change_percent: 0,
  };
  button.disabled = true; button.textContent = 'Projecting…';
  host.textContent = 'Calculating the scenario timeline…';
  try {
    const response = await fetch(`${API}/forecasts/project`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({...values, scenario})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API returned ${response.status}`);
    const metrics = ['traffic','water','electricity'];
    const rows = data.timeline.map(point => `<tr><td>Year ${point.year}</td>${metrics.map(key => `<td>${fmt(point.metrics[key].projected)}<small>${point.metrics[key].change_from_scenario_start_percent>=0?'+':''}${point.metrics[key].change_from_scenario_start_percent}%</small></td>`).join('')}</tr>`).join('');
    host.innerHTML = `<p class="caveat">${escapeHtml(data.method)} Year 0 is the selected scenario result.</p><div class="forecast-table-wrap"><table class="forecast-table"><thead><tr><th>Timeline</th><th>Traffic</th><th>Water</th><th>Electricity</th></tr></thead><tbody>${rows}</tbody></table></div><p class="caveat">Annual assumptions: traffic ${data.annual_growth_assumptions.traffic}%, water ${data.annual_growth_assumptions.water}%, electricity ${data.annual_growth_assumptions.electricity}%.</p><p class="caveat">${data.limitations.map(escapeHtml).join(' ')}</p>`;
  } catch (error) { host.textContent = `Forecast failed: ${error.message}`; }
  finally { button.disabled = false; button.textContent = 'Generate forecast →'; }
});


// Milestone 24: fetch separately attributed live weather context from Open-Meteo.
$('fetch-weather').addEventListener('click', async () => {
  const button = $('fetch-weather'); const host = $('weather-output');
  const latitude = Number($('weather-latitude').value);
  const longitude = Number($('weather-longitude').value);
  if ($('weather-latitude').value.trim() === '' || $('weather-longitude').value.trim() === '' || !Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    host.textContent = 'Enter a valid latitude (-90 to 90) and longitude (-180 to 180).';
    return;
  }
  button.disabled = true; button.textContent = 'Fetching…';
  host.textContent = 'Requesting a current snapshot from Open-Meteo…';
  try {
    const response = await fetch(`${API}/data-sources/open-meteo/current`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({latitude, longitude})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API returned ${response.status}`);
    const weather = data.current;
    host.innerHTML = `<div class="weather-result"><div><small>TEMPERATURE</small><strong>${escapeHtml(weather.temperature_c)} °C</strong></div><div><small>HUMIDITY</small><strong>${escapeHtml(weather.relative_humidity_percent)}%</strong></div><div><small>PRECIPITATION</small><strong>${escapeHtml(weather.precipitation_mm)} mm</strong></div><div><small>WIND</small><strong>${escapeHtml(weather.wind_speed_kmh)} km/h</strong></div></div><p class="caveat">Observed at ${escapeHtml(data.observed_at)} (${escapeHtml(data.timezone)}). Coordinates: ${escapeHtml(data.coordinates.latitude)}, ${escapeHtml(data.coordinates.longitude)}.</p><p class="caveat">${escapeHtml(data.attribution)} · ${escapeHtml(data.usage_note)}</p>`;
  } catch (error) { host.textContent = `External data request failed: ${error.message}`; }
  finally { button.disabled = false; button.textContent = 'Fetch live weather →'; }
});

// Milestone 25: import infrastructure observations with explicit provenance.
const infraImportButton = $('import-infrastructure');
if (infraImportButton) {
  infraImportButton.addEventListener('click', async () => {
    const output = $('infrastructure-import-output');
    infraImportButton.disabled = true;
    infraImportButton.textContent = 'Checking dataset…';
    try {
      let payload;
      try { payload = JSON.parse($('infrastructure-json').value); }
      catch { throw new Error('The dataset JSON is not valid. Check commas, quotes and braces.'); }
      const response = await fetch(`${API}/infrastructure-data/import`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Dataset import failed.');
      output.innerHTML = `<strong>${escapeHtml(result.dataset_name)}</strong><p>${escapeHtml(result.observation_count)} accepted · ${escapeHtml(result.rejected_count)} rejected · Status: ${escapeHtml(result.quality_status)}</p><p>${escapeHtml(result.integration_note)}</p>${(result.quality_issues || []).map(issue => `<p class="caveat">Row ${escapeHtml(issue.row ?? 'metadata')}: ${escapeHtml(issue.message)}</p>`).join('')}`;
      await refreshInfrastructureDatasets();
    } catch (error) {
      output.textContent = error.message || 'Could not import dataset.';
    } finally {
      infraImportButton.disabled = false;
      infraImportButton.textContent = 'Validate and import dataset →';
    }
  });
}

async function refreshInfrastructureDatasets() {
  const host = $('infrastructure-datasets');
  if (!host) return;
  try {
    const response = await fetch(`${API}/infrastructure-data`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Could not load datasets.');
    host.innerHTML = result.datasets.length ? result.datasets.map(item => `<article class="dataset-item"><strong>${escapeHtml(item.dataset_name)}</strong><span>${escapeHtml(item.domain)} · ${escapeHtml(item.provider)} · ${escapeHtml(item.observation_count)} observations</span><span>${escapeHtml(item.quality_status)} · as of ${escapeHtml(item.data_as_of)}</span></article>`).join('') : 'No datasets imported in this API session.';
  } catch (error) { host.textContent = error.message || 'Could not load datasets.'; }
}
const refreshInfraButton = $('refresh-infrastructure');
if (refreshInfraButton) refreshInfraButton.addEventListener('click', refreshInfrastructureDatasets);
if ($('infrastructure-datasets')) refreshInfrastructureDatasets();
