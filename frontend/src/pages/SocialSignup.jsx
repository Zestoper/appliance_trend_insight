import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'
import styles from '../styles/Login.module.css'
import s from '../styles/Signup.module.css'

// 카카오 · 구글로 처음 로그인한 사람의 약관 동의 화면.
// 여기서 동의해야 서버가 회원을 만든다 (POST /api/auth/social/complete). 기존 회원은 이 화면을 거치지 않는다.
const PROVIDER_NAME = { kakao: '카카오', google: 'Google' }

export default function SocialSignup() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [nickname, setNickname] = useState(state?.name || '')
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [agreePrivacy, setAgreePrivacy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const agreeAll = agreeTerms && agreePrivacy

  // 새로고침 등으로 가입 티켓이 없으면 로그인부터 다시
  if (!state?.ticket) return <Navigate to="/login" replace />

  async function submit() {
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API_BASE}/api/auth/social/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket: state.ticket, agree_terms: agreeAll, nickname: nickname.trim() }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || '가입에 실패했어요. 다시 시도해 주세요')
      const me = await fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${data.token}` } })
        .then(res => (res.ok ? res.json() : {}))
      login(data.token, me)
      navigate('/', { replace: true })
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>거의 다 됐어요</h1>
        <p className={styles.sub}>
          {PROVIDER_NAME[state.provider] || '소셜'} 계정으로 처음 오셨네요. 약관에 동의하면 가입이 끝나요
        </p>

        <div className={styles.field} style={{ marginTop: 20 }}>
          <input id="nickname" type="text" className={styles.input} placeholder=" "
            value={nickname} onChange={e => setNickname(e.target.value)} maxLength={100} />
          <label htmlFor="nickname" className={styles.floatLabel}>닉네임</label>
        </div>

        <div className={s.agreeBox}>
          <label className={`${s.agreeRow} ${s.agreeAll}`}>
            <input type="checkbox" checked={agreeAll}
              onChange={e => { setAgreeTerms(e.target.checked); setAgreePrivacy(e.target.checked) }} />
            전체 동의
          </label>
          <label className={s.agreeRow}>
            <input type="checkbox" checked={agreeTerms} onChange={e => setAgreeTerms(e.target.checked)} />
            <span>[필수] 이용약관 동의</span>
            <Link to="/terms" target="_blank" className={s.agreeView}>보기</Link>
          </label>
          <label className={s.agreeRow}>
            <input type="checkbox" checked={agreePrivacy} onChange={e => setAgreePrivacy(e.target.checked)} />
            <span>[필수] 개인정보 수집 · 이용 동의</span>
            <Link to="/privacy" target="_blank" className={s.agreeView}>보기</Link>
          </label>
        </div>

        {error && <p className={styles.errorMsg}>{error}</p>}

        <button className={styles.submitBtn} style={{ marginTop: 16 }}
          disabled={!agreeAll || !nickname.trim() || loading} onClick={submit}>
          {loading ? <span className={styles.spinner} /> : '동의하고 시작하기'}
        </button>
        <p className={styles.signupRow}>
          <Link to="/login">취소하고 돌아가기</Link>
        </p>
      </div>
    </div>
  )
}
