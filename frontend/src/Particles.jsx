import { useEffect, useRef } from 'react'

// A quiet constellation behind the page: slow drifting points, faint links between close neighbours,
// and a gentle pull toward the cursor. Pure canvas + requestAnimationFrame; no React state per frame.
export default function Particles() {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas.getContext('2d')
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)')
    const scheme = window.matchMedia('(prefers-color-scheme: light)')
    let w = 0, h = 0, dpr = 1, raf = 0, pts = [], color = '232,163,61'
    const mouse = { x: -9999, y: -9999 }
    const LINK = 120

    function readColor() {
      color = getComputedStyle(document.documentElement).getPropertyValue('--particle').trim() || color
    }

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      const n = Math.min(90, Math.round((w * h) / 16000))
      pts = Array.from({ length: n }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.4 + 0.6,
      }))
    }

    function draw() {
      ctx.clearRect(0, 0, w, h)
      for (const p of pts) {
        const dx = mouse.x - p.x, dy = mouse.y - p.y
        const d2 = dx * dx + dy * dy
        if (d2 < 180 * 180) { p.vx += dx * 0.00002; p.vy += dy * 0.00002 }
        p.vx = Math.max(-0.45, Math.min(0.45, p.vx * 0.999))
        p.vy = Math.max(-0.45, Math.min(0.45, p.vy * 0.999))
        p.x += p.vx
        p.y += p.vy
        if (p.x < -10) p.x = w + 10; else if (p.x > w + 10) p.x = -10
        if (p.y < -10) p.y = h + 10; else if (p.y > h + 10) p.y = -10
      }
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i]
        for (let j = i + 1; j < pts.length; j++) {
          const b = pts[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const d = Math.hypot(dx, dy)
          if (d < LINK) {
            ctx.strokeStyle = `rgba(${color},${(1 - d / LINK) * 0.16})`
            ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke()
          }
        }
        const md = Math.hypot(mouse.x - a.x, mouse.y - a.y)
        if (md < 160) {
          ctx.strokeStyle = `rgba(${color},${(1 - md / 160) * 0.28})`
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke()
        }
        ctx.fillStyle = `rgba(${color},0.55)`
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2); ctx.fill()
      }
    }

    function loop() {
      draw()
      raf = requestAnimationFrame(loop)
    }

    function start() {
      cancelAnimationFrame(raf)
      if (reduce.matches) draw() // one still frame
      else raf = requestAnimationFrame(loop)
    }

    const onMove = (e) => { mouse.x = e.clientX; mouse.y = e.clientY }
    const onLeave = () => { mouse.x = mouse.y = -9999 }
    const onVis = () => (document.hidden ? cancelAnimationFrame(raf) : start())
    const onResize = () => { resize(); start() }
    const onScheme = () => { readColor(); start() }

    readColor()
    resize()
    start()
    window.addEventListener('resize', onResize)
    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerleave', onLeave)
    document.addEventListener('visibilitychange', onVis)
    reduce.addEventListener?.('change', start)
    scheme.addEventListener?.('change', onScheme)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerleave', onLeave)
      document.removeEventListener('visibilitychange', onVis)
      reduce.removeEventListener?.('change', start)
      scheme.removeEventListener?.('change', onScheme)
    }
  }, [])

  return <canvas ref={ref} className="particles" aria-hidden="true" />
}
