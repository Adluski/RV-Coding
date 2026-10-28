import { useEffect, useState } from 'react'
import { api } from './api.js'
import { Diff } from './ui.jsx'

const EXAMPLE_TESTS = JSON.stringify(
  [
    { input: '1 2\n', expected_output: '3\n', is_sample: true },
    { input: '10 20\n', expected_output: '30\n', is_sample: false },
  ],
  null,
  2,
)

const EMPTY = { id: null, title: '', statement: '', time_limit_sec: 2, memory_limit_mb: 256, published: false, difficulty: 'Easy', hint: '', time_complexity: '', space_complexity: '', tests: EXAMPLE_TESTS }

export default function Admin() {
  const [problems, setProblems] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => api('/admin/problems').then(setProblems).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  function edit(p) {
    setForm({ ...p, tests: JSON.stringify(p.tests, null, 2) })
    setMsg('')
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function save(e) {
    e.preventDefault()
    setMsg('')
    setError('')
    let tests
    try {
      tests = JSON.parse(form.tests)
      if (!Array.isArray(tests)) throw new Error()
    } catch {
      setError('Tests must be a valid JSON array')
      return
    }
    const body = {
      title: form.title,
      statement: form.statement,
      time_limit_sec: Number(form.time_limit_sec),
      memory_limit_mb: Number(form.memory_limit_mb),
      published: form.published,
      difficulty: form.difficulty,
      hint: form.hint || null,
      time_complexity: form.time_complexity || null,
      space_complexity: form.space_complexity || null,
      tests,
    }
    setSaving(true)
    try {
      const saved = form.id
        ? await api(`/admin/problems/${form.id}`, { method: 'PUT', body })
        : await api('/admin/problems', { method: 'POST', body })
      setForm({ ...saved, tests: JSON.stringify(saved.tests, null, 2) })
      setMsg(`Saved problem #${saved.id}`)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="page-head"><div><h1>Admin</h1><p className="muted">Create and edit problems. Editing replaces all of a problem’s tests.</p></div></div>
      <div className="admin-grid">
        <form onSubmit={save} className="panel form">
          <h2>{form.id ? `Edit problem #${form.id}` : 'New problem'}</h2>
          <label className="field"><span>Title</span><input value={form.title} onChange={set('title')} required /></label>
          <label className="field"><span>Statement</span><textarea rows={7} value={form.statement} onChange={set('statement')} required /></label>
          <div className="row3">
            <label className="field"><span>Time limit (s)</span><input type="number" step="0.1" min="0.1" max="15" value={form.time_limit_sec} onChange={set('time_limit_sec')} /></label>
            <label className="field"><span>Memory (MB)</span><input type="number" min="16" max="512" value={form.memory_limit_mb} onChange={set('memory_limit_mb')} /></label>
            <label className="field"><span>Difficulty</span>
              <select value={form.difficulty} onChange={set('difficulty')}><option>Easy</option><option>Medium</option><option>Hard</option></select>
            </label>
          </div>
          <label className="field"><span>Hint</span><textarea rows={3} value={form.hint || ''} onChange={set('hint')} /></label>
          <div className="row2">
            <label className="field"><span>Target time complexity</span><input value={form.time_complexity || ''} onChange={set('time_complexity')} maxLength={64} placeholder="O(n log n)" /></label>
            <label className="field"><span>Target space complexity</span><input value={form.space_complexity || ''} onChange={set('space_complexity')} maxLength={64} placeholder="O(n)" /></label>
          </div>
          <label className="field"><span>Tests: JSON array of {'{input, expected_output, is_sample}'} (order = test number)</span>
            <textarea className="mono" rows={12} value={form.tests} onChange={set('tests')} spellCheck={false} />
          </label>
          <label className="check-row"><input type="checkbox" checked={form.published} onChange={set('published')} /> Published (visible to participants)</label>
          {error && <p className="err">{error}</p>}
          {msg && <p className="ok">{msg}</p>}
          <div className="form-actions">
            <button className="btn primary" type="submit" disabled={saving}>{saving ? 'Saving…' : form.id ? 'Update problem' : 'Create problem'}</button>
            {form.id && <button className="btn ghost" type="button" onClick={() => { setForm(EMPTY); setMsg(''); setError('') }}>New problem</button>}
          </div>
        </form>

        <div className="panel flush admin-list">
          <table className="list">
            <thead><tr><th>#</th><th>Title</th><th>Level</th><th>Tests</th><th /></tr></thead>
            <tbody>
              {problems.map((p) => (
                <tr key={p.id} className={form.id === p.id ? 'me' : ''}>
                  <td className="mono dim">{p.id}</td>
                  <td>{p.title} {!p.published && <span className="chip">draft</span>}</td>
                  <td><Diff d={p.difficulty} /></td>
                  <td className="mono">{p.tests.length}</td>
                  <td><button className="btn ghost sm" onClick={() => edit(p)}>Edit</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
