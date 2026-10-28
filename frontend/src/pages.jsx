import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from './api.js'

function useLoad(path) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setData(null)
    api(path).then(setData).catch((e) => setError(e.message))
  }, [path])
  return [data, error]
}

export function AuthPage({ mode, onAuth }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const nav = useNavigate()

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const u = await api('/auth/' + mode, { method: 'POST', body: { username, password } })
      onAuth(u)
      nav('/')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form onSubmit={submit} className="card narrow">
      <h2>{mode === 'login' ? 'Log in' : 'Register'}</h2>
      <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
      <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={8} required /></label>
      {mode === 'register' && <small>Password: at least 8 characters.</small>}
      {error && <p className="err">{error}</p>}
      <button type="submit">{mode === 'login' ? 'Log in' : 'Create account'}</button>
    </form>
  )
}

export function ProblemList() {
  const [problems, error] = useLoad('/problems')
  if (error) return <p className="err">{error}</p>
  if (!problems) return <p>Loading…</p>
  return (
    <>
      <h2>Problems</h2>
      {problems.length === 0 && <p>No problems published yet.</p>}
      {['Easy', 'Medium', 'Hard'].map((level) => {
        const group = problems.filter((p) => p.difficulty === level)
        if (group.length === 0) return null
        return (
          <section key={level}>
            <h3 className={'d-' + level}>{level} <span className="muted">({group.filter((p) => p.solved).length}/{group.length} solved)</span></h3>
            <table>
              <thead><tr><th>#</th><th>Title</th><th>Solved</th></tr></thead>
              <tbody>
                {group.map((p) => (
                  <tr key={p.id}>
                    <td>{p.id}</td>
                    <td><Link to={`/problems/${p.id}`}>{p.title}</Link></td>
                    <td>{p.solved ? '✓' : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )
      })}
    </>
  )
}

const VERDICT_TEXT = {
  AC: 'Accepted', WA: 'Wrong answer', TLE: 'Time limit exceeded', RE: 'Runtime error',
  CE: 'Compilation error', ERR: 'Judge error',
}

export function VerdictBox({ sub }) {
  if (!sub) return null
  if (sub.status !== 'done') {
    return <div className="card">Pending… judging submission #{sub.id}{sub.message ? ` (${sub.message})` : ''}</div>
  }
  return (
    <div className={'card verdict v-' + sub.verdict}>
      <b>{sub.verdict}</b> — {VERDICT_TEXT[sub.verdict]}
      {sub.failed_test != null && <div>Failed test: #{sub.failed_test}</div>}
      {sub.runtime_ms != null && <div>Runtime: {sub.runtime_ms} ms</div>}
      {sub.memory_kb != null && <div>Memory: {sub.memory_kb} KB</div>}
      {sub.message && <pre>{sub.message}</pre>}
      {(sub.claimed_time || sub.claimed_space) && (
        <div className="muted">Your stated complexity (self-reported, not measured): time {sub.claimed_time || '–'}, space {sub.claimed_space || '–'}</div>
      )}
    </div>
  )
}

export function ProblemPage() {
  const { id } = useParams()
  const [p, error] = useLoad(`/problems/${id}`)
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')
  const [sub, setSub] = useState(null)
  const [submitError, setSubmitError] = useState('')
  const [claimedTime, setClaimedTime] = useState('')
  const [claimedSpace, setClaimedSpace] = useState('')
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  async function poll(sid) {
    try {
      const s = await api(`/submissions/${sid}`)
      setSub(s)
      if (s.status !== 'done') timer.current = setTimeout(() => poll(sid), 2000)
    } catch (e) {
      setSubmitError(e.message)
    }
  }

  async function submit() {
    setSubmitError('')
    clearTimeout(timer.current)
    try {
      const { id: sid } = await api('/submissions', { method: 'POST', body: { problem_id: Number(id), language, source_code: code, claimed_time: claimedTime, claimed_space: claimedSpace } })
      setSub({ id: sid, status: 'pending' })
      poll(sid)
    } catch (e) {
      setSubmitError(e.message)
    }
  }

  if (error) return <p className="err">{error}</p>
  if (!p) return <p>Loading…</p>
  const busy = sub && sub.status !== 'done'
  return (
    <>
      <h2>{p.title} <span className={'badge d-' + p.difficulty}>{p.difficulty}</span></h2>
      <p className="muted">Time limit {p.time_limit_sec}s · Memory limit {p.memory_limit_mb} MB</p>
      <pre className="statement">{p.statement}</pre>
      {p.hint && (
        <details className="card">
          <summary><b>Hint</b> (click to reveal)</summary>
          <p>{p.hint}</p>
        </details>
      )}
      {(p.time_complexity || p.space_complexity) && (
        <details className="card">
          <summary><b>Target complexity</b> (click to reveal; spoils the intended approach)</summary>
          <p>Time: {p.time_complexity || '–'} · Space: {p.space_complexity || '–'}</p>
          <p className="muted">This is the complexity of the intended solution. It is not measured from your code; the tests only catch solutions that are far too slow.</p>
        </details>
      )}
      <h3>Samples</h3>
      {p.samples.length === 0 && <p>No samples.</p>}
      {p.samples.map((s) => (
        <div className="sample" key={s.position}>
          <div><b>Input</b><pre>{s.input}</pre></div>
          <div><b>Output</b><pre>{s.expected_output}</pre></div>
        </div>
      ))}
      <h3>Submit</h3>
      <p className="muted">Your code and the problem tests are sent to the hosted Judge0 service for execution.</p>
      <label>Language
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="python">Python 3</option>
          <option value="cpp">C++17</option>
        </select>
      </label>
      <div className="sample">
        <label>Your time complexity (optional, e.g. O(n log n))<input value={claimedTime} maxLength={64} onChange={(e) => setClaimedTime(e.target.value)} /></label>
        <label>Your space complexity (optional, e.g. O(n))<input value={claimedSpace} maxLength={64} onChange={(e) => setClaimedSpace(e.target.value)} /></label>
      </div>
      <textarea className="code" rows={16} value={code} onChange={(e) => setCode(e.target.value)} spellCheck={false} placeholder="Paste your solution here" />
      <button onClick={submit} disabled={busy || !code.trim()}>{busy ? 'Judging…' : 'Submit'}</button>
      {submitError && <p className="err">{submitError}</p>}
      <VerdictBox sub={sub} />
    </>
  )
}

export function Submissions() {
  const [rows, error] = useLoad('/submissions')
  if (error) return <p className="err">{error}</p>
  if (!rows) return <p>Loading…</p>
  return (
    <>
      <h2>My submissions</h2>
      {rows.length === 0 && <p>No submissions yet.</p>}
      <table>
        <thead><tr><th>ID</th><th>Problem</th><th>Lang</th><th>Stated time / space</th><th>Verdict</th><th>Failed test</th><th>Time</th><th>Memory</th><th>When</th></tr></thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td><Link to={`/problems/${s.problem_id}`}>{s.problem_title}</Link></td>
              <td>{s.language}</td>
              <td>{s.claimed_time || s.claimed_space ? `${s.claimed_time || '–'} / ${s.claimed_space || '–'}` : ''}</td>
              <td className={'v-' + s.verdict}>{s.status === 'done' ? s.verdict : 'pending'}</td>
              <td>{s.failed_test ?? ''}</td>
              <td>{s.runtime_ms != null ? s.runtime_ms + ' ms' : ''}</td>
              <td>{s.memory_kb != null ? s.memory_kb + ' KB' : ''}</td>
              <td>{new Date(s.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

export function Leaderboard() {
  const [rows, error] = useLoad('/leaderboard')
  if (error) return <p className="err">{error}</p>
  if (!rows) return <p>Loading…</p>
  return (
    <>
      <h2>Leaderboard</h2>
      <table>
        <thead><tr><th>Rank</th><th>User</th><th>Solved</th><th>Wrong attempts</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.username}><td>{r.rank}</td><td>{r.username}</td><td>{r.solved}</td><td>{r.wrong}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
