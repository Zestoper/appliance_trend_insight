import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/common/Navbar'
import s from '../styles/MyPage.module.css'
import { API_BASE } from '../config'

const API = API_BASE

function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function MyPage() {
  const { user, token, isLoggedIn, logout } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [alertDeleting, setAlertDeleting] = useState({})

  useEffect(() => {
    if (!isLoggedIn) return
    setFetchError(null)
    fetch(`${API}/api/user/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json() })
      .then(data => { setProfile(data); setLoading(false) })
      .catch(() => { setFetchError('프로필을 불러올 수 없습니다'); setLoading(false) })

    fetch(`${API}/api/user/alerts`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => setAlerts(data.alerts || []))
      .catch(() => {})
  }, [isLoggedIn, token])

  async function deleteAlert(alertId) {
    setAlertDeleting(prev => ({ ...prev, [alertId]: true }))
    try {
      await fetch(`${API}/api/user/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      setAlerts(prev => prev.filter(a => a.alert_id !== alertId))
    } finally {
      setAlertDeleting(prev => ({ ...prev, [alertId]: false }))
    }
  }

  if (!isLoggedIn) {
    return (
      <div className={s.denied}>
        <div className={s.deniedIcon}>🔒</div>
        <h1 className={s.deniedTitle}>로그인이 필요해요</h1>
        <p className={s.deniedSub}>마이페이지는 로그인 후 이용할 수 있어요</p>
        <button className={s.deniedBtn} onClick={() => navigate('/login')}>로그인하기 →</button>
      </div>
    )
  }

  const displayName = user?.nickname || user?.company_name || user?.email || '—'
  const isB2B = user?.user_type === 'b2b'
  const isAdmin = user?.role === 'admin'

  return (
    <div>
      <Navbar />
      <div className={s.page}>
        <div className={s.inner}>

          <div className={s.header}>
            <h1 className={s.title}>마이페이지</h1>
            <p className={s.sub}>계정 정보를 확인하세요</p>
          </div>

          {/* 프로필 카드 */}
          <div className={s.profileCard}>
            <div className={s.avatar}>{isB2B ? '🏢' : '👤'}</div>
            <div className={s.profileInfo}>
              <p className={s.profileName}>
                {displayName}
                {isAdmin && <span className={s.adminBadge}>관리자</span>}
              </p>
              <p className={s.profileEmail}>{user?.email}</p>
              <span className={isB2B ? `${s.typeBadge} ${s.typeBadgeB2B}` : `${s.typeBadge} ${s.typeBadgeB2C}`}>
                {isB2B ? '🏢 사업자' : '👤 개인'}
              </span>
            </div>
          </div>

          {/* 계정 정보 */}
          {loading ? (
            <div className={s.loading}>
              <div className={s.spinner} />
              <span>정보 불러오는 중...</span>
            </div>
          ) : fetchError ? (
            <div className={s.fetchError}>{fetchError}</div>
          ) : (
            <div className={s.section}>
              <p className={s.sectionTitle}>계정 정보</p>

              <div className={s.infoRow}>
                <span className={s.infoKey}>이메일</span>
                <span className={s.infoVal}>{profile?.email || user?.email}</span>
              </div>

              <div className={s.infoRow}>
                <span className={s.infoKey}>계정 유형</span>
                <span className={s.infoVal}>{isB2B ? '사업자 (B2B)' : '개인 (B2C)'}</span>
              </div>

              {isB2B ? (
                <>
                  <div className={s.infoRow}>
                    <span className={s.infoKey}>회사명</span>
                    <span className={s.infoVal}>{profile?.company_name || '—'}</span>
                  </div>
                  <div className={s.infoRow}>
                    <span className={s.infoKey}>업종</span>
                    <span className={s.infoVal}>{profile?.business_type || '—'}</span>
                  </div>
                  <div className={s.infoRow}>
                    <span className={s.infoKey}>연락처</span>
                    <span className={s.infoVal}>{profile?.contact_phone || '—'}</span>
                  </div>
                </>
              ) : (
                <div className={s.infoRow}>
                  <span className={s.infoKey}>닉네임</span>
                  <span className={s.infoVal}>{profile?.nickname || '—'}</span>
                </div>
              )}

              <div className={s.infoRow}>
                <span className={s.infoKey}>가입일</span>
                <span className={s.infoVal}>{fmtDate(profile?.created_at)}</span>
              </div>
            </div>
          )}

          {/* 가격 알림 목록 */}
          <div className={s.section}>
            <p className={s.sectionTitle}>가격 알림</p>
            {alerts.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                등록된 가격 알림이 없어요. 제품 리포트에서 설정할 수 있어요.
              </p>
            ) : (
              <div className={s.alertList}>
                {alerts.map(a => (
                  <div key={a.alert_id} className={s.alertRow}>
                    <div className={s.alertInfo}>
                      <p className={s.alertName}>{a.product_name}</p>
                      <p className={s.alertMeta}>
                        목표 <strong>{Number(a.target_price).toLocaleString()}원</strong>
                        &nbsp;·&nbsp;현재 {Number(a.current_price).toLocaleString()}원
                      </p>
                    </div>
                    <button
                      className={s.alertDeleteBtn}
                      disabled={!!alertDeleting[a.alert_id]}
                      onClick={() => deleteAlert(a.alert_id)}
                    >
                      {alertDeleting[a.alert_id] ? '…' : '✕'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 버튼 */}
          <div className={s.btnRow}>
            <button className={s.homeBtn} onClick={() => navigate('/')}>← 홈으로</button>
            <button className={s.logoutBtn} onClick={() => { logout(); navigate('/') }}>로그아웃</button>
          </div>

        </div>
      </div>
    </div>
  )
}
