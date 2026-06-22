import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from '../styles/Login.module.css'
import s from '../styles/Signup.module.css'
import { API_BASE } from '../config'

const STEPS = [
  { label: '이메일',   icon: '📧' },
  { label: '인증코드', icon: '🔑' },
  { label: '비밀번호', icon: '🔒' },
  { label: '프로필',   icon: '👤' },
]

function EyeIcon({ hidden }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {hidden ? (
        <>
          <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 2 12 2 12a20.29 20.29 0 0 1 5.06-5.94" />
          <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 10 8 10 8a20.78 20.78 0 0 1-2.16 3.19" />
          <path d="M14.12 14.12A3 3 0 0 1 9.88 9.88" />
          <path d="M1 1l22 22" />
        </>
      ) : (
        <>
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
          <circle cx="12" cy="12" r="3" />
        </>
      )}
    </svg>
  )
}

function getPwStrength(pw) {
  if (!pw) return null
  let score = 0
  if (pw.length >= 6)  score++
  if (pw.length >= 10) score++
  if (/[0-9]/.test(pw)) score++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pw)) score++
  if (/[A-Z]/.test(pw)) score++
  if (score <= 1) return { bars: 1, label: '취약', color: '#ef4444' }
  if (score <= 3) return { bars: 2, label: '보통', color: '#f59e0b' }
  return               { bars: 3, label: '강함', color: '#22c55e' }
}

// 카운트다운 훅 (초 단위)
function useCountdown(initial) {
  const [sec, setSec] = useState(0)
  const ref = useRef(null)
  function start() {
    clearInterval(ref.current)
    setSec(initial)
    ref.current = setInterval(() => {
      setSec(v => { if (v <= 1) { clearInterval(ref.current); return 0 } return v - 1 })
    }, 1000)
  }
  useEffect(() => () => clearInterval(ref.current), [])
  const mm = String(Math.floor(sec / 60)).padStart(2, '0')
  const ss = String(sec % 60).padStart(2, '0')
  return { display: `${mm}:${ss}`, active: sec > 0, start }
}

export default function Signup() {
  const [step, setStep] = useState(0)
  const [userType, setUserType] = useState('b2c')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const digitRefs = useRef([])

  const updateDigits = useCallback((next) => {
    setDigits(next)
    setCode(next.join(''))
    setError('')
  }, [])

  function handleDigitChange(i, val) {
    const d = val.replace(/\D/g, '').slice(-1)
    const next = [...digits]
    next[i] = d
    updateDigits(next)
    if (d && i < 5) digitRefs.current[i + 1]?.focus()
  }

  function handleDigitKeyDown(i, e) {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      digitRefs.current[i - 1]?.focus()
    }
    if (e.key === 'Enter' && code.length === 6) next()
  }

  function handleDigitPaste(e) {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    const next = [...digits]
    pasted.split('').forEach((c, i) => { next[i] = c })
    updateDigits(next)
    const focusIdx = Math.min(pasted.length, 5)
    digitRefs.current[focusIdx]?.focus()
  }
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [businessType, setBusinessType] = useState('')
  const [contactPhone, setContactPhone] = useState('')

  const pwStrength = getPwStrength(password)
  const countdown = useCountdown(600)

  useEffect(() => {
    if (step === 1) setTimeout(() => digitRefs.current[0]?.focus(), 350)
  }, [step])
  const { login } = useAuth()
  const navigate = useNavigate()

  const canNext = [
    !!email,
    code.length === 6 && countdown.active,
    password.length >= 6,
    userType === 'b2c' ? !!nickname : !!companyName && !!businessType,
  ][step]

  // Step 0 → 인증코드 발송
  async function sendCode() {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      setError('올바른 이메일 주소를 입력해주세요')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res  = await fetch(`${API_BASE}/api/auth/send-code`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || '발송 실패'); setLoading(false); return }
      // 개발 모드: 응답에 코드 포함
      if (data.dev_code) setCode(data.dev_code)
      countdown.start()
      setStep(1)
    } catch { setError('서버에 연결할 수 없습니다') }
    finally  { setLoading(false) }
  }

  // Step 1 → 인증코드 확인
  async function verifyCode() {
    setLoading(true)
    setError('')
    try {
      const res  = await fetch(`${API_BASE}/api/auth/verify-code`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || '인증 실패'); setLoading(false); return }
      setStep(2)
    } catch { setError('서버에 연결할 수 없습니다') }
    finally  { setLoading(false) }
  }

  // Step 3 → 최종 가입
  async function handleSubmit() {
    setLoading(true)
    setError('')
    const url  = `${API_BASE}/api/auth/signup/${userType}`
    const body = userType === 'b2c'
      ? { email, password, nickname }
      : { email, password, company_name: companyName, business_type: businessType, contact_phone: contactPhone }
    try {
      const res  = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || '가입 실패'); setLoading(false); return }
      if (data.status === 'pending') {
        navigate('/signup/pending', { state: { company_name: data.company_name, email } })
        return
      }
      login(data.token, { user_type: data.user_type, nickname: data.nickname || '', company_name: data.company_name || '', email })
      navigate('/')
    } catch { setError('서버에 연결할 수 없습니다') }
    finally  { setLoading(false) }
  }

  function next() {
    if (!canNext || loading) return
    if (step === 0) { sendCode();    return }
    if (step === 1) { verifyCode();  return }
    if (step === 3) { handleSubmit(); return }
    setError('')
    setStep(s => s + 1)
  }

  function prev() {
    if (step === 0) return
    setError('')
    setStep(s => s - 1)
  }

  return (
    <div className={styles.page}>
      <style>{`
        @keyframes lineGrow {
          from { width: 0%; }
          to   { width: 100%; }
        }
        .line-grow { animation: lineGrow 0.7s cubic-bezier(0.4,0,0.2,1) forwards; }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .fade-up { animation: fadeUp 0.35s ease forwards; }
      `}</style>

      <div className={styles.blobWrap}>
        <div className={`${styles.blob} ${styles.blobIndigo}`} />
        <div className={`${styles.blob} ${styles.blobPurple}`} />
      </div>

      <div className={`${styles.card} ${s.card}`}>
        <div className={styles.logo} onClick={() => navigate('/')}>
          <div className={styles.logoIcon}>A</div>
          <span className={styles.logoText}>가전무쌍</span>
        </div>

        <div className={s.progressWrap}>
          {STEPS.slice(0, -1).map((_, i) => {
            const filled = step > i
            return (
              <div key={i} className={s.segTrack}
                style={{ left: `calc(${12.5 + 25 * i}% + 20px)`, width: 'calc(25% - 40px)' }}>
                {filled && <div key={`seg-${i}-${step}`} className={`${s.segFill} line-grow`} />}
              </div>
            )
          })}
          {STEPS.map((st, i) => {
            const done = i < step, active = i === step
            return (
              <div key={i} className={s.stepItem}>
                <div className={s.stepCircle} style={{
                  background: done   ? 'linear-gradient(135deg,#6366f1,#a855f7)' : 'transparent',
                  border:     active ? '2px solid #6366f1' : done ? 'none' : '2px solid rgba(255,255,255,0.15)',
                  color:      done   ? 'white' : active ? '#818cf8' : 'rgba(255,255,255,0.25)',
                  boxShadow:  active ? '0 0 0 4px rgba(99,102,241,0.2)' : 'none',
                }}>
                  {done ? '✓' : i + 1}
                </div>
                <span className={s.stepLabel} style={{ color: done || active ? 'var(--text)' : 'rgba(255,255,255,0.2)' }}>
                  {st.label}
                </span>
              </div>
            )
          })}
        </div>

        <div key={step} className={`${s.stepContent} fade-up`}>

          {step === 0 && (
            <>
              <p className={styles.sub} style={{ marginBottom: 8 }}>
                가입할 이메일을 입력하세요
              </p>
              <div className={styles.field}>
                <input id="email" type="email" className={styles.input} placeholder=" "
                  value={email}
                  onChange={e => { setEmail(e.target.value); setError('') }}
                  onKeyDown={e => { if (!e.nativeEvent.isComposing && e.key === 'Enter') next() }} />
                <label htmlFor="email" className={styles.floatLabel}>이메일</label>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <p className={styles.sub} style={{ marginBottom: 16 }}>
                <strong style={{ color: 'var(--text)' }}>{email}</strong>로<br />
                인증코드를 발송했어요
              </p>
              <div className={s.otpWrap}>
                {digits.map((d, i) => (
                  <input
                    key={i}
                    ref={el => digitRefs.current[i] = el}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    className={s.otpBox}
                    value={d}
                    onChange={e => handleDigitChange(i, e.target.value)}
                    onKeyDown={e => handleDigitKeyDown(i, e)}
                    onPaste={i === 0 ? handleDigitPaste : undefined}
                    onFocus={e => e.target.select()}
                  />
                ))}
              </div>
              <div className={s.codeRow}>
                {countdown.active
                  ? <span className={s.countdown}>{countdown.display} 후 만료</span>
                  : <span className={s.countdownExpired}>만료됨</span>
                }
                <button type="button" className={s.resendBtn}
                  onClick={sendCode} disabled={loading}>
                  재발송
                </button>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <p className={styles.sub} style={{ marginBottom: 8 }}>사용할 비밀번호를 설정하세요</p>
              <div className={styles.field}>
                <input id="password" type={showPw ? 'text' : 'password'} className={styles.input}
                  placeholder=" " value={password}
                  onChange={e => { setPassword(e.target.value); setError('') }}
                  style={{ paddingRight: '44px' }}
                  onKeyDown={e => { if (!e.nativeEvent.isComposing && e.key === 'Enter') next() }} />
                <label htmlFor="password" className={styles.floatLabel}>비밀번호 (6자 이상)</label>
                <button type="button" className={styles.eyeBtn} onClick={() => setShowPw(v => !v)}>
                  <EyeIcon hidden={!showPw} />
                </button>
              </div>
              {password && pwStrength && (
                <div className={s.pwStrength}>
                  <div className={s.pwBars}>
                    {[1, 2, 3].map(n => (
                      <div key={n} className={s.pwBar} style={{
                        background: n <= pwStrength.bars ? pwStrength.color : 'rgba(255,255,255,0.1)',
                        boxShadow:  n <= pwStrength.bars ? `0 0 6px ${pwStrength.color}88` : 'none',
                      }} />
                    ))}
                  </div>
                  <span className={s.pwLabel} style={{ color: pwStrength.color }}>{pwStrength.label}</span>
                </div>
              )}
            </>
          )}

          {step === 3 && (
            <>
              <p className={styles.sub} style={{ marginBottom: 8 }}>유형과 프로필을 설정하세요</p>
              <div className={s.typeToggle}>
                <button type="button"
                  className={`${s.typeBtn} ${userType === 'b2c' ? s.typeBtnActive : ''}`}
                  onClick={() => setUserType('b2c')}>
                  <span className={s.typeIcon}>👤</span>
                  <span className={s.typeLabel}>일반 소비자</span>
                  <span className={s.typeDesc}>제품 구매·비교</span>
                </button>
                <button type="button"
                  className={`${s.typeBtn} ${userType === 'b2b' ? s.typeBtnActive : ''}`}
                  onClick={() => setUserType('b2b')}>
                  <span className={s.typeIcon}>🏢</span>
                  <span className={s.typeLabel}>사업자</span>
                  <span className={s.typeDesc}>시장 트렌드 분석</span>
                </button>
              </div>

              {userType === 'b2c' && (
                <div className={styles.field}>
                  <input id="nickname" type="text" className={styles.input} placeholder=" "
                    value={nickname} onChange={e => setNickname(e.target.value)} />
                  <label htmlFor="nickname" className={styles.floatLabel}>닉네임</label>
                </div>
              )}
              {userType === 'b2b' && (
                <>
                  <div className={s.b2bNotice}>
                    🔐 사업자 계정은 <strong>관리자 승인 후</strong> 이용 가능합니다.<br />
                    가입 후 1~2일 내 검토 결과를 이메일로 안내해드려요.
                  </div>
                  <div className={styles.field}>
                    <input id="company" type="text" className={styles.input} placeholder=" "
                      value={companyName} onChange={e => setCompanyName(e.target.value)} />
                    <label htmlFor="company" className={styles.floatLabel}>회사명</label>
                  </div>
                  <div className={styles.field}>
                    <input id="bizType" type="text" className={styles.input} placeholder=" "
                      value={businessType} onChange={e => setBusinessType(e.target.value)} />
                    <label htmlFor="bizType" className={styles.floatLabel}>업종 (예: 유통, 제조)</label>
                  </div>
                  <div className={styles.field}>
                    <input id="phone" type="text" className={styles.input} placeholder=" "
                      value={contactPhone} onChange={e => setContactPhone(e.target.value)} />
                    <label htmlFor="phone" className={styles.floatLabel}>담당자 연락처 (선택)</label>
                  </div>
                </>
              )}
            </>
          )}

          {error && <p className={styles.errorMsg}>{error}</p>}
        </div>

        <div className={s.btnRow}>
          <button className={s.prevBtn} onClick={prev} disabled={step === 0}>
            ← 이전
          </button>
          <button className={styles.submitBtn} onClick={next}
            disabled={!canNext || loading}
            style={{ flex: 1, margin: 0 }}>
            {loading
              ? <span className={styles.spinner} />
              : step === 0 ? '인증코드 발송 →'
              : step === 1 ? '인증 확인 →'
              : step === 3 ? '가입 완료 🎉'
              : '다음 →'}
          </button>
        </div>

        <p className={styles.signupRow}>
          이미 계정이 있으신가요?&nbsp;
          <Link to="/login" className={styles.signupLink}>로그인</Link>
        </p>
      </div>
    </div>
  )
}
