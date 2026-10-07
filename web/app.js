const $ = (id) => document.getElementById(id);
const state = { scenario: 'growth-reliability', result: null };
const scenarios = [
  ['growth-reliability','↗','Growth vs reliability','Lift with a hidden cost'],
  ['healthy-winner','✓','Healthy winner','Clear, balanced gains'],
  ['allocation-drift','!','Allocation drift','The deceptive test'],
  ['noisy-experiment','~','Noisy experiment','Know when to wait'],
];
const fmtPct = (value, digits=2) => value == null ? '—' : `${(value*100).toFixed(digits)}%`;
const fmtNum = (value) => new Intl.NumberFormat('en-GB').format(value ?? 0);
const escapeHtml = (s) => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function api(path, options={}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(()=>({}));
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body));
  return body;
}

function renderScenarios(){
  $('scenario-list').innerHTML = scenarios.map(([id,icon,name,desc]) => `<div class="scenario ${state.scenario===id?'active':''}" data-id="${id}"><div class="scenario-icon">${icon}</div><div><strong>${name}</strong><small>${desc}</small></div><span class="radio"></span></div>`).join('');
  document.querySelectorAll('.scenario').forEach(el => el.onclick = () => { state.scenario=el.dataset.id; renderScenarios(); });
}

function verdictKind(result){ return result.verdict === 'ship' ? ['SHIP / RELEASE','↗'] : result.verdict === 'hold' ? ['STOP / GUARDRAIL','↘'] : ['WAIT / EVIDENCE','~']; }

function renderResult(r, mode='SYNTHETIC DEMO'){
  state.result = r;
  const [label, icon] = verdictKind(r);
  $('hero-confidence').innerHTML = `${r.confidence_score}<sup>%</sup>`;
  $('data-mode').textContent = mode;
  $('run-id').textContent = `RUN / ${r.run_id.slice(0,12).toUpperCase()}`;
  const banner = $('verdict-banner'); banner.className = `verdict-banner ${r.verdict}`;
  banner.querySelector('.verdict-icon').textContent = icon;
  $('verdict-type').textContent = label;
  $('verdict-title').textContent = r.verdict_title;
  $('verdict-reason').textContent = r.verdict_reason;
  $('control-rate').textContent = fmtPct(r.control.conversion_rate);
  $('control-n').textContent = `${fmtNum(r.control.assigned)} assigned users · A`;
  $('treatment-rate').textContent = fmtPct(r.treatment.conversion_rate);
  $('treatment-n').textContent = `${fmtNum(r.treatment.assigned)} assigned users · B`;
  $('lift').textContent = `${r.relative_lift_pct >= 0 ? '+' : ''}${r.relative_lift_pct.toFixed(2)}%`;
  $('ci').textContent = `95% CI ${r.confidence_interval_pp[0].toFixed(2)} to ${r.confidence_interval_pp[1].toFixed(2)} pp`;
  $('pvalue').textContent = r.p_value < .0001 ? '<0.0001' : r.p_value.toFixed(4);
  $('power').textContent = `${(r.estimated_power*100).toFixed(1)}%`;
  $('latency').textContent = `${r.latency_change_pct>=0?'+':''}${r.latency_change_pct.toFixed(1)}%`;
  $('srm').textContent = r.srm_p_value.toFixed(4);
  $('row-count').textContent = `${r.row_count} cohort rows`;
  renderChecks(r.checks); renderSegments(r.segments); renderChart(r.daily); loadHistory();
  const first = r.daily[0]?.date || '—', last = r.daily.at(-1)?.date || '—'; $('window-label').textContent = `Experiment window ${first} — ${last}`;
  showToast();
}

function renderChecks(checks){
  $('checks').innerHTML = checks.map(c => `<div class="check-item ${c.passed?'':'fail'}"><span class="check-icon">${c.passed?'✓':'!'}</span><div><b>${escapeHtml(c.name)}</b><small>${escapeHtml(c.detail)}</small></div></div>`).join('');
}
function renderSegments(segments){
  $('segments').innerHTML = segments.map(s => `<tr><td><b>${escapeHtml(s.segment)}</b></td><td>${fmtPct(s.control_rate)}</td><td>${fmtPct(s.treatment_rate)}</td><td>${s.relative_lift_pct==null?'—':`${s.relative_lift_pct>=0?'+':''}${s.relative_lift_pct.toFixed(1)}%`}</td><td>${s.adjusted_p_value.toFixed(4)}</td></tr>`).join('');
}
function renderChart(points){
  if (!points.length) return;
  const width=680,height=225,pad={l:42,r:16,t:12,b:27};
  const values = points.flatMap(p => [p.control_rate,p.treatment_rate]).filter(v=>v!=null).map(v=>v*100);
  let min=Math.floor(Math.min(...values)-1), max=Math.ceil(Math.max(...values)+1); if(max-min<4){min-=1;max+=1;}
  const x=i=>pad.l+i*(width-pad.l-pad.r)/Math.max(1,points.length-1); const y=v=>pad.t+(max-v*100)*(height-pad.t-pad.b)/(max-min);
  const path = key => points.map((p,i)=>`${i?'L':'M'} ${x(i).toFixed(1)} ${y(p[key]).toFixed(1)}`).join(' ');
  const grid=[]; for(let i=0;i<=4;i++){const val=min+(max-min)*i/4; const yy=pad.t+(4-i)*(height-pad.t-pad.b)/4; grid.push(`<line class="gridline" x1="${pad.l}" y1="${yy}" x2="${width-pad.r}" y2="${yy}"/><text class="axis-label" x="4" y="${yy+3}">${val.toFixed(1)}%</text>`)}
  const labels=points.map((p,i)=> i===0||i===points.length-1||i%3===0 ? `<text class="axis-label" x="${x(i)-14}" y="${height-6}">${p.date.slice(5)}</text>`:'').join('');
  const dots=points.map((p,i)=>`<circle class="point-treatment" cx="${x(i)}" cy="${y(p.treatment_rate)}" r="3.5"/>`).join('');
  $('chart').innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Control and treatment conversion rate over time">${grid.join('')}<path class="line-control" d="${path('control_rate')}"/><path class="line-treatment" d="${path('treatment_rate')}"/>${dots}${labels}</svg>`;
}
async function loadHistory(){
  try{ const items=await api('/api/history?limit=5'); $('history').innerHTML=items.map(h=>`<div class="history-item"><div><b>${escapeHtml(h.experiment_name)}</b><small>${new Date(h.created_at).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})}</small></div><span class="history-tag ${h.verdict}">${h.verdict.toUpperCase()}</span></div>`).join('') || '<p class="muted">No runs yet.</p>'; }catch(e){ $('history').innerHTML='<p class="muted">History unavailable.</p>'; }
}
function showToast(){ const t=$('toast'); t.classList.add('show'); clearTimeout(window._toast); window._toast=setTimeout(()=>t.classList.remove('show'),2600); }
async function runScenario(){
  $('run-btn').disabled=true; $('run-btn').textContent='Auditing evidence…';
  try{ const r=await api(`/api/scenarios/${state.scenario}`,{method:'POST'}); renderResult(r); }
  catch(e){ alert(e.message); }
  finally{ $('run-btn').disabled=false; $('run-btn').innerHTML='Run evidence audit <span>↗</span>'; }
}
async function importCsv(file){
  if(!file) return; const text=await file.text();
  try{ const r=await api(`/api/import/csv?experiment_name=${encodeURIComponent(file.name.replace(/\.csv$/i,''))}`,{method:'POST',headers:{'content-type':'text/csv'},body:text}); renderResult(r,'IMPORTED CSV'); }
  catch(e){ alert(`CSV import failed: ${e.message}`); }
}
function exportJson(){
  if(!state.result) return alert('Run an analysis first.');
  const blob=new Blob([JSON.stringify(state.result,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=`variantverdict-${state.result.run_id.slice(0,8)}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1000);
}

renderScenarios(); loadHistory();
$('run-btn').onclick=runScenario;
$('import-btn').onclick=()=>$('csv-file').click();
$('csv-file').onchange=e=>importCsv(e.target.files?.[0]);
$('export-btn').onclick=exportJson;
runScenario();
