import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import { AuthPage, Leaderboard, ProblemList, ProblemPage, Submissions } from './pages.jsx'
import Admin from './Admin.jsx'

export default function App() {
  const [user, setUser] = useState(undefined) // undefined = loading, null = anonymous
  const nav = useNavigate()

  useEffect(() => {
    api('/auth/me').then(setUser).catch(() => setUser(null))
  }, [])

  async function logout() {
    await api('/auth/logout', { method: 'POST' }).catch(() => {})
    setUser(null)
    nav('/login')
  }

  if (user === undefined) return <p className="wrap">Loading…</p>

  const guard = (el, admin) => (!user ? <Navigate to="/login" /> : admin && user.role !== 'admin' ? <Navigate to="/" /> : el)

  return (
    <>
      <nav>
        <b>Online Judge</b>
        {user && (
          <>
            <Link to="/">Problems</Link>
            <Link to="/submissions">My submissions</Link>
            <Link to="/leaderboard">Leaderboard</Link>
            {user.role === 'admin' && <Link to="/admin">Admin</Link>}
            <span className="spacer" />
            <span>{user.username}</span>
            <button onClick={logout}>Log out</button>
          </>
        )}
        {!user && (
          <>
            <span className="spacer" />
            <Link to="/login">Log in</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
      <main className="wrap">
        <Routes>
          <Route path="/login" element={<AuthPage mode="login" onAuth={setUser} />} />
          <Route path="/register" element={<AuthPage mode="register" onAuth={setUser} />} />
          <Route path="/" element={guard(<ProblemList />)} />
          <Route path="/problems/:id" element={guard(<ProblemPage />)} />
          <Route path="/submissions" element={guard(<Submissions />)} />
          <Route path="/leaderboard" element={guard(<Leaderboard />)} />
          <Route path="/admin" element={guard(<Admin />, true)} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </>
  )
}
