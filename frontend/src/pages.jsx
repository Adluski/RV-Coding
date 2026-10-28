import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import { Check, Diff, Verdict, ago, fmtMem, fmtMs, storage } from './ui.jsx'

function useLoad(path) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setData(null)
    setError('')
    api(path).then(setData).catch((e) => setError(e.message))
  }, [path])
  return [data, error, setData]
}

export function AuthPage({ mode, onAuth }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const login = mode === 'login'

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const u = await api('/auth/' + mode, { method: 'POST', body: { username, password } })
      onAuth(u)
      nav('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth">
      <form onSubmit={submit} className="panel auth-card">
        <div className="eyebrow">rv/coding</div>
        <h1>{login ? 'Welcome back' : 'Create an account'}</h1>
        <p className="muted">{login ? 'Sign in to keep solving.' : 'Solve problems in Python or C++ and climb the leaderboard.'}</p>
        <label className="field">
          <span>Username</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus required />
        </label>
        <label className="field">
          <span>Password</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={login ? 'current-password' : 'new-password'} minLength={8} required />
        </label>
        {!login && <p className="hint-text">Letters, digits and _ for the username. Password: 8 or more characters.</p>}
        {error && <p className="err">{error}</p>}
        <button className="btn primary block" type="submit" disabled={busy}>{busy ? 'Please wait…' : login ? 'Log in' : 'Create account'}</button>
        <p className="muted small switch">
          {login ? <>New here? <Link to="/register">Create an account</Link></> : <>Already registered? <Link to="/login">Log in</Link></>}
        </p>
      </form>
    </div>
  )
}

const LEVELS = ['Easy', 'Medium', 'Hard']

export function ProblemList() {
  const [problems, error] = useLoad('/problems')
  const [level, setLevel] = useState(() => storage.get('filter:level') || 'All')
  const [status, setStatus] = useState('all')
  const [q, setQ] = useState('')

  useEffect(() => storage.set('filter:level', level), [level])

  const shown = useMemo(() => (problems || []).filter((p) =>
    (level === 'All' || p.difficulty === level) &&
    (status === 'all' || (status === 'solved') === p.solved) &&
    p.title.toLowerCase().includes(q.trim().toLowerCase())), [problems, level, status, q])

  if (error) return <p className="err">{error}</p>
  if (!problems) return <p className="muted">Loading problems…</p>

  const solvedTotal = problems.filter((p) => p.solved).length
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Problems</h1>
          <p className="muted">{solvedTotal} of {problems.length} solved</p>
        </div>
        <div className="stats">
          {LEVELS.map((l) => {
            const all = problems.filter((p) => p.difficulty === l)
            const done = all.filter((p) => p.solved).length
            return (
              <div className="stat" key={l}>
                <div className="stat-top"><Diff d={l} /><span className="mono">{done}/{all.length}</span></div>
                <div className="bar"><div className={'fill f-' + l} style={{ width: all.length ? (100 * done) / all.length + '%' : 0 }} /></div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="toolbar">
        <div className="seg" role="tablist">
          {['All', ...LEVELS].map((l) => (
            <button key={l} role="tab" aria-selected={level === l} className={level === l ? 'on' : ''} onClick={() => setLevel(l)}>{l}</button>
          ))}
        </div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status filter">
          <option value="all">Any status</option>
          <option value="solved">Solved</option>
          <option value="unsolved">Unsolved</option>
        </select>
        <input className="search" placeholder="Search problems" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      <div className="panel flush">
        <table className="list">
          <thead><tr><th className="w-status" /><th>Title</th><th className="w-diff">Difficulty</th></tr></thead>
          <tbody>
            {shown.map((p) => (
              <tr key={p.id}>
                <td className="w-status">{p.solved && <Check />}</td>
                <td><Link to={`/problems/${p.id}`} className="row-link"><span className="mono dim">{p.id}.</span> {p.title}</Link></td>
                <td className="w-diff"><Diff d={p.difficulty} /></td>
              </tr>
            ))}
            {shown.length === 0 && <tr><td colSpan={3} className="muted center-pad">No problems match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  )
}

export function Submissions() {
  const [rows, error, setRows] = useLoad('/submissions')

  // Keep pending rows fresh: poll each one every 2 s until it is judged.
  const pendingIds = (rows || []).filter((r) => r.status !== 'done').map((r) => r.id).join(',')
  useEffect(() => {
    if (!pendingIds) return
    const t = setTimeout(async () => {
      const updates = await Promise.all(pendingIds.split(',').map((id) => api(`/submissions/${id}`).catch(() => null)))
      setRows((cur) => cur.map((r) => {
        const u = updates.find((x) => x && x.id === r.id)
        return u ? { ...r, ...u } : r
      }))
    }, 2000)
    return () => clearTimeout(t)
  }, [pendingIds, rows, setRows])

  if (error) return <p className="err">{error}</p>
  if (!rows) return <p className="muted">Loading submissions…</p>
  return (
    <>
      <div className="page-head"><div><h1>Submissions</h1><p className="muted">Your last {rows.length} submissions, newest first.</p></div></div>
      {rows.length === 0 ? (
        <div className="panel empty">No submissions yet. <Link to="/">Pick a problem</Link> to get started.</div>
      ) : (
        <div className="panel flush scroll-x">
          <table className="list">
            <thead><tr><th>Problem</th><th>Verdict</th><th>Tests</th><th>Runtime</th><th>Memory</th><th>Lang</th><th>Your complexity</th><th>When</th></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td><Link to={`/problems/${s.problem_id}`} className="row-link">{s.problem_title}</Link></td>
                  <td><Verdict v={s.status === 'done' ? s.verdict : null} long /></td>
                  <td className="mono">{s.tests_total != null && s.tests_passed != null ? `${s.tests_passed}/${s.tests_total}` : '–'}</td>
                  <td className="mono">{fmtMs(s.runtime_ms)}</td>
                  <td className="mono">{fmtMem(s.memory_kb)}</td>
                  <td className="mono">{s.language === 'cpp' ? 'C++17' : 'Python 3'}</td>
                  <td className="mono small">{s.claimed_time || s.claimed_space ? `${s.claimed_time || '–'} · ${s.claimed_space || '–'}` : <span className="dim">–</span>}</td>
                  <td className="muted small" title={new Date(s.created_at).toLocaleString()}>{ago(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export function Leaderboard({ user }) {
  const [rows, error] = useLoad('/leaderboard')
  if (error) return <p className="err">{error}</p>
  if (!rows) return <p className="muted">Loading leaderboard…</p>
  return (
    <>
      <div className="page-head"><div><h1>Leaderboard</h1><p className="muted">Ranked by problems solved, then fewest wrong attempts before solving, then who finished first.</p></div></div>
      <div className="panel flush">
        <table className="list">
          <thead><tr><th className="w-rank">Rank</th><th>User</th><th className="num">Solved</th><th className="num">Wrong attempts</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.username} className={user && r.username === user.username ? 'me' : ''}>
                <td className="w-rank"><span className={'rank r' + r.rank}>{r.rank}</span></td>
                <td>{r.username}{user && r.username === user.username && <span className="you">you</span>}</td>
                <td className="num mono">{r.solved}</td>
                <td className="num mono">{r.wrong}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={4} className="muted center-pad">No participants yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  )
}
