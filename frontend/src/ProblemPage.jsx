import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from './api.js'
import CodeEditor from './CodeEditor.jsx'
import { Diff, Spinner, VERDICT_TEXT, Verdict, fmtMem, fmtMs, storage } from './ui.jsx'

const TEMPLATES = {
  python: 'import sys\n\n\ndef main():\n    data = sys.stdin.read().split()\n    \n\n\nmain()\n',
  cpp: '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    \n    return 0;\n}\n',
}
const LANG_LABEL = { python: 'Python 3', cpp: 'C++17' }
const POLL_MS = 2000
const GIVE_UP_MS = 5 * 60 * 1000

export default function ProblemPage() {
  const { id } = useParams()
  const [p, setP] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [lang, setLang] = useState(() => storage.get('lang') || 'python')
  const [code, setCode] = useState('')
  const [tab, setTab] = useState('testcase')
  const [caseIdx, setCaseIdx] = useState(0)
  const [useCustom, setUseCustom] = useState(false)
  const [customInput, setCustomInput] = useState('')
  const [busy, setBusy] = useState(null) // null | 'run' | 'submit'
  const [elapsed, setElapsed] = useState(0)
  const [result, setResult] = useState(null) // {kind: 'run'|'submit', data}
  const [error, setError] = useState('')
  const [claimedTime, setClaimedTime] = useState('')
  const [claimedSpace, setClaimedSpace] = useState('')
  const [resetArmed, setResetArmed] = useState(false)
  const gen = useRef(0) // bumps on every new action; stale polls check it and stop
  const timer = useRef(null)

  const draftKey = `draft:${id}:${lang}`

  useEffect(() => {
    setP(null)
    setLoadError('')
    setResult(null)
    setCaseIdx(0)
    api(`/problems/${id}`).then(setP).catch((e) => setLoadError(e.message))
  }, [id])

  useEffect(() => {
    setCode(storage.get(draftKey) ?? TEMPLATES[lang])
    storage.set('lang', lang)
  }, [draftKey, lang])

  useEffect(() => () => { gen.current++; clearTimeout(timer.current) }, [])

  useEffect(() => {
    if (!busy) return
    const started = Date.now()
    setElapsed(0)
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(t)
  }, [busy])

  function edit(v) {
    setCode(v)
    storage.set(draftKey, v)
    setResetArmed(false)
  }

  function reset() {
    if (!resetArmed) { setResetArmed(true); return }
    edit(TEMPLATES[lang])
  }

  function poll(fn, onDone, started, g) {
    timer.current = setTimeout(async () => {
      if (g !== gen.current) return
      try {
        const r = await fn()
        if (g !== gen.current) return
        if (r.status === 'done') { onDone(r); setBusy(null); return }
        if (Date.now() - started > GIVE_UP_MS) { setError('The judge is taking too long. Check My submissions later.'); setBusy(null); return }
        if (r.message) setError(r.message); else setError('')
        poll(fn, onDone, started, g)
      } catch (e) {
        if (g !== gen.current) return
        setError(e.message)
        setBusy(null)
      }
    }, POLL_MS)
  }

  async function runCode() {
    if (busy || !code.trim()) return
    const g = ++gen.current
    clearTimeout(timer.current)
    setError('')
    setBusy('run')
    setTab('result')
    try {
      const body = { problem_id: Number(id), language: lang, source_code: code }
      if (useCustom) body.custom_input = customInput
      const { run_token } = await api('/run', { method: 'POST', body })
      poll(() => api('/run?token=' + encodeURIComponent(run_token)), (data) => { setResult({ kind: 'run', data }); setCaseIdx(0) }, Date.now(), g)
    } catch (e) {
      setError(e.message)
      setBusy(null)
    }
  }

  async function submitCode() {
    if (busy || !code.trim()) return
    const g = ++gen.current
    clearTimeout(timer.current)
    setError('')
    setBusy('submit')
    setTab('result')
    try {
      const { id: sid } = await api('/submissions', {
        method: 'POST',
        body: { problem_id: Number(id), language: lang, source_code: code, claimed_time: claimedTime, claimed_space: claimedSpace },
      })
      poll(() => api(`/submissions/${sid}`), (data) => {
        setResult({ kind: 'submit', data })
        if (data.verdict === 'AC') setP((cur) => cur && { ...cur, solvedNow: true })
      }, Date.now(), g)
    } catch (e) {
      setError(e.message)
      setBusy(null)
    }
  }

  if (loadError) return <div className="panel empty">{loadError}. <Link to="/">Back to problems</Link></div>
  if (!p) return <p className="muted center-pad">Loading problem…</p>

  const samples = p.samples
  return (
    <div className="ws">
      <section className="pane statement-pane">
        <div className="pane-inner">
          <Link to="/" className="back">← Problems</Link>
          <h1 className="ptitle">{p.title}</h1>
          <div className="meta">
            <Diff d={p.difficulty} />
            <span className="chip mono">time {p.time_limit_sec}s</span>
            <span className="chip mono">memory {p.memory_limit_mb} MB</span>
            {p.solvedNow && <span className="chip ok">Solved</span>}
          </div>
          <div className="statement">{p.statement}</div>

          {samples.map((s, i) => (
            <div className="example" key={s.position}>
              <div className="example-title">Example {i + 1}</div>
              <div className="io">
                <div><div className="io-label">Input</div><pre>{s.input}</pre></div>
                <div><div className="io-label">Output</div><pre>{s.expected_output}</pre></div>
              </div>
            </div>
          ))}

          {p.hint && (
            <details className="reveal">
              <summary>Hint</summary>
              <p>{p.hint}</p>
            </details>
          )}
          {(p.time_complexity || p.space_complexity) && (
            <details className="reveal">
              <summary>Target complexity <span className="dim small">(spoils the approach)</span></summary>
              <p className="mono">Time {p.time_complexity || '–'} · Space {p.space_complexity || '–'}</p>
              <p className="muted small">This is the complexity of the intended solution. Your code’s complexity is not measured; large hidden tests only catch solutions that are far too slow.</p>
            </details>
          )}
          <p className="muted small footnote">Your code and this problem’s tests are sent to the hosted Judge0 service to run.</p>
        </div>
      </section>

      <section className="pane code-pane">
        <div className="code-bar">
          <select value={lang} onChange={(e) => { setLang(e.target.value); setResetArmed(false) }} aria-label="Language">
            <option value="python">Python 3</option>
            <option value="cpp">C++17</option>
          </select>
          <span className="dim small kbd-hint">Ctrl+Enter run · Ctrl+Shift+Enter submit</span>
          <div className="spacer" />
          <button className="btn ghost sm" onClick={reset}>{resetArmed ? 'Click again to reset' : 'Reset code'}</button>
        </div>

        <CodeEditor value={code} onChange={edit} onRun={runCode} onSubmit={submitCode} />

        <div className="console">
          <div className="console-tabs">
            <button className={tab === 'testcase' ? 'on' : ''} onClick={() => setTab('testcase')}>Testcase</button>
            <button className={tab === 'result' ? 'on' : ''} onClick={() => setTab('result')}>
              Result {result && !busy && <Verdict v={result.data.verdict} />}
            </button>
          </div>
          <div className="console-body">
            {tab === 'testcase' ? (
              <TestcaseTab samples={samples} caseIdx={caseIdx} setCaseIdx={setCaseIdx} useCustom={useCustom}
                setUseCustom={setUseCustom} customInput={customInput} setCustomInput={setCustomInput} />
            ) : busy ? (
              <div className="judging"><Spinner /> {busy === 'run' ? 'Running your code' : 'Judging on all tests'}… <span className="mono dim">{elapsed}s</span>
                {error && <p className="warn small">{error}</p>}
              </div>
            ) : error && !result ? (
              <p className="err">{error}</p>
            ) : !result ? (
              <p className="muted">Run your code to see the output here, or submit it to be judged on every test.</p>
            ) : result.kind === 'run' ? (
              <RunResult r={result.data} caseIdx={caseIdx} setCaseIdx={setCaseIdx} error={error} />
            ) : (
              <SubmitResult s={result.data} p={p} error={error} />
            )}
          </div>
        </div>

        <div className="action-bar">
          <div className="claims">
            <span className="dim small">Your complexity (optional)</span>
            <input placeholder="time, e.g. O(n)" value={claimedTime} maxLength={64} onChange={(e) => setClaimedTime(e.target.value)} aria-label="Your time complexity" />
            <input placeholder="space, e.g. O(1)" value={claimedSpace} maxLength={64} onChange={(e) => setClaimedSpace(e.target.value)} aria-label="Your space complexity" />
          </div>
          <div className="spacer" />
          <button className="btn" onClick={runCode} disabled={!!busy || !code.trim()}>{busy === 'run' ? <><Spinner /> Running</> : 'Run'}</button>
          <button className="btn primary" onClick={submitCode} disabled={!!busy || !code.trim()}>{busy === 'submit' ? <><Spinner /> Judging</> : 'Submit'}</button>
        </div>
      </section>
    </div>
  )
}

function TestcaseTab({ samples, caseIdx, setCaseIdx, useCustom, setUseCustom, customInput, setCustomInput }) {
  return (
    <>
      <div className="cases">
        {samples.map((s, i) => (
          <button key={s.position} className={!useCustom && caseIdx === i ? 'case on' : 'case'} onClick={() => { setUseCustom(false); setCaseIdx(i) }}>Case {i + 1}</button>
        ))}
        <button className={useCustom ? 'case on' : 'case'} onClick={() => setUseCustom(true)}>Custom input</button>
      </div>
      {useCustom ? (
        <>
          <textarea className="custom-input mono" rows={5} value={customInput} onChange={(e) => setCustomInput(e.target.value)}
            placeholder="Type the exact stdin your program should receive" spellCheck={false} />
          <p className="dim small">Run uses this input instead of the examples. There is no expected output, so you just see what your program prints.</p>
        </>
      ) : samples.length ? (
        <>
          <div className="io-label">Input</div>
          <pre>{samples[caseIdx]?.input}</pre>
          <div className="io-label">Expected output</div>
          <pre>{samples[caseIdx]?.expected_output}</pre>
          <p className="dim small">Run checks your code against all {samples.length} example{samples.length > 1 ? 's' : ''}. Submit judges it on the hidden tests too.</p>
        </>
      ) : (
        <p className="muted">This problem has no examples. Use custom input to try your code.</p>
      )}
    </>
  )
}

function RunResult({ r, caseIdx, setCaseIdx, error }) {
  const c = r.cases[Math.min(caseIdx, r.cases.length - 1)]
  return (
    <>
      <div className="result-head">
        <span className={'big v-' + r.verdict}>{VERDICT_TEXT[r.verdict] || r.verdict}</span>
        <span className="dim small">{r.custom ? 'custom input' : `${r.cases.filter((x) => x.verdict === 'AC').length}/${r.cases.length} examples passed`}</span>
      </div>
      {error && <p className="warn small">{error}</p>}
      {r.verdict === 'CE' ? (
        <pre className="out err-out">{r.compile_output}</pre>
      ) : r.verdict === 'ERR' ? (
        <p className="warn">{r.message}</p>
      ) : (
        <>
          {r.cases.length > 1 && (
            <div className="cases">
              {r.cases.map((x, i) => (
                <button key={i} className={(caseIdx === i ? 'case on ' : 'case ') + (x.verdict === 'AC' ? 'pass' : 'fail')} onClick={() => setCaseIdx(i)}>
                  <span className="dot" /> Case {i + 1}
                </button>
              ))}
            </div>
          )}
          <div className="usage mono small dim">{fmtMs(c.runtime_ms)} · {fmtMem(c.memory_kb)}{c.verdict !== 'AC' && c.verdict !== 'OK' && ` · ${VERDICT_TEXT[c.verdict]}`}</div>
          {c.input != null && <><div className="io-label">Input</div><pre>{c.input}</pre></>}
          <div className="io-label">Your output</div>
          <pre className={c.verdict === 'WA' ? 'out bad' : 'out'}>{c.stdout || <span className="dim">(no output)</span>}</pre>
          {c.expected_output != null && <><div className="io-label">Expected</div><pre>{c.expected_output}</pre></>}
          {c.stderr && <><div className="io-label">stderr</div><pre className="out err-out">{c.stderr}</pre></>}
        </>
      )}
    </>
  )
}

function Meter({ label, value, limit, fmt }) {
  const pct = limit ? Math.min(100, (100 * (value || 0)) / limit) : 0
  return (
    <div className="meter">
      <div className="meter-top"><span className="dim small">{label}</span><span className="mono">{fmt(value)}</span></div>
      <div className="bar"><div className="fill f-accent" style={{ width: pct + '%' }} /></div>
      <div className="dim small mono">{pct.toFixed(pct < 10 ? 1 : 0)}% of the {fmt(limit)} limit</div>
    </div>
  )
}

function SubmitResult({ s, p, error }) {
  const maxMs = Math.max(1, ...s.tests.map((t) => t.runtime_ms))
  return (
    <>
      <div className="result-head">
        <span className={'big v-' + s.verdict}>{VERDICT_TEXT[s.verdict] || s.verdict}</span>
        {s.tests_total != null && s.tests_passed != null && (
          <span className="mono">{s.tests_passed} / {s.tests_total} tests passed</span>
        )}
      </div>
      {error && <p className="warn small">{error}</p>}
      {s.verdict === 'CE' && <pre className="out err-out">{s.message}</pre>}
      {s.verdict === 'ERR' && <p className="warn">{s.message}</p>}
      {['WA', 'TLE', 'RE'].includes(s.verdict) && <p className="muted">{s.message}. Hidden test contents are not shown.</p>}

      {s.runtime_ms != null && (
        <div className="meters">
          <Meter label="Runtime (slowest test)" value={s.runtime_ms} limit={p.time_limit_sec * 1000} fmt={fmtMs} />
          <Meter label="Memory (peak)" value={s.memory_kb} limit={p.memory_limit_mb * 1024} fmt={fmtMem} />
        </div>
      )}

      {s.tests.length > 0 && (
        <>
          <div className="io-label">Per-test runtime</div>
          <div className="strip" role="img" aria-label="Runtime of each test">
            {s.tests.map((t) => (
              <div key={t.position} className={'tick v-bg-' + t.verdict} style={{ height: 6 + (34 * t.runtime_ms) / maxMs + 'px' }}
                title={`Test ${t.position}: ${VERDICT_TEXT[t.verdict]} · ${t.runtime_ms} ms · ${fmtMem(t.memory_kb)}`} />
            ))}
            {s.tests_total > s.tests.length && Array.from({ length: s.tests_total - s.tests.length }, (_, i) => (
              <div key={'n' + i} className="tick skipped" title="Not checked (stopped at the first failure)" />
            ))}
          </div>
        </>
      )}

      <div className="complexity">
        <div><span className="dim small">Your stated complexity</span><div className="mono">{s.claimed_time || s.claimed_space ? `Time ${s.claimed_time || '–'} · Space ${s.claimed_space || '–'}` : '—'}</div></div>
        {s.verdict === 'AC' && (p.time_complexity || p.space_complexity) && (
          <div><span className="dim small">Intended solution</span><div className="mono">Time {p.time_complexity || '–'} · Space {p.space_complexity || '–'}</div></div>
        )}
      </div>
      <p className="dim small">Runtime and memory are measured by Judge0. Complexity is not measured; the values above are what you entered and, after an accept, the intended target.</p>
    </>
  )
}
