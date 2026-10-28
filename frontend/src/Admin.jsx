import { useEffect, useState } from 'react'
import { api } from './api.js'

const EXAMPLE_TESTS = JSON.stringify(
  [
    { input: '1 2\n', expected_output: '3\n', is_sample: true },
    { input: '10 20\n', expected_output: '30\n', is_sample: false },
  ],
  null,
  2,
)

const EMPTY = { id: null, title: '', statement: '', time_limit_sec: 2, memory_limit_mb: 256, published: false, tests: EXAMPLE_TESTS }

export default function Admin() {
  const [problems, setProblems] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => api('/admin/problems').then(setProblems).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  function edit(p) {
    setForm({ ...p, tests: JSON.stringify(p.tests, null, 2) })
    setMsg('')
    setError('')
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
      tests,
    }
    try {
      const saved = form.id
        ? await api(`/admin/problems/${form.id}`, { method: 'PUT', body })
        : await api('/admin/problems', { method: 'POST', body })
      setForm({ ...saved, tests: JSON.stringify(saved.tests, null, 2) })
      setMsg(`Saved problem #${saved.id}`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <>
      <h2>Admin: problems</h2>
      <table>
        <thead><tr><th>#</th><th>Title</th><th>Published</th><th>Tests</th><th /></tr></thead>
        <tbody>
          {problems.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td><td>{p.title}</td><td>{p.published ? 'yes' : 'no'}</td><td>{p.tests.length}</td>
              <td><button onClick={() => edit(p)}>Edit</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={save} className="card">
        <h3>{form.id ? `Edit problem #${form.id}` : 'New problem'}</h3>
        <label>Title<input value={form.title} onChange={set('title')} required /></label>
        <label>Statement<textarea rows={6} value={form.statement} onChange={set('statement')} required /></label>
        <label>Time limit (seconds)<input type="number" step="0.1" min="0.1" max="15" value={form.time_limit_sec} onChange={set('time_limit_sec')} /></label>
        <label>Memory limit (MB)<input type="number" min="16" max="512" value={form.memory_limit_mb} onChange={set('memory_limit_mb')} /></label>
        <label className="inline"><input type="checkbox" checked={form.published} onChange={set('published')} /> Published</label>
        <label>Tests (JSON array of {'{input, expected_output, is_sample}'}; order = test position)
          <textarea className="code" rows={12} value={form.tests} onChange={set('tests')} spellCheck={false} />
        </label>
        {error && <p className="err">{error}</p>}
        {msg && <p className="ok">{msg}</p>}
        <button type="submit">{form.id ? 'Update' : 'Create'}</button>{' '}
        {form.id && <button type="button" onClick={() => { setForm(EMPTY); setMsg('') }}>New problem</button>}
      </form>
    </>
  )
}
