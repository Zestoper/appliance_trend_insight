import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import s from '../styles/Admin.module.css'
import { API_BASE } from '../config'

const API = API_BASE

function formatDate(str) {
  if (!str) return '—'
  const d = new Date(str)
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
}

const STATUS_META = {
  pending:  { label: '대기 중', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', icon: '⏳' },
  active:   { label: '승인완료', color: '#34d399', bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.3)', icon: '✅' },
  rejected: { label: '거절됨', color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', icon: '❌' },
}

const TABS = [
  { key: 'all', label: '전체' },
  { key: 'pending', label: '대기 중' },
  { key: 'active', label: '승인완료' },
  { key: 'rejected', label: '거절됨' },
]

export default function Admin() {
  const { user, token } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState('all')
  const [users, setUsers] = useState([])
  const [counts, setCounts] = useState({ pending: 0, active: 0, rejected: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [busy, setBusy] = useState({})

  const isAdmin = user?.role === 'admin'

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2800)
  }, [])

  const fetchUsers = useCallback(async (statusFilter) => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/b2b-users?status=${statusFilter}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const data = await res.json()
      setUsers(data.users || [])
      if (data.counts) setCounts(data.counts)
    } catch {
      showToast('목록을 불러오지 못했습니다', 'error')
    } finally {
      setLoading(false)
    }
  }, [token, showToast])

  useEffect(() => {
    if (isAdmin) fetchUsers(tab)
  }, [isAdmin, tab, fetchUsers])

  async function handleAction(userId, action) {
    setBusy(prev => ({ ...prev, [userId]: true }))
    try {
      const res = await fetch(`${API}/api/admin/users/${userId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error()
      const labels = { approve: '✅ 승인 완료', reject: '❌ 거절 완료' }
      showToast(labels[action] || '처리 완료')
      fetchUsers(tab)
    } catch {
      showToast('처리 중 오류가 발생했습니다', 'error')
      setBusy(prev => ({ ...prev, [userId]: false }))
    }
  }

  if (!user) {
    return (
      <div className={s.denied}>
        <div className={s.deniedIcon}>🔒</div>
        <h1 className={s.deniedTitle}>로그인이 필요합니다</h1>
        <p className={s.deniedSub}>관리자 계정으로 로그인해주세요</p>
        <button className={s.deniedBtn} onClick={() => navigate('/login')}>로그인 →</button>
      </div>
    )
  }
  if (!isAdmin) {
    return (
      <div className={s.denied}>
        <div className={s.deniedIcon}>🚫</div>
        <h1 className={s.deniedTitle}>접근 권한이 없습니다</h1>
        <p className={s.deniedSub}>관리자 계정만 접근할 수 있습니다</p>
        <button className={s.deniedBtn} onClick={() => navigate('/')}>홈으로 →</button>
      </div>
    )
  }

  const filtered = tab === 'all' ? users : users.filter(u => u.status === tab)

  return (
    <div className={s.page}>

      {/* 헤더 */}
      <div className={s.header}>
        <div className={s.titleGroup}>
          <span className={s.badge}>🛡️ Admin</span>
          <h1 className={s.title}>B2B 사업자 관리</h1>
          <p className={s.sub}>사업자 계정 승인·거절·재활성화를 관리하세요</p>
        </div>
        <button className={s.homeBtn} onClick={() => navigate('/')}>← 홈으로</button>
      </div>

      {/* 통계 카드 */}
      <div className={s.statsRow}>
        {[
          { label: '전체',    value: counts.total,    icon: '📋', color: '#818cf8' },
          { label: '대기 중', value: counts.pending,  icon: '⏳', color: '#f59e0b' },
          { label: '승인완료',value: counts.active,   icon: '✅', color: '#34d399' },
          { label: '거절됨',  value: counts.rejected, icon: '❌', color: '#f87171' },
        ].map(stat => (
          <div key={stat.label} className={s.statCard}>
            <span className={s.statIcon}>{stat.icon}</span>
            <span className={s.statValue} style={{ color: stat.color }}>{stat.value}</span>
            <span className={s.statLabel}>{stat.label}</span>
          </div>
        ))}
      </div>

      {/* 탭 */}
      <div className={s.tabs}>
        {TABS.map(t => (
          <button
            key={t.key}
            className={`${s.tabBtn} ${tab === t.key ? s.tabBtnActive : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
            {t.key === 'pending' && counts.pending > 0 && (
              <span className={s.tabBadge}>{counts.pending}</span>
            )}
          </button>
        ))}
      </div>

      {/* 로딩 */}
      {loading && (
        <div className={s.loading}>
          <div className={s.spinner} />
          <span>불러오는 중...</span>
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && filtered.length === 0 && (
        <div className={s.empty}>
          <div className={s.emptyIcon}>{tab === 'pending' ? '🎉' : '📭'}</div>
          <p className={s.emptyText}>
            {tab === 'pending' ? '대기 중인 요청이 없어요' : '해당하는 사업자가 없어요'}
          </p>
          <p className={s.emptySub}>
            {tab === 'pending' ? '모든 가입 신청이 처리됐습니다' : '다른 탭을 확인해보세요'}
          </p>
        </div>
      )}

      {/* 유저 카드 목록 */}
      {!loading && filtered.length > 0 && (
        <div className={s.list}>
          {filtered.map(u => {
            const meta = STATUS_META[u.status] || STATUS_META.pending
            return (
              <div key={u.user_id} className={s.card}>
                <div className={s.cardAvatar}>🏢</div>

                <div className={s.cardBody}>
                  <div className={s.cardTop}>
                    <span className={s.companyName}>{u.company_name || '(미입력)'}</span>
                    {u.business_type && (
                      <span className={s.businessType}>{u.business_type}</span>
                    )}
                    <span
                      className={s.statusBadge}
                      style={{ color: meta.color, background: meta.bg, border: `1px solid ${meta.border}` }}
                    >
                      {meta.icon} {meta.label}
                    </span>
                  </div>
                  <div className={s.cardMeta}>
                    <span className={s.metaItem}>
                      <span className={s.metaIcon}>✉️</span>{u.email}
                    </span>
                    {u.contact_phone && (
                      <span className={s.metaItem}>
                        <span className={s.metaIcon}>📞</span>{u.contact_phone}
                      </span>
                    )}
                  </div>
                </div>

                <span className={s.cardDate}>{formatDate(u.created_at)}</span>

                <div className={s.actions}>
                  {u.status === 'pending' && (
                    <>
                      <button
                        className={s.approveBtn}
                        disabled={!!busy[u.user_id]}
                        onClick={() => handleAction(u.user_id, 'approve')}
                      >
                        {busy[u.user_id] ? '처리중…' : '승인'}
                      </button>
                      <button
                        className={s.rejectBtn}
                        disabled={!!busy[u.user_id]}
                        onClick={() => handleAction(u.user_id, 'reject')}
                      >
                        거절
                      </button>
                    </>
                  )}
                  {u.status === 'active' && (
                    <button
                      className={s.rejectBtn}
                      disabled={!!busy[u.user_id]}
                      onClick={() => handleAction(u.user_id, 'reject')}
                    >
                      {busy[u.user_id] ? '처리중…' : '승인 취소'}
                    </button>
                  )}
                  {u.status === 'rejected' && (
                    <button
                      className={s.approveBtn}
                      disabled={!!busy[u.user_id]}
                      onClick={() => handleAction(u.user_id, 'approve')}
                    >
                      {busy[u.user_id] ? '처리중…' : '재승인'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 토스트 */}
      {toast && (
        <div className={`${s.toast} ${toast.type === 'error' ? s.toastError : s.toastSuccess}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
