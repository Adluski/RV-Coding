export const VERDICT_TEXT = {
  AC: 'Accepted', WA: 'Wrong Answer', TLE: 'Time Limit Exceeded', RE: 'Runtime Error',
  CE: 'Compilation Error', ERR: 'Judge Error', OK: 'Finished',
}

export function Verdict({ v, long }) {
  if (!v) return <span className="pill pending">Judging</span>
  return <span className={'pill v-' + v}>{long ? VERDICT_TEXT[v] || v : v}</span>
}

export function Diff({ d }) {
  return <span className={'diff d-' + d}>{d}</span>
}

export function Check() {
  return (
    <svg className="check" viewBox="0 0 16 16" width="16" height="16" aria-label="Solved">
      <circle cx="8" cy="8" r="7.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4.8 8.2l2.1 2.1 4.3-4.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />
}

export function fmtMem(kb) {
  if (kb == null) return '–'
  if (kb < 1024) return kb + ' KB'
  const mb = kb / 1024
  return (Number.isInteger(mb) ? mb : mb.toFixed(1)) + ' MB'
}

export function fmtMs(ms) {
  return ms == null ? '–' : ms + ' ms'
}

export function ago(iso) {
  if (!iso) return ''
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return Math.floor(s / 60) + 'm ago'
  if (s < 86400) return Math.floor(s / 3600) + 'h ago'
  return new Date(iso).toLocaleDateString()
}

export const storage = {
  get(k) { try { return window.localStorage.getItem(k) } catch { return null } },
  set(k, v) { try { window.localStorage.setItem(k, v) } catch { /* private mode etc. */ } },
}
