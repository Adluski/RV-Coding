import { useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import { AuthPage, Leaderboard, ProblemList, Submissions } from './pages.jsx'
import ProblemPage from './ProblemPage.jsx'
import Admin from './Admin.jsx'
import Particles from './Particles.jsx'

export default function App() {
  const [user, setUser] = useState(undefined) // undefined = loading, null = anonymous
  const nav = useNavigate()
  const loc = useLocation()
  const wide = loc.pathname.startsWith('/problems/')

  useEffect(() => {
    api('/auth/me').then(setUser).catch(() => setUser(null))
  }, [])

  async function logout() {
    await api('/auth/logout', { method: 'POST' }).catch(() => {})
    setUser(null)
    nav('/login')
  }

  const guard = (el, admin) =>
    !user ? <Navigate to="/login" replace /> : admin && user.role !== 'admin' ? <Navigate to="/" replace /> : el

  return (
    <>
      <Particles />
      <header className="topbar">
        <Link to="/" className="brand">rv<span>/</span>coding</Link>
        {user && (
          <nav className="links">
            <NavLink to="/" end>Problems</NavLink>
            <NavLink to="/submissions">Submissions</NavLink>
            <NavLink to="/leaderboard">Leaderboard</NavLink>
            {user.role === 'admin' && <NavLink to="/admin">Admin</NavLink>}
          </nav>
        )}
        <div className="spacer" />
        {user ? (
          <div className="who">
            <span className="avatar" aria-hidden="true">{user.username[0].toUpperCase()}</span>
            <span className="who-name">{user.username}</span>
            <button className="btn ghost sm" onClick={logout}>Log out</button>
          </div>
        ) : user === null ? (
          <nav className="links">
            <NavLink to="/login">Log in</NavLink>
            <NavLink to="/register">Register</NavLink>
          </nav>
        ) : null}
      </header>
      <main className={wide ? 'page wide' : 'page'}>
        {user === undefined ? (
          <p className="muted center-pad">Loading…</p>
        ) : (
          <Routes>
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage mode="login" onAuth={setUser} />} />
            <Route path="/register" element={user ? <Navigate to="/" replace /> : <AuthPage mode="register" onAuth={setUser} />} />
            <Route path="/" element={guard(<ProblemList />)} />
            <Route path="/problems/:id" element={guard(<ProblemPage />)} />
            <Route path="/submissions" element={guard(<Submissions />)} />
            <Route path="/leaderboard" element={guard(<Leaderboard user={user} />)} />
            <Route path="/admin" element={guard(<Admin />, true)} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
    </>
  )
}
