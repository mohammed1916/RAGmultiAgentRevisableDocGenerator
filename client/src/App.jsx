import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { addEdge, Background, Controls, Handle, MarkerType, Position, ReactFlow, ReactFlowProvider, useEdgesState, useNodesState } from '@xyflow/react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  BarChart3, BookOpen, Bot, Check, ChevronDown, CircleDot, Clock3, Command, Cpu,
  FileText, GraduationCap, LayoutDashboard, Network, PanelLeft, Pencil, Play, Plus, RefreshCw, Search,
  Send, Sparkles, Target, Trash2, Upload, X, Zap,
} from 'lucide-react'
import { api, fileDownloadUrl } from './api'

function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" onClick={onClose}>
    <div className="modal" onClick={(event) => event.stopPropagation()}>
      <div className="modal-head"><h2>{title}</h2><button className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      {children}
    </div>
  </div>
}

function ConfirmDialog({ title, message, confirmLabel = 'Delete', onConfirm, onClose }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function confirm() {
    setBusy(true); setError('')
    try { await onConfirm() } catch (err) { setError(err.message); setBusy(false) }
  }
  return <Modal title={title} onClose={busy ? () => {} : onClose}>
    <div className="modal-form">
      <p className="confirm-message">{message}</p>
      {error && <p className="modal-error">{error}</p>}
      <div className="modal-actions"><button type="button" className="ghost" onClick={onClose} disabled={busy}>Cancel</button><button type="button" className="danger-action" onClick={confirm} disabled={busy}>{busy ? 'Deleting…' : confirmLabel}</button></div>
    </div>
  </Modal>
}

function NewProfileForm({ onCreate, onClose }) {
  const [form, setForm] = useState({ name: '', exam: '', target_date: '', daily_study_hours: 2, timezone: 'Asia/Kolkata' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))
  async function submit(event) {
    event.preventDefault()
    if (!form.name.trim() || busy) return
    setBusy(true); setError('')
    try {
      const payload = { ...form, daily_study_hours: Number(form.daily_study_hours) || 0 }
      if (!payload.target_date) delete payload.target_date
      if (!payload.exam) delete payload.exam
      await onCreate(payload)
    } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Profile name<input autoFocus value={form.name} onChange={set('name')} placeholder="e.g. Class 12 Boards" required /></label>
    <label>Exam / goal<input value={form.exam} onChange={set('exam')} placeholder="e.g. CBSE Boards, JEE Main" /></label>
    <div className="modal-row">
      <label>Target date<input type="date" value={form.target_date} onChange={set('target_date')} /></label>
      <label>Hours / day<input type="number" min="0" max="24" step="0.5" value={form.daily_study_hours} onChange={set('daily_study_hours')} /></label>
    </div>
    <label>Timezone<input value={form.timezone} onChange={set('timezone')} /></label>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Creating…' : 'Create profile'}</button></div>
  </form>
}

const navItems = [
  ['overview', 'Overview', LayoutDashboard], ['roadmap', 'Roadmap', Network],
  ['workspace', 'Workspace', FileText], ['planner', 'Planner', Target],
  ['review', 'Review', CircleDot], ['tutor', 'Tutor', Bot],
]

function GraphNode({ data }) {
  return <div className={`graph-node ${data.kind}`}>
    <Handle type="target" position={Position.Left} />
    <span className="graph-dot" style={{ '--progress': `${data.progress * 100}%` }} />
    <div><strong>{data.label}</strong><small>{Math.round(data.progress * 100)}% confident</small></div>
    <Handle type="source" position={Position.Right} />
  </div>
}
const graphTypes = { learning: GraphNode }

function StatusPill({ online, label }) {
  return <span className={`status-pill ${online ? 'online' : 'offline'}`}><i />{label}</span>
}

function ModelSelector() {
  const [options, setOptions] = useState([])
  const [active, setActive] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    api.listModels().then((data) => { setOptions(data.options || []); setActive(data.active || null) }).catch(() => {})
  }, [])
  const value = active ? `${active.mode}::${active.model}` : ''
  async function change(event) {
    const [mode, model] = event.target.value.split('::')
    setBusy(true)
    try { const next = await api.setModel(mode, model); setActive(next) } catch { /* ignore */ } finally { setBusy(false) }
  }
  if (!options.length) return null
  return <label className="model-selector" title="Model used by all agents">
    <Cpu size={14} />
    <select value={value} onChange={change} disabled={busy} aria-label="Active model">
      {options.map((o) => <option key={`${o.mode}::${o.model}`} value={`${o.mode}::${o.model}`}>{o.mode === 'cloud' ? '☁ ' : '🖥 '}{o.model}</option>)}
    </select>
  </label>
}

function Metric({ label, value, suffix, accent = 'cyan' }) {
  return <article className="metric"><span className={`metric-icon ${accent}`}><Zap size={16} /></span><div><small>{label}</small><strong>{value}<em>{suffix}</em></strong></div></article>
}

function EditProfileForm({ profile, onSave, onClose }) {
  const [form, setForm] = useState({
    name: profile.name || '', learner_name: profile.learner_name || '', exam: profile.exam || '',
    target_date: profile.target_date || '', daily_study_hours: profile.daily_study_hours ?? 0,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError('')
    try {
      const changes = { name: form.name, learner_name: form.learner_name || null, exam: form.exam || null, daily_study_hours: Number(form.daily_study_hours) || 0 }
      if (form.target_date) changes.target_date = form.target_date
      await onSave(changes)
    } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Your name<input autoFocus value={form.learner_name} onChange={set('learner_name')} placeholder="Shown in your greeting" /></label>
    <label>Profile name<input value={form.name} onChange={set('name')} required /></label>
    <label>Exam / goal<input value={form.exam} onChange={set('exam')} placeholder="e.g. CBSE Boards" /></label>
    <div className="modal-row">
      <label>Target date<input type="date" value={form.target_date} onChange={set('target_date')} /></label>
      <label>Hours / day<input type="number" min="0" max="24" step="0.5" value={form.daily_study_hours} onChange={set('daily_study_hours')} /></label>
    </div>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button></div>
  </form>
}

function GenerateButton({ label, busyLabel, onGenerate, onRefresh }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function run() {
    setBusy(true); setError('')
    try { await onGenerate(); await onRefresh() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <span className="generate-wrap">
    <button className="rebuild-button" onClick={run} disabled={busy}><Sparkles size={14} className={busy ? 'spinning' : ''}/> {busy ? busyLabel : label}</button>
    {error && <em className="generate-error">{error}</em>}
  </span>
}

function App() {
  const [profiles, setProfiles] = useState([])
  const [activeId, setActiveId] = useState('')
  const [data, setData] = useState(null)
  const [view, setView] = useState('overview')
  const [openProfiles, setOpenProfiles] = useState(false)
  const [showNewProfile, setShowNewProfile] = useState(false)
  const [showEditProfile, setShowEditProfile] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [infra, setInfra] = useState({ ollama: {}, milvus: {} })
  const [error, setError] = useState('')
  const searchRef = useRef(null)

  // Dismiss the search-results popover on outside click or Escape.
  useEffect(() => {
    if (results.length === 0) return undefined
    const onClick = (event) => { if (searchRef.current && !searchRef.current.contains(event.target)) setResults([]) }
    const onKey = (event) => { if (event.key === 'Escape') setResults([]) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onClick); document.removeEventListener('keydown', onKey) }
  }, [results.length])

  async function createProfile(payload) {
    const created = await api.createProfile(payload)
    const items = await api.listProfiles()
    setProfiles(items)
    setActiveId(created.profile_id)
    setShowNewProfile(false)
    setOpenProfiles(false)
  }

  async function editProfile(changes) {
    await api.updateProfile(activeId, changes)
    const items = await api.listProfiles()
    setProfiles(items)
    setShowEditProfile(false)
    refresh()
  }

  const refresh = useCallback(async (profileId = activeId) => {
    if (!profileId) return
    try { setData(await api.dashboard(profileId)); setError('') } catch (err) { setError(err.message) }
  }, [activeId])

  useEffect(() => {
    Promise.all([api.bootstrap(), api.infrastructure()]).then(([items, state]) => {
      setProfiles(items); setActiveId(items[0]?.profile_id || ''); setInfra(state)
    }).catch((err) => setError(`Cannot connect to the study service: ${err.message}`))
  }, [])
  useEffect(() => { refresh(activeId) }, [activeId, refresh])

  const activeProfile = profiles.find((profile) => profile.profile_id === activeId)
  const dueCount = data?.analytics.review_due || 0
  const completedPercent = data ? Math.round((data.analytics.tasks_completed / Math.max(data.analytics.task_total, 1)) * 100) : 0

  async function performSearch(event) {
    event.preventDefault()
    if (!query.trim() || !activeId) return
    setResults(await api.search(activeId, query))
  }
  async function moveTask(taskId, status) { await api.updateTask(activeId, taskId, status); refresh() }
  async function review(cardId, rating) { await api.review(activeId, cardId, rating); refresh() }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><GraduationCap size={21} /></span><span>atlas<span>study</span></span></div>
      <button className="profile-switcher" onClick={() => setOpenProfiles(!openProfiles)}>
        <span className="profile-orb">{activeProfile?.name?.slice(0, 1) || 'A'}</span><span><b>{activeProfile?.name || 'Loading profile'}</b><small>{activeProfile?.exam || 'Your study space'}</small></span><ChevronDown size={16} />
      </button>
      {openProfiles && <div className="profile-menu">{profiles.map((profile) => <button key={profile.profile_id} onClick={() => { setActiveId(profile.profile_id); setOpenProfiles(false) }}><span>{profile.name.slice(0, 1)}</span>{profile.name}</button>)}<button className="profile-menu-edit" onClick={() => { setShowEditProfile(true); setOpenProfiles(false) }}><span><Command size={13} /></span>Edit current profile</button><button className="profile-menu-add" onClick={() => { setShowNewProfile(true); setOpenProfiles(false) }}><span><Plus size={14} /></span>New profile</button></div>}
      <nav>{navItems.map(([id, label, Icon]) => <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}><Icon size={18} />{label}{id === 'review' && dueCount > 0 && <b className="count">{dueCount}</b>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="goal-box"><Target size={18}/><p>Target date</p><strong>{activeProfile?.target_date || 'Set a goal'}</strong><span>{activeProfile?.daily_study_hours || 0}h/day focus</span></div><StatusPill online={infra.ollama?.available} label={infra.ollama?.available ? 'AI ready' : 'AI offline'} /></div>
    </aside>
    <main className="main">
      <header className="topbar"><button className="mobile-menu"><PanelLeft size={20}/></button><form className="global-search" ref={searchRef} onSubmit={performSearch}><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this profile"/><kbd><Command size={11}/> K</kbd></form><div className="topbar-right"><ModelSelector /><StatusPill online={infra.milvus?.available} label={infra.milvus?.available ? 'Vector index' : 'Local search'} /><span className="avatar">A</span></div></header>
      {error && <div className="error-banner">{error}</div>}
      {results.length > 0 && <section className="search-results" onMouseDown={(event) => event.stopPropagation()}><b>Results in {activeProfile?.name}</b>{results.map((result) => <button key={result.document_id} onClick={() => { setView('workspace'); setResults([]) }}><FileText size={16}/><span>{result.title}<small>{result.subject} / {result.chapter}</small></span><em>{Math.round(result.score * 100)}%</em></button>)}</section>}
      {!data ? <div className="loading"><span className="loader"/>Opening your learning space...</div> : <PageContent view={view} data={data} activeId={activeId} onMoveTask={moveTask} onReview={review} onRefresh={refresh} />}
    </main>
    {showNewProfile && <Modal title="Create a learning profile" onClose={() => setShowNewProfile(false)}><NewProfileForm onCreate={createProfile} onClose={() => setShowNewProfile(false)} /></Modal>}
    {showEditProfile && activeProfile && <Modal title="Edit profile" onClose={() => setShowEditProfile(false)}><EditProfileForm profile={activeProfile} onSave={editProfile} onClose={() => setShowEditProfile(false)} /></Modal>}
  </div>
}

function greeting(name) {
  const hour = new Date().getHours()
  const part = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  return name ? `${part}, ${name}` : part
}

function PageContent({ view, data, activeId, onMoveTask, onReview, onRefresh }) {
  const learner = data.profile?.learner_name
  const heading = { overview: [greeting(learner), 'Your focus is clear. Keep the next move small and specific.'], roadmap: ['Learning roadmap', 'See prerequisite paths and your current confidence.'], workspace: ['Workspace', 'Write, connect, and retrieve notes without leaving your profile.'], planner: ['Study planner', 'Move work through the day as your plan evolves.'], review: ['Review queue', 'Retrieval practice scheduled for today.'], tutor: ['Study tutor', 'Ask against the notes and concepts in this profile.'] }[view]
  return <section className="page"><div className="page-heading"><div><h1>{heading[0]}</h1><p>{heading[1]}</p></div>{view === 'overview' && <button className="primary-action" onClick={() => document.querySelector('[data-tutor-input]')?.focus()}><Sparkles size={17}/> Ask Atlas</button>}</div>
    {view === 'overview' && <Overview data={data} activeId={activeId} onRefresh={onRefresh} />}
    {view === 'roadmap' && <Roadmap graph={data.graph} activeId={activeId} onRefresh={onRefresh} />}
    {view === 'workspace' && <Workspace data={data} activeId={activeId} onRefresh={onRefresh} />}
    {view === 'planner' && <Planner tasks={data.tasks} activeId={activeId} onMoveTask={onMoveTask} onRefresh={onRefresh} />}
    {view === 'review' && <Review cards={data.flashcards} activeId={activeId} onReview={onReview} onRefresh={onRefresh} />}
    {view === 'tutor' && <Tutor activeId={activeId} />}
  </section>
}

function SubjectForm({ subject, onSave, onClose }) {
  const [form, setForm] = useState({ name: subject?.name || '', progress: subject?.progress ?? 0, mastery: subject ? Math.round(subject.mastery * 100) : 0, color: subject?.color || '#0c8fa2' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }))
  async function submit(e) {
    e.preventDefault(); if (!form.name.trim() || busy) return
    setBusy(true); setError('')
    try { await onSave({ name: form.name.trim(), progress: Number(form.progress) || 0, mastery: (Number(form.mastery) || 0) / 100, color: form.color }) }
    catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Subject<input autoFocus value={form.name} onChange={set('name')} disabled={!!subject} required /></label>
    <div className="modal-row"><label>Coverage %<input type="number" min="0" max="100" value={form.progress} onChange={set('progress')} /></label><label>Mastery %<input type="number" min="0" max="100" value={form.mastery} onChange={set('mastery')} /></label></div>
    <label>Color<input type="color" value={form.color} onChange={set('color')} /></label>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button></div>
  </form>
}

function Overview({ data, activeId, onRefresh }) {
  const { analytics, subjects, tasks, flashcards } = data
  const [subjModal, setSubjModal] = useState(null)
  const [subjDelete, setSubjDelete] = useState(null)
  return <><div className="metrics-grid"><Metric label="Study time" value={`${Math.floor(analytics.study_minutes_this_week / 60)}h ${analytics.study_minutes_this_week % 60}m`} suffix="this week"/><Metric label="Current streak" value={analytics.streak} suffix="days" accent="orange"/><Metric label="Plan progress" value={`${analytics.tasks_completed}/${analytics.task_total}`} suffix="tasks" accent="violet"/><Metric label="Reviews due" value={analytics.review_due} suffix="cards" accent="green"/></div>
  <div className="overview-grid"><section className="panel activity-panel"><div className="panel-title"><div><h2>Learning rhythm</h2><p>Focused study minutes this week</p></div><span className={`trend ${analytics.trend_percent < 0 ? 'down' : ''}`}>{analytics.trend_percent > 0 ? '+' : ''}{analytics.trend_percent ?? 0}% <small>vs last week</small></span></div><div className="chart"><ResponsiveContainer width="100%" height={230}><AreaChart data={analytics.activity}><defs><linearGradient id="study-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity=".28"/><stop offset="100%" stopColor="#06b6d4" stopOpacity="0"/></linearGradient></defs><CartesianGrid vertical={false} stroke="#e7edf4"/><XAxis dataKey="day" tickLine={false} axisLine={false}/><YAxis hide/><Tooltip/><Area type="monotone" dataKey="minutes" stroke="#0891b2" strokeWidth={3} fill="url(#study-fill)"/></AreaChart></ResponsiveContainer></div></section><section className="panel focus-panel"><div className="panel-title"><div><h2>Today's focus</h2><p>Move one meaningful task forward</p></div><button aria-label="Open planner"><Play size={17}/></button></div>{tasks.filter((task) => task.status !== 'done').slice(0, 3).map((task) => <div className="focus-task" key={task.id}><span className={`priority ${task.priority}`}/><div><b>{task.title}</b><small>{task.parent} · {task.estimate}</small></div><Clock3 size={16}/></div>)}</section></div>
  <div className="section-row"><div><h2>Subject mastery</h2><p>Confidence blends recall, practice, and recent review.</p></div><span className="bar-actions"><button className="chip-button" onClick={() => setSubjModal('add')}><Plus size={14}/> Add subject</button><GenerateButton label="Generate from content" busyLabel="Deriving…" onGenerate={() => api.generateSubjects(activeId)} onRefresh={onRefresh} /></span></div><div className="subject-grid">{subjects.map((subject) => <article className="subject-card" key={subject.name}><div className="subject-title"><span style={{ background: subject.color }}>{subject.name.slice(0, 1)}</span><div><h3>{subject.name}</h3><p>{subject.progress}% syllabus covered</p></div><span className="card-tools-inline"><button aria-label="Edit subject" onClick={() => setSubjModal(subject)}><Pencil size={13}/></button><button aria-label="Delete subject" onClick={() => setSubjDelete(subject)}><Trash2 size={13}/></button></span></div><div className="mastery"><div><span>Mastery</span><b>{Math.round(subject.mastery * 100)}%</b></div><div className="progress"><i style={{ width: `${subject.mastery * 100}%`, background: subject.color }}/></div></div></article>)}</div>
  {subjModal === 'add' && <Modal title="Add subject" onClose={() => setSubjModal(null)}><SubjectForm onSave={async (f) => { await api.addSubject(activeId, f); setSubjModal(null); await onRefresh() }} onClose={() => setSubjModal(null)} /></Modal>}
  {subjModal && subjModal !== 'add' && <Modal title="Edit subject" onClose={() => setSubjModal(null)}><SubjectForm subject={subjModal} onSave={async (f) => { await api.editSubject(activeId, subjModal.name, f); setSubjModal(null); await onRefresh() }} onClose={() => setSubjModal(null)} /></Modal>}
  {subjDelete && <ConfirmDialog title="Delete subject" message={`Delete "${subjDelete.name}"?`} onConfirm={async () => { await api.deleteSubject(activeId, subjDelete.name); setSubjDelete(null); await onRefresh() }} onClose={() => setSubjDelete(null)} />}
  <section className="panel review-strip"><div><span className="panel-eyebrow">Active recall</span><h2>{flashcards.length ? `${flashcards.length} cards are ready for review` : 'Your review queue is clear'}</h2><p>{flashcards.length ? 'A short retrieval session now will keep the current-electricity chain warm.' : 'Your next cards will appear here on their scheduled date.'}</p></div><button className="primary-action"><CircleDot size={17}/> Review now</button></section></>
}

function toFlowNodes(graph) {
  return graph.nodes.map((node, index) => ({
    id: node.id, type: 'learning',
    position: node.position || { x: (index % 4) * 230, y: 90 + Math.floor(index / 4) * 150 + (index % 2) * 40 },
    data: node,
  }))
}
function toFlowEdges(graph) {
  return graph.edges.map((edge, i) => ({
    id: edge.id || `e-${edge.source}-${edge.target}-${i}`,
    source: edge.source, target: edge.target, label: edge.label, type: 'smoothstep',
    markerEnd: { type: MarkerType.ArrowClosed },
  }))
}

function Roadmap({ graph, activeId, onRefresh }) {
  const [busy, setBusy] = useState('')      // '' | 'rebuild' | 'save'
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [saved, setSaved] = useState(true)
  const [nodes, setNodes, onNodesChange] = useNodesState(toFlowNodes(graph))
  const [edges, setEdges, onEdgesChange] = useEdgesState(toFlowEdges(graph))

  // Re-sync when the underlying graph changes (e.g. after a rebuild).
  useEffect(() => { setNodes(toFlowNodes(graph)); setEdges(toFlowEdges(graph)); setSaved(true) }, [graph, setNodes, setEdges])

  const onConnect = useCallback((params) => { setEdges((eds) => addEdge({ ...params, type: 'smoothstep', label: 'requires', markerEnd: { type: MarkerType.ArrowClosed } }, eds)); setSaved(false) }, [setEdges])
  const markDirty = () => setSaved(false)

  function addNode() {
    const label = window.prompt('New concept name')
    if (!label || !label.trim()) return
    const id = `${label.trim().toLowerCase().replace(/\s+/g, '-').slice(0, 40)}-${nodes.length}`
    setNodes((ns) => [...ns, { id, type: 'learning', position: { x: 60, y: 40 }, data: { id, label: label.trim(), kind: 'concept', progress: 0 } }])
    setSaved(false)
  }

  async function rebuild() {
    setBusy('rebuild'); setError('')
    try { await api.refreshGraph(activeId); await onRefresh() }
    catch (err) { setError(err.message) }
    finally { setBusy('') }
  }
  async function save() {
    setBusy('save'); setError('')
    try {
      const payload = {
        nodes: nodes.map((n) => ({ ...n.data, id: n.id, position: n.position })),
        edges: edges.map((e) => ({ source: e.source, target: e.target, label: e.label || 'requires' })),
      }
      await api.saveGraph(activeId, payload)
      setSaved(true); setEditing(false); await onRefresh()
    } catch (err) { setError(err.message) }
    finally { setBusy('') }
  }

  const empty = nodes.length === 0
  return <><div className="roadmap-toolbar"><span><Network size={17}/> Prerequisite learning path</span><div className="roadmap-tools">
    {editing && <button onClick={addNode}><Plus size={14}/> Add node</button>}
    <button className={editing ? 'on' : ''} onClick={() => setEditing((v) => !v)}>{editing ? 'Done editing' : 'Edit graph'}</button>
    {editing && <button className="rebuild-button" onClick={save} disabled={busy || saved}><Check size={14}/> {busy === 'save' ? 'Saving…' : saved ? 'Saved' : 'Save layout'}</button>}
    <button className="rebuild-button" onClick={rebuild} disabled={!!busy}><RefreshCw size={14} className={busy === 'rebuild' ? 'spinning' : ''}/> {busy === 'rebuild' ? 'Running agents…' : 'Rebuild from data'}</button>
  </div></div>
    {error && <div className="error-banner">{error}</div>}
    {editing && <p className="edit-hint">Drag nodes to reposition · drag between handles to connect · select a node/edge and press Delete to remove · then Save layout.</p>}
    {empty ? <div className="empty-state"><Network size={28}/><h2>No graph yet</h2><p>Add data in the Workspace, then run "Rebuild from data" to derive a prerequisite graph — or "Edit graph" to build one by hand.</p></div>
      : <div className="flow-shell"><ReactFlowProvider><ReactFlow
          nodes={nodes} edges={edges} nodeTypes={graphTypes}
          onNodesChange={(c) => { onNodesChange(c); if (c.some((x) => x.type === 'position' || x.type === 'remove')) markDirty() }}
          onEdgesChange={(c) => { onEdgesChange(c); if (c.some((x) => x.type === 'remove')) markDirty() }}
          onConnect={onConnect}
          nodesDraggable={editing} nodesConnectable={editing} elementsSelectable={editing} deleteKeyCode={editing ? ['Backspace', 'Delete'] : null}
          fitView fitViewOptions={{ padding: .2 }}><Background color="#dce6ed" gap={22}/><Controls showInteractive={false}/></ReactFlow></ReactFlowProvider></div>}
    <div className="graph-legend"><span><i className="legend complete"/>Strong</span><span><i className="legend active"/>In progress</span><span><i className="legend weak"/>Needs practice</span><p><Sparkles size={15}/> Edges are derived by a multi-agent pipeline; edit and save to keep a custom layout.</p></div></>
}

function NewDocumentForm({ activeId, onCreated, onClose }) {
  const [form, setForm] = useState({ title: '', subject: '', chapter: '', content: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))
  async function submit(event) {
    event.preventDefault()
    if (!form.title.trim() || busy) return
    setBusy(true); setError('')
    try {
      // A document needs a collection (workspace); create one on the fly.
      const workspace = await api.createWorkspace(activeId, form.title.trim())
      const doc = await api.createDocument({
        profile_id: activeId, workspace_id: workspace.workspace_id,
        title: form.title.trim(), subject: form.subject || null, chapter: form.chapter || null,
        content: form.content,
      })
      await onCreated(doc)
    } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Title<input autoFocus value={form.title} onChange={set('title')} placeholder="e.g. Ohm's law summary" required /></label>
    <div className="modal-row">
      <label>Subject<input value={form.subject} onChange={set('subject')} placeholder="Physics" /></label>
      <label>Chapter<input value={form.chapter} onChange={set('chapter')} placeholder="Current Electricity" /></label>
    </div>
    <label>Content (markdown)<textarea rows={6} value={form.content} onChange={set('content')} placeholder="# Notes…" /></label>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Creating…' : 'Create note'}</button></div>
  </form>
}

function IngestForm({ activeId, onDone, onClose }) {
  const [mode, setMode] = useState('pdf')
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const [meta, setMeta] = useState({ subject: '', chapter: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setError(''); setResult(null)
    try {
      const fields = { subject: meta.subject || null, chapter: meta.chapter || null }
      const res = mode === 'pdf'
        ? await api.ingestPdf(activeId, file, fields)
        : await api.ingestText(activeId, { text, ...fields })
      setResult(res)
      onDone?.()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <div className="segmented"><button type="button" className={mode === 'pdf' ? 'on' : ''} onClick={() => setMode('pdf')}>PDF upload</button><button type="button" className={mode === 'text' ? 'on' : ''} onClick={() => setMode('text')}>Paste text</button></div>
    {mode === 'pdf'
      ? <label className="file-drop"><Upload size={18} /><span>{file ? file.name : 'Choose a PDF to add to this profile'}</span><input type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files[0])} required /></label>
      : <label>Text<textarea rows={7} value={text} onChange={(event) => setText(event.target.value)} placeholder="Paste notes or curriculum text to embed…" required /></label>}
    <div className="modal-row">
      <label>Subject<input value={meta.subject} onChange={(event) => setMeta((m) => ({ ...m, subject: event.target.value }))} placeholder="Physics" /></label>
      <label>Chapter<input value={meta.chapter} onChange={(event) => setMeta((m) => ({ ...m, chapter: event.target.value }))} placeholder="Current Electricity" /></label>
    </div>
    {error && <p className="modal-error">{error}</p>}
    {result && <p className="modal-ok"><Check size={14} /> Ingested {result.ingested} chunk{result.ingested === 1 ? '' : 's'}. This content now powers Search, the Tutor, Plan generation, and the Roadmap graph — it appears under "Knowledge base", not as an editable note.</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>{result ? 'Close' : 'Cancel'}</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Embedding…' : 'Ingest'}</button></div>
  </form>
}

function KnowledgeBasePanel({ activeId, refreshKey }) {
  const [sources, setSources] = useState([])
  const [pending, setPending] = useState(null)
  const [bump, setBump] = useState(0)
  useEffect(() => { api.listSources(activeId).then(setSources).catch(() => setSources([])) }, [activeId, refreshKey, bump])
  const total = sources.reduce((sum, s) => sum + s.chunks, 0)
  async function confirmDelete() { await api.deleteSource(activeId, pending.doc_id); setPending(null); setBump((b) => b + 1) }
  return <aside className="context-panel"><span className="panel-eyebrow">Knowledge base</span><h3>{total ? `${total} chunks embedded` : 'Nothing ingested yet'}</h3>
    <p className="kb-explain">Ingested data powers <b>Search</b>, the <b>Tutor</b>, <b>Plan</b> generation, and the <b>Roadmap</b> graph. It isn’t shown as an editable note.</p>
    {sources.length === 0
      ? <p className="kb-empty">Use “Add data” to upload a PDF or paste text.</p>
      : sources.map((s) => <div className="kb-source" key={s.doc_id}><FileText size={14}/><div><b>{s.source}</b><small>{[s.subject, s.chapter].filter(Boolean).join(' · ') || 'no tags'} · {s.chunks} chunk{s.chunks === 1 ? '' : 's'}</small></div><button aria-label="Remove source" onClick={() => setPending(s)}><Trash2 size={13}/></button></div>)}
    {pending && <ConfirmDialog title="Remove from knowledge base" message={`Remove "${pending.source}" (${pending.chunks} chunks)? Search, Tutor and the graph will no longer use it.`} onConfirm={confirmDelete} onClose={() => setPending(null)} />}
  </aside>
}

function Workspace({ data, activeId, onRefresh }) {
  const [selectedId, setSelectedId] = useState(data.documents[0]?.document_id)
  const selected = data.documents.find((document) => document.document_id === selectedId) || data.documents[0]
  const [content, setContent] = useState(selected?.content || '')
  const [saved, setSaved] = useState(true)
  const [modal, setModal] = useState(null) // 'note' | 'ingest' | null
  const [pendingDelete, setPendingDelete] = useState(null)
  const [kbKey, setKbKey] = useState(0)     // bump to refresh the knowledge base after ingest
  useEffect(() => { setContent(selected?.content || ''); setSaved(true) }, [selectedId])
  async function save() { if (!selected) return; await api.saveDocument(selected.document_id, content); setSaved(true); onRefresh(); setKbKey((k) => k + 1) }
  async function afterCreate(doc) { setModal(null); await onRefresh(); setKbKey((k) => k + 1); if (doc?.document_id) setSelectedId(doc.document_id) }
  async function afterIngest() { await onRefresh(); setKbKey((k) => k + 1) }
  async function confirmDelete() {
    await api.deleteDocument(pendingDelete.document_id)
    if (pendingDelete.document_id === selectedId) setSelectedId(undefined)
    setPendingDelete(null)
    await onRefresh(); setKbKey((k) => k + 1)
  }

  const toolbar = <div className="workspace-actions">
    <button className="chip-button" onClick={() => setModal('note')}><Plus size={14} /> New note</button>
    <button className="chip-button" onClick={() => setModal('ingest')}><Upload size={14} /> Add data</button>
  </div>

  const modals = <>
    {modal === 'note' && <Modal title="New note" onClose={() => setModal(null)}><NewDocumentForm activeId={activeId} onCreated={afterCreate} onClose={() => setModal(null)} /></Modal>}
    {modal === 'ingest' && <Modal title="Add data to knowledge base" onClose={() => setModal(null)}><IngestForm activeId={activeId} onDone={afterIngest} onClose={() => setModal(null)} /></Modal>}
    {pendingDelete && <ConfirmDialog title="Delete note" message={`Delete "${pendingDelete.title}"? This removes the note and its embedded chunks from the knowledge base. This cannot be undone.`} onConfirm={confirmDelete} onClose={() => setPendingDelete(null)} />}
  </>

  if (!selected) return <><div className="empty-state"><BookOpen size={28}/><h2>No notes yet</h2><p>Create a note or ingest a PDF to start building this profile's knowledge base.</p>{toolbar}</div>{modals}</>
  return <div className="workspace-layout"><aside className="file-tree"><div className="tree-title"><span>Notes</span><button onClick={() => setModal('note')} aria-label="New note"><Plus size={15}/></button></div>{data.documents.map((document) => <div className={`tree-row ${document.document_id === selected.document_id ? 'selected' : ''}`} key={document.document_id}><button className="tree-select" onClick={() => setSelectedId(document.document_id)}><FileText size={15}/><span>{document.title}</span></button><button className="tree-delete" aria-label={`Delete ${document.title}`} onClick={() => setPendingDelete(document)}><Trash2 size={14}/></button></div>)}<button className="tree-ingest" onClick={() => setModal('ingest')}><Upload size={14}/> Add data</button></aside><section className="editor-pane"><div className="editor-top"><div><span className="crumb">{selected.subject} / {selected.chapter}</span><h2>{selected.title}</h2></div><div><span className={saved ? 'saved' : 'unsaved'}>{saved ? <><Check size={14}/> Saved</> : 'Unsaved'}</span><button className="save-button" onClick={save}>Save</button></div></div><div className="editor-split"><textarea value={content} onChange={(event) => { setContent(event.target.value); setSaved(false) }} spellCheck="true"/><article className="markdown-preview"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown></article></div></section><KnowledgeBasePanel activeId={activeId} refreshKey={kbKey} />{modals}</div>
}

const PLAN_PRESETS = [
  ['Balanced', 'A balanced plan covering all chapters evenly.'],
  ['Crash revision', 'A short crash revision focused on the most important, high-yield topics only.'],
  ['Deep mastery', 'A thorough plan that builds deep mastery: theory, worked examples, then practice for each chapter.'],
  ['Exam sprint', 'A 2-week exam sprint: prioritise weak areas, heavy practice and mock tests.'],
]

function PlanForm({ onGenerate, onClose }) {
  const [instruction, setInstruction] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault(); if (busy) return
    setBusy(true); setError('')
    try { await onGenerate(instruction.trim()) } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <div className="preset-row">{PLAN_PRESETS.map(([label, text]) => <button type="button" key={label} className={instruction === text ? 'preset on' : 'preset'} onClick={() => setInstruction(text)}>{label}</button>)}</div>
    <label>What should this plan focus on?<textarea autoFocus rows={3} value={instruction} onChange={(e) => setInstruction(e.target.value)} placeholder="e.g. 2-week crash revision on weak areas, daily 1 hour, practice-heavy" /></label>
    <p className="modal-hint">Leave blank for a balanced plan. Your instruction guides the planner agent.</p>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}><Sparkles size={15} className={busy ? 'spinning' : ''}/> {busy ? 'Planning…' : 'Generate plan'}</button></div>
  </form>
}

function Planner({ tasks, activeId, onMoveTask, onRefresh }) {
  const columns = [['planned', 'Planned'], ['in_progress', 'In progress'], ['done', 'Done']]
  const [modal, setModal] = useState(null)   // 'add' | 'plan' | {task} for edit
  const [pendingDelete, setPendingDelete] = useState(null)

  async function addTask(fields) { await api.addTask(activeId, fields); setModal(null); await onRefresh() }
  async function editTask(fields) { await api.editTask(activeId, modal.id, fields); setModal(null); await onRefresh() }
  async function confirmDelete() { await api.deleteTask(activeId, pendingDelete.id); setPendingDelete(null); await onRefresh() }
  async function genPlan(instruction) { await api.generatePlan(activeId, instruction); setModal(null); await onRefresh() }

  const modals = <>
    {modal === 'add' && <Modal title="Add task" onClose={() => setModal(null)}><TaskForm onSave={addTask} onClose={() => setModal(null)} /></Modal>}
    {modal === 'plan' && <Modal title="Generate study plan" onClose={() => setModal(null)}><PlanForm onGenerate={genPlan} onClose={() => setModal(null)} /></Modal>}
    {modal && modal !== 'add' && modal !== 'plan' && <Modal title="Edit task" onClose={() => setModal(null)}><TaskForm task={modal} onSave={editTask} onClose={() => setModal(null)} /></Modal>}
    {pendingDelete && <ConfirmDialog title="Delete task" message={`Delete "${pendingDelete.title}"?`} onConfirm={confirmDelete} onClose={() => setPendingDelete(null)} />}
  </>

  return <><div className="generate-bar"><span>{tasks.length ? `${tasks.length} tasks in this plan` : 'No plan yet'}</span><span className="bar-actions"><button className="chip-button" onClick={() => setModal('add')}><Plus size={14}/> Add task</button><button className="rebuild-button" onClick={() => setModal('plan')}><Sparkles size={14}/> Generate plan</button></span></div>
    {tasks.length === 0 ? <div className="empty-state"><Target size={28}/><h2>No plan yet</h2><p>Generate a study plan from this profile's goal and chapters, or add tasks manually.</p></div>
    : <div className="kanban">{columns.map(([status, label]) => <section key={status} className="kanban-column"><div className="column-title"><span>{label}</span><b>{tasks.filter((task) => task.status === status).length}</b></div>{tasks.filter((task) => task.status === status).map((task) => <article className="task-card" key={task.id}><span className={`priority ${task.priority}`}/><div className="card-tools"><button aria-label="Edit task" onClick={() => setModal(task)}><Pencil size={13}/></button><button aria-label="Delete task" onClick={() => setPendingDelete(task)}><Trash2 size={13}/></button></div><h3>{task.title}</h3><p>{task.parent}</p><footer><span><Clock3 size={14}/>{task.estimate}</span><select value={task.status} onChange={(event) => onMoveTask(task.id, event.target.value)} aria-label={`Move ${task.title}`}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="done">Done</option></select></footer></article>)}</section>)}</div>}
    {modals}</>
}

function TaskForm({ task, onSave, onClose }) {
  const [form, setForm] = useState({ title: task?.title || '', parent: task?.parent || '', estimate: task?.estimate || '30 min', priority: task?.priority || 'medium' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }))
  async function submit(e) {
    e.preventDefault(); if (!form.title.trim() || busy) return
    setBusy(true); setError('')
    try { await onSave(form) } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Task<input autoFocus value={form.title} onChange={set('title')} required /></label>
    <div className="modal-row"><label>Under (subject/chapter)<input value={form.parent} onChange={set('parent')} /></label><label>Estimate<input value={form.estimate} onChange={set('estimate')} /></label></div>
    <label>Priority<select value={form.priority} onChange={set('priority')}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button></div>
  </form>
}

function CardForm({ card, onSave, onClose }) {
  const [form, setForm] = useState({ front: card?.front || '', back: card?.back || '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }))
  async function submit(e) {
    e.preventDefault(); if (!form.front.trim() || !form.back.trim() || busy) return
    setBusy(true); setError('')
    try { await onSave(form) } catch (err) { setError(err.message); setBusy(false) }
  }
  return <form className="modal-form" onSubmit={submit}>
    <label>Front (question)<textarea autoFocus rows={2} value={form.front} onChange={set('front')} required /></label>
    <label>Back (answer)<textarea rows={3} value={form.back} onChange={set('back')} required /></label>
    {error && <p className="modal-error">{error}</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>Cancel</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button></div>
  </form>
}

const RATING_INTERVAL = { again: '1d', hard: '2d', good: '5d', easy: '10d' }

function Review({ cards, activeId, onReview, onRefresh }) {
  // Work from a local snapshot of the due queue so the card doesn't jump when
  // the dashboard refreshes after a rating. Rebuild only when the set of due
  // card ids actually changes (e.g. generate/add/delete).
  const [queue, setQueue] = useState(cards)
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [lastRating, setLastRating] = useState(null)   // {rating, interval} after rating
  const [modal, setModal] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)

  const cardIds = cards.map((c) => c.id).join(',')
  useEffect(() => { setQueue(cards); setIndex(0); setRevealed(false); setLastRating(null) }, [cardIds])

  const card = queue[index]

  async function rate(rating) {
    if (!card || lastRating) return
    setLastRating({ rating, interval: RATING_INTERVAL[rating] })
    // Persist + refresh analytics in the background; do NOT swap the card yet.
    try { await onReview(card.id, rating) } catch { /* surfaced by app-level error */ }
  }
  function next() {
    setLastRating(null); setRevealed(false)
    setIndex((i) => i + 1)
  }
  async function addCard(fields) { await api.addCard(activeId, fields); setModal(null); await onRefresh() }
  async function editCard(fields) { await api.editCard(activeId, modal.id, fields); setModal(null); await onRefresh() }
  async function confirmDelete() { await api.deleteCard(activeId, pendingDelete.id); setPendingDelete(null); await onRefresh() }

  const modals = <>
    {modal === 'add' && <Modal title="Add flashcard" onClose={() => setModal(null)}><CardForm onSave={addCard} onClose={() => setModal(null)} /></Modal>}
    {modal && modal !== 'add' && <Modal title="Edit flashcard" onClose={() => setModal(null)}><CardForm card={modal} onSave={editCard} onClose={() => setModal(null)} /></Modal>}
    {pendingDelete && <ConfirmDialog title="Delete flashcard" message={`Delete this card? "${pendingDelete.front.slice(0, 60)}"`} onConfirm={confirmDelete} onClose={() => setPendingDelete(null)} />}
  </>

  const addBar = <div className="generate-bar"><span>{queue.length ? `Card ${Math.min(index + 1, queue.length)} of ${queue.length}` : 'No cards due'}</span><span className="bar-actions"><button className="chip-button" onClick={() => setModal('add')}><Plus size={14}/> Add card</button><GenerateButton label="Generate flashcards" busyLabel="Writing cards…" onGenerate={() => api.generateFlashcards(activeId)} onRefresh={onRefresh} /></span></div>

  // Finished the queue (or empty).
  if (!card) return <>{addBar}<div className="empty-state"><Check size={28}/><h2>{queue.length ? 'Session complete' : 'No cards due'}</h2><p>{queue.length ? 'You reviewed every due card. New reviews appear on their scheduled dates.' : 'Generate flashcards from this profile’s notes, add one manually, or wait for scheduled reviews.'}</p></div>{modals}</>

  return <>{addBar}<div className="review-layout"><section className="flashcard"><div className="card-meta"><span>Flashcard {index + 1}/{queue.length}</span><span className="card-tools-inline"><button aria-label="Edit card" onClick={() => setModal(card)}><Pencil size={13}/></button><button aria-label="Delete card" onClick={() => setPendingDelete(card)}><Trash2 size={13}/></button></span></div>
    <div className="card-face"><p>{revealed ? card.back : card.front}</p></div>
    {lastRating
      ? <div className="rated-row"><span className="rated-badge"><Check size={15}/> Rated <b>{lastRating.rating}</b> · next in {lastRating.interval}</span><button className="reveal" onClick={next}>{index + 1 < queue.length ? 'Next card' : 'Finish'} <ChevronDown size={16} style={{ transform: 'rotate(-90deg)' }}/></button></div>
      : !revealed
        ? <button className="reveal" onClick={() => setRevealed(true)}>Show answer <ChevronDown size={17}/></button>
        : <div className="rating-row">{[['again','Again'],['hard','Hard'],['good','Good'],['easy','Easy']].map(([rating, label]) => <button key={rating} className={rating} onClick={() => rate(rating)}><small>{RATING_INTERVAL[rating]}</small>{label}</button>)}</div>}
  </section><aside className="review-info"><span className="panel-eyebrow">Memory state</span><h3>Designed for retention</h3><p>Rate how well you recalled it — that sets the next review interval. Nothing advances until you choose <b>Next card</b>.</p><dl><div><dt>Stability</dt><dd>{card.stability} days</dd></div><div><dt>Difficulty</dt><dd>{card.difficulty}/10</dd></div><div><dt>Reviews</dt><dd>{card.reps}</dd></div></dl></aside></div>{modals}</>
}

function Tutor({ activeId }) {
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState('answer')   // 'answer' | 'document'
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Ask a question for a grounded answer, or switch to **Generate document** to produce a downloadable .docx via the multi-agent pipeline.' }])
  const [busy, setBusy] = useState(false)
  const [files, setFiles] = useState([])

  useEffect(() => { api.listFiles().then((r) => setFiles(r.files || [])).catch(() => setFiles([])) }, [])

  async function send(event) {
    event.preventDefault()
    if (!question.trim() || busy) return
    const prompt = question.trim()
    setMessages((items) => [...items, { role: 'user', content: prompt }])
    setQuestion(''); setBusy(true)
    try {
      if (mode === 'document') {
        const res = await api.generateDocument(prompt, { profile_id: activeId, source: 'tutor' })
        if (res.success && res.document_filename) {
          setMessages((items) => [...items, { role: 'assistant', content: 'Your document is ready.', file: res.document_filename }])
          const r = await api.listFiles(); setFiles(r.files || [])
        } else {
          setMessages((items) => [...items, { role: 'assistant', content: `Generation failed: ${res.error || 'unknown error'}` }])
        }
      } else {
        const answer = await api.tutor(activeId, prompt)
        setMessages((items) => [...items, { role: 'assistant', content: answer.answer, sources: answer.sources, provider: answer.provider }])
      }
    } catch (err) {
      setMessages((items) => [...items, { role: 'assistant', content: `Something went wrong: ${err.message}` }])
    } finally { setBusy(false) }
  }

  return <div className="tutor-layout"><section className="tutor-chat">
    <div className="segmented tutor-mode"><button type="button" className={mode === 'answer' ? 'on' : ''} onClick={() => setMode('answer')}><Bot size={13}/> Answer</button><button type="button" className={mode === 'document' ? 'on' : ''} onClick={() => setMode('document')}><FileText size={13}/> Generate document</button></div>
    {messages.map((message, index) => <article className={`chat-message ${message.role}`} key={index}><span>{message.role === 'assistant' ? <Bot size={17}/> : 'A'}</span><div><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>{message.file && <a className="doc-download" href={fileDownloadUrl(message.file)} target="_blank" rel="noreferrer"><FileText size={14}/> Download {message.file}</a>}{message.sources?.length > 0 && <div className="sources">{message.sources.map((source) => <small key={source.document_id}><BookOpen size={12}/>{source.title}</small>)}</div>}</div></article>)}
    {busy && <article className="chat-message assistant"><span><Bot size={17}/></span><div className="typing">{mode === 'document' ? <span className="doc-progress">Planning → writing → reviewing…</span> : <><i/><i/><i/></>}</div></article>}
    <form onSubmit={send}><textarea data-tutor-input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={mode === 'document' ? 'Describe the document to generate (e.g. "2-page revision note on Current Electricity")' : 'Ask about your current notes...'}/><button type="submit" disabled={busy} aria-label={mode === 'document' ? 'Generate document' : 'Send question'}>{mode === 'document' ? <FileText size={18}/> : <Send size={18}/>}</button></form>
  </section><aside className="tutor-sidebar"><span className="panel-eyebrow">{mode === 'document' ? 'Multi-agent pipeline' : 'Grounded context'}</span><h3>{mode === 'document' ? 'Plan → Write → Review' : 'Active profile only'}</h3><p>{mode === 'document' ? 'Documents are produced by the LangGraph agents and saved as .docx using the active model.' : 'Your other profiles are excluded from this conversation and retrieval context.'}</p>
    {files.length > 0 && <div className="files-list"><span className="panel-eyebrow">Recent documents</span>{files.slice(0, 6).map((f) => <a key={f.filename} className="file-item" href={fileDownloadUrl(f.filename)} target="_blank" rel="noreferrer"><FileText size={13}/><span>{f.filename}</span><small>{f.size_mb}MB</small></a>)}</div>}
  </aside></div>
}

export default App
