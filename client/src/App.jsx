import { useCallback, useEffect, useMemo, useState } from 'react'
import { Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider } from '@xyflow/react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  BarChart3, BookOpen, Bot, Check, ChevronDown, CircleDot, Clock3, Command,
  FileText, GraduationCap, LayoutDashboard, Network, PanelLeft, Play, Plus, Search,
  Send, Sparkles, Target, Upload, X, Zap,
} from 'lucide-react'
import { api } from './api'

function Modal({ title, onClose, children }) {
  return <div className="modal-backdrop" onClick={onClose}>
    <div className="modal" onClick={(event) => event.stopPropagation()}>
      <div className="modal-head"><h2>{title}</h2><button className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      {children}
    </div>
  </div>
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

function Metric({ label, value, suffix, accent = 'cyan' }) {
  return <article className="metric"><span className={`metric-icon ${accent}`}><Zap size={16} /></span><div><small>{label}</small><strong>{value}<em>{suffix}</em></strong></div></article>
}

function App() {
  const [profiles, setProfiles] = useState([])
  const [activeId, setActiveId] = useState('')
  const [data, setData] = useState(null)
  const [view, setView] = useState('overview')
  const [openProfiles, setOpenProfiles] = useState(false)
  const [showNewProfile, setShowNewProfile] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [infra, setInfra] = useState({ ollama: {}, milvus: {} })
  const [error, setError] = useState('')

  async function createProfile(payload) {
    const created = await api.createProfile(payload)
    const items = await api.listProfiles()
    setProfiles(items)
    setActiveId(created.profile_id)
    setShowNewProfile(false)
    setOpenProfiles(false)
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
      {openProfiles && <div className="profile-menu">{profiles.map((profile) => <button key={profile.profile_id} onClick={() => { setActiveId(profile.profile_id); setOpenProfiles(false) }}><span>{profile.name.slice(0, 1)}</span>{profile.name}</button>)}<button className="profile-menu-add" onClick={() => { setShowNewProfile(true); setOpenProfiles(false) }}><span><Plus size={14} /></span>New profile</button></div>}
      <nav>{navItems.map(([id, label, Icon]) => <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}><Icon size={18} />{label}{id === 'review' && dueCount > 0 && <b className="count">{dueCount}</b>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="goal-box"><Target size={18}/><p>Target date</p><strong>{activeProfile?.target_date || 'Set a goal'}</strong><span>{activeProfile?.daily_study_hours || 0}h/day focus</span></div><StatusPill online={infra.ollama?.available} label={infra.ollama?.available ? 'AI ready' : 'AI offline'} /></div>
    </aside>
    <main className="main">
      <header className="topbar"><button className="mobile-menu"><PanelLeft size={20}/></button><form className="global-search" onSubmit={performSearch}><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this profile"/><kbd><Command size={11}/> K</kbd></form><div className="topbar-right"><StatusPill online={infra.milvus?.available} label={infra.milvus?.available ? 'Vector index' : 'Local search'} /><span className="avatar">A</span></div></header>
      {error && <div className="error-banner">{error}</div>}
      {results.length > 0 && <section className="search-results"><b>Results in {activeProfile?.name}</b>{results.map((result) => <button key={result.document_id} onClick={() => { setView('workspace'); setResults([]) }}><FileText size={16}/><span>{result.title}<small>{result.subject} / {result.chapter}</small></span><em>{Math.round(result.score * 100)}%</em></button>)}</section>}
      {!data ? <div className="loading"><span className="loader"/>Opening your learning space...</div> : <PageContent view={view} data={data} activeId={activeId} onMoveTask={moveTask} onReview={review} onRefresh={refresh} />}
    </main>
    {showNewProfile && <Modal title="Create a learning profile" onClose={() => setShowNewProfile(false)}><NewProfileForm onCreate={createProfile} onClose={() => setShowNewProfile(false)} /></Modal>}
  </div>
}

function PageContent({ view, data, activeId, onMoveTask, onReview, onRefresh }) {
  const heading = { overview: ['Good evening, Abdullah', 'Your focus is clear. Keep the next move small and specific.'], roadmap: ['Learning roadmap', 'See prerequisite paths and your current confidence.'], workspace: ['Workspace', 'Write, connect, and retrieve notes without leaving your profile.'], planner: ['Study planner', 'Move work through the day as your plan evolves.'], review: ['Review queue', 'Retrieval practice scheduled for today.'], tutor: ['Study tutor', 'Ask against the notes and concepts in this profile.'] }[view]
  return <section className="page"><div className="page-heading"><div><h1>{heading[0]}</h1><p>{heading[1]}</p></div>{view === 'overview' && <button className="primary-action" onClick={() => document.querySelector('[data-tutor-input]')?.focus()}><Sparkles size={17}/> Ask Atlas</button>}</div>
    {view === 'overview' && <Overview data={data} />}
    {view === 'roadmap' && <Roadmap graph={data.graph} />}
    {view === 'workspace' && <Workspace data={data} activeId={activeId} onRefresh={onRefresh} />}
    {view === 'planner' && <Planner tasks={data.tasks} onMoveTask={onMoveTask} />}
    {view === 'review' && <Review cards={data.flashcards} onReview={onReview} />}
    {view === 'tutor' && <Tutor activeId={activeId} />}
  </section>
}

function Overview({ data }) {
  const { analytics, subjects, tasks, flashcards } = data
  return <><div className="metrics-grid"><Metric label="Study time" value={`${Math.floor(analytics.study_minutes_this_week / 60)}h ${analytics.study_minutes_this_week % 60}m`} suffix="this week"/><Metric label="Current streak" value={analytics.streak} suffix="days" accent="orange"/><Metric label="Plan progress" value={`${analytics.tasks_completed}/${analytics.task_total}`} suffix="tasks" accent="violet"/><Metric label="Reviews due" value={analytics.review_due} suffix="cards" accent="green"/></div>
  <div className="overview-grid"><section className="panel activity-panel"><div className="panel-title"><div><h2>Learning rhythm</h2><p>Focused study minutes this week</p></div><span className="trend">+18% <small>vs last week</small></span></div><div className="chart"><ResponsiveContainer width="100%" height={230}><AreaChart data={analytics.activity}><defs><linearGradient id="study-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#06b6d4" stopOpacity=".28"/><stop offset="100%" stopColor="#06b6d4" stopOpacity="0"/></linearGradient></defs><CartesianGrid vertical={false} stroke="#e7edf4"/><XAxis dataKey="day" tickLine={false} axisLine={false}/><YAxis hide/><Tooltip/><Area type="monotone" dataKey="minutes" stroke="#0891b2" strokeWidth={3} fill="url(#study-fill)"/></AreaChart></ResponsiveContainer></div></section><section className="panel focus-panel"><div className="panel-title"><div><h2>Today's focus</h2><p>Move one meaningful task forward</p></div><button aria-label="Open planner"><Play size={17}/></button></div>{tasks.filter((task) => task.status !== 'done').slice(0, 3).map((task) => <div className="focus-task" key={task.id}><span className={`priority ${task.priority}`}/><div><b>{task.title}</b><small>{task.parent} · {task.estimate}</small></div><Clock3 size={16}/></div>)}</section></div>
  <div className="section-row"><div><h2>Subject mastery</h2><p>Confidence blends recall, practice, and recent review.</p></div><button className="text-button">View analytics <BarChart3 size={15}/></button></div><div className="subject-grid">{subjects.map((subject) => <article className="subject-card" key={subject.name}><div className="subject-title"><span style={{ background: subject.color }}>{subject.name.slice(0, 1)}</span><div><h3>{subject.name}</h3><p>{subject.progress}% syllabus covered</p></div></div><div className="mastery"><div><span>Mastery</span><b>{Math.round(subject.mastery * 100)}%</b></div><div className="progress"><i style={{ width: `${subject.mastery * 100}%`, background: subject.color }}/></div></div></article>)}</div>
  <section className="panel review-strip"><div><span className="panel-eyebrow">Active recall</span><h2>{flashcards.length ? `${flashcards.length} cards are ready for review` : 'Your review queue is clear'}</h2><p>{flashcards.length ? 'A short retrieval session now will keep the current-electricity chain warm.' : 'Your next cards will appear here on their scheduled date.'}</p></div><button className="primary-action"><CircleDot size={17}/> Review now</button></section></>
}

function Roadmap({ graph }) {
  const nodes = useMemo(() => graph.nodes.map((node, index) => ({ id: node.id, type: 'learning', position: { x: index * 210, y: 120 + (index % 2) * 130 }, data: node })), [graph])
  const edges = useMemo(() => graph.edges.map((edge) => ({ ...edge, animated: edge.target === 'kirchhoff', label: edge.label, type: 'smoothstep' })), [graph])
  return <><div className="roadmap-toolbar"><span><Network size={17}/> Physics learning path</span><div><button>Auto layout</button><button>Filter weak areas</button></div></div><div className="flow-shell"><ReactFlowProvider><ReactFlow nodes={nodes} edges={edges} nodeTypes={graphTypes} fitView fitViewOptions={{ padding: .2 }}><Background color="#dce6ed" gap={22}/><Controls showInteractive={false}/></ReactFlow></ReactFlowProvider></div><div className="graph-legend"><span><i className="legend complete"/>Strong</span><span><i className="legend active"/>In progress</span><span><i className="legend weak"/>Needs practice</span><p><Sparkles size={15}/> Recommendation: practice Kirchhoff's laws after a short capacitance recall.</p></div></>
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
    {result && <p className="modal-ok"><Check size={14} /> Ingested {result.ingested} chunk{result.ingested === 1 ? '' : 's'} into this profile's knowledge base.</p>}
    <div className="modal-actions"><button type="button" className="ghost" onClick={onClose}>{result ? 'Close' : 'Cancel'}</button><button type="submit" className="primary-action" disabled={busy}>{busy ? 'Embedding…' : 'Ingest'}</button></div>
  </form>
}

function Workspace({ data, activeId, onRefresh }) {
  const [selectedId, setSelectedId] = useState(data.documents[0]?.document_id)
  const selected = data.documents.find((document) => document.document_id === selectedId) || data.documents[0]
  const [content, setContent] = useState(selected?.content || '')
  const [saved, setSaved] = useState(true)
  const [modal, setModal] = useState(null) // 'note' | 'ingest' | null
  useEffect(() => { setContent(selected?.content || ''); setSaved(true) }, [selectedId])
  async function save() { if (!selected) return; await api.saveDocument(selected.document_id, content); setSaved(true); onRefresh() }
  async function afterCreate(doc) { setModal(null); await onRefresh(); if (doc?.document_id) setSelectedId(doc.document_id) }

  const toolbar = <div className="workspace-actions">
    <button className="chip-button" onClick={() => setModal('note')}><Plus size={14} /> New note</button>
    <button className="chip-button" onClick={() => setModal('ingest')}><Upload size={14} /> Add data</button>
  </div>

  const modals = <>
    {modal === 'note' && <Modal title="New note (collection)" onClose={() => setModal(null)}><NewDocumentForm activeId={activeId} onCreated={afterCreate} onClose={() => setModal(null)} /></Modal>}
    {modal === 'ingest' && <Modal title="Add data to knowledge base" onClose={() => setModal(null)}><IngestForm activeId={activeId} onDone={onRefresh} onClose={() => setModal(null)} /></Modal>}
  </>

  if (!selected) return <><div className="empty-state"><BookOpen size={28}/><h2>No notes yet</h2><p>Create a note or ingest a PDF to start building this profile's knowledge base.</p>{toolbar}</div>{modals}</>
  return <div className="workspace-layout"><aside className="file-tree"><div className="tree-title"><span>Notes</span><button onClick={() => setModal('note')} aria-label="New note"><Plus size={15}/></button></div>{data.documents.map((document) => <button className={document.document_id === selected.document_id ? 'selected' : ''} key={document.document_id} onClick={() => setSelectedId(document.document_id)}><FileText size={15}/><span>{document.title}</span></button>)}<button className="tree-ingest" onClick={() => setModal('ingest')}><Upload size={14}/> Add data</button></aside><section className="editor-pane"><div className="editor-top"><div><span className="crumb">{selected.subject} / {selected.chapter}</span><h2>{selected.title}</h2></div><div><span className={saved ? 'saved' : 'unsaved'}>{saved ? <><Check size={14}/> Saved</> : 'Unsaved'}</span><button className="save-button" onClick={save}>Save</button></div></div><div className="editor-split"><textarea value={content} onChange={(event) => { setContent(event.target.value); setSaved(false) }} spellCheck="true"/><article className="markdown-preview"><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>{content}</ReactMarkdown></article></div></section><aside className="context-panel"><span className="panel-eyebrow">Context</span><h3>Connected concepts</h3><button><span>Current Electricity</span><ChevronDown size={14}/></button><button><span>Ohm's Law</span><ChevronDown size={14}/></button><button><span>Kirchhoff's Laws</span><ChevronDown size={14}/></button><div className="memory-callout"><Sparkles size={16}/><p>You learn this topic best after seeing one worked numerical example.</p></div></aside>{modals}</div>
}

function Planner({ tasks, onMoveTask }) {
  const columns = [['planned', 'Planned'], ['in_progress', 'In progress'], ['done', 'Done']]
  return <div className="kanban">{columns.map(([status, label]) => <section key={status} className="kanban-column"><div className="column-title"><span>{label}</span><b>{tasks.filter((task) => task.status === status).length}</b></div>{tasks.filter((task) => task.status === status).map((task) => <article className="task-card" key={task.id}><span className={`priority ${task.priority}`}/><h3>{task.title}</h3><p>{task.parent}</p><footer><span><Clock3 size={14}/>{task.estimate}</span><select value={task.status} onChange={(event) => onMoveTask(task.id, event.target.value)} aria-label={`Move ${task.title}`}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="done">Done</option></select></footer></article>)}</section>)}</div>
}

function Review({ cards, onReview }) {
  const [revealed, setRevealed] = useState(false)
  const card = cards[0]
  useEffect(() => setRevealed(false), [card?.id])
  if (!card) return <div className="empty-state"><CircleDot size={28}/><h2>All caught up</h2><p>Your next review will appear when its schedule is due.</p></div>
  return <div className="review-layout"><section className="flashcard"><div className="card-meta"><span>Current Electricity</span><span>{cards.length} due</span></div><div className="card-face"><p>{revealed ? card.back : card.front}</p></div>{!revealed ? <button className="reveal" onClick={() => setRevealed(true)}>Show answer <ChevronDown size={17}/></button> : <div className="rating-row">{[['again','Again'],['hard','Hard'],['good','Good'],['easy','Easy']].map(([rating, label]) => <button key={rating} className={rating} onClick={() => onReview(card.id, rating)}><small>{rating === 'again' ? '1d' : rating === 'hard' ? '2d' : rating === 'good' ? '5d' : '10d'}</small>{label}</button>)}</div>}</section><aside className="review-info"><span className="panel-eyebrow">Memory state</span><h3>Designed for retention</h3><p>Each rating updates the next review interval and records the stability of this concept.</p><dl><div><dt>Stability</dt><dd>{card.stability} days</dd></div><div><dt>Difficulty</dt><dd>{card.difficulty}/10</dd></div><div><dt>Reviews</dt><dd>{card.reps}</dd></div></dl></aside></div>
}

function Tutor({ activeId }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([{ role: 'assistant', content: 'Ask about a concept, a note, or what to study next. I will only use the active profile.' }])
  const [busy, setBusy] = useState(false)
  async function send(event) { event.preventDefault(); if (!question.trim() || busy) return; const prompt = question.trim(); setMessages((items) => [...items, { role: 'user', content: prompt }]); setQuestion(''); setBusy(true); try { const answer = await api.tutor(activeId, prompt); setMessages((items) => [...items, { role: 'assistant', content: answer.answer, sources: answer.sources, provider: answer.provider }]) } finally { setBusy(false) } }
  return <div className="tutor-layout"><section className="tutor-chat">{messages.map((message, index) => <article className={`chat-message ${message.role}`} key={index}><span>{message.role === 'assistant' ? <Bot size={17}/> : 'A'}</span><div><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>{message.sources?.length > 0 && <div className="sources">{message.sources.map((source) => <small key={source.document_id}><BookOpen size={12}/>{source.title}</small>)}</div>}</div></article>)}{busy && <article className="chat-message assistant"><span><Bot size={17}/></span><div className="typing"><i/><i/><i/></div></article>}<form onSubmit={send}><textarea data-tutor-input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about your current notes..."/><button type="submit" disabled={busy} aria-label="Send question"><Send size={18}/></button></form></section><aside className="tutor-sidebar"><span className="panel-eyebrow">Grounded context</span><h3>Active profile only</h3><p>Your other profiles are excluded from this conversation and retrieval context.</p><div><BookOpen size={17}/><span>Documents and notes</span></div><div><Network size={17}/><span>Concept graph</span></div><div><CircleDot size={17}/><span>Review history</span></div></aside></div>
}

export default App
