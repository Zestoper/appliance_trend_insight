import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { API_BASE } from '../config'

const AuthContext = createContext(null)

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

function loadFromStorage() {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const user  = JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    return { token, user }
  } catch {
    return { token: null, user: null }
  }
}

export function AuthProvider({ children }) {
  const initial = loadFromStorage()
  const [token, setToken] = useState(initial.token)
  const [user, setUser] = useState(initial.user)

  const login = useCallback((tokenValue, userInfo) => {
    setToken(tokenValue)
    setUser(userInfo)
    localStorage.setItem(TOKEN_KEY, tokenValue)
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }, [])

  const updateUser = useCallback((partial) => {
    setUser(prev => {
      const next = { ...prev, ...partial }
      localStorage.setItem(USER_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  // localStorage에 남은 토큰은 서버 검증 없이 복원되므로, 만료·탈퇴 등으로 이미
  // 무효해진 토큰도 "로그인된 것처럼" 보이다가 실제 API 호출에서만 뒤늦게 401이
  // 나는 문제가 있었다 — 앱 로드 시 한 번 서버에 확인해 무효하면 바로 로그아웃시킨다.
  useEffect(() => {
    if (!initial.token) return
    fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${initial.token}` },
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => updateUser(data))
      .catch(() => logout())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, isLoggedIn: !!token, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
