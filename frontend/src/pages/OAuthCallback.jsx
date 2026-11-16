import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'
import styles from '../styles/Login.module.css'

// 구글/카카오 로그인 후 백엔드가 /oauth/callback#token=... 으로 보내준다.
// 토큰으로 내 정보를 받아 로그인 상태로 만든 뒤 홈으로 이동한다.
export default function OAuthCallback() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const done = useRef(false) // 개발 모드(StrictMode)에서 effect 가 두 번 도는 것 방지

  useEffect(() => {
    if (done.current) return
    done.current = true

    const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
    // 주소창에서 토큰을 지운다 (뒤로가기·복사로 새지 않게)
    window.history.replaceState(null, '', window.location.pathname)

    if (!token) {
      navigate('/login', { replace: true, state: { error: '로그인 정보를 받지 못했습니다' } })
      return
    }

    fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(me => {
        login(token, me)
        navigate(me.role === 'admin' ? '/admin' : '/', { replace: true })
      })
      .catch(() => navigate('/login', { replace: true, state: { error: '로그인에 실패했습니다. 다시 시도해주세요' } }))
  }, [login, navigate])

  return (
    <div className={styles.page}>
      <div className={styles.card} style={{ textAlign: 'center' }}>
        <span className={styles.spinner} />
        <p className={styles.sub} style={{ marginTop: 16 }}>로그인 중이에요…</p>
      </div>
    </div>
  )
}
