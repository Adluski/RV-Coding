import { useRef } from 'react'

const INDENT = '    '

// Plain textarea with a line-number gutter, Tab indentation and auto-indent on Enter.
export default function CodeEditor({ value, onChange, onRun, onSubmit, disabled }) {
  const ta = useRef(null)
  const gutter = useRef(null)
  const lines = value.split('\n').length

  function replace(start, end, text, caret) {
    const el = ta.current
    const next = value.slice(0, start) + text + value.slice(end)
    onChange(next)
    requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = caret })
  }

  function onKeyDown(e) {
    const el = e.target
    const { selectionStart: s, selectionEnd: t } = el
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      if (e.shiftKey) onSubmit?.()
      else onRun?.()
      return
    }
    if (e.key === 'Tab') {
      e.preventDefault()
      const lineStart = value.lastIndexOf('\n', s - 1) + 1
      if (e.shiftKey) {
        const lead = value.slice(lineStart).match(/^ {1,4}/)
        if (lead) replace(lineStart, lineStart + lead[0].length, '', Math.max(lineStart, s - lead[0].length))
      } else {
        replace(s, t, INDENT, s + INDENT.length)
      }
      return
    }
    if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault()
      const lineStart = value.lastIndexOf('\n', s - 1) + 1
      const line = value.slice(lineStart, s)
      let indent = line.match(/^[ \t]*/)[0]
      if (/[:{(\[]\s*$/.test(line)) indent += INDENT
      replace(s, t, '\n' + indent, s + 1 + indent.length)
    }
  }

  return (
    <div className={'editor' + (disabled ? ' editor-disabled' : '')}>
      <div className="gutter" ref={gutter} aria-hidden="true">
        {Array.from({ length: lines }, (_, i) => <div key={i}>{i + 1}</div>)}
      </div>
      <textarea
        ref={ta}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        onScroll={(e) => { if (gutter.current) gutter.current.scrollTop = e.target.scrollTop }}
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        autoCorrect="off"
        wrap="off"
        aria-label="Code editor"
      />
    </div>
  )
}
