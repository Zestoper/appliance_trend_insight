import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import s from '../styles/B2BPriceMonitor.module.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SIGNAL_CFG = {
  buy:      { label: '매입 적기',  color: '#10b981', bg: '#10b98118', icon: '▼' },
  watch:    { label: '하락 추세',  color: '#3b82f6', bg: '#3b82f618', icon: '↓' },
  neutral:  { label: '보합',      color: '#6b7280', bg: '#6b728018', icon: '─' },
  caution:  { label: '상승 추세', color: '#f59e0b', bg: '#f59e0b18', icon: '↑' },
  wait:     { label: '가격 상승', color: '#ef4444', bg: '#ef444418', icon: '▲' },
  realtime: { label: '실시간',    color: '#6366f1', bg: '#6366f118', icon: '◎' },
}

function MiniSparkline({ history }) {
  if (!history || history.length < 2) return null
  const prices = history.map(h => h.avg_price)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const W = 80, H = 32
  const pts = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * W
    const y = H - ((p - min) / range) * (H - 4) - 2
    return `${x},${y}`
  }).join(' ')
  const isDown = prices[prices.length - 1] <= prices[0]
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className={s.sparkline}>
      <polyline points={pts} fill="none" stroke={isDown ? '#10b981' : '#ef4444'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function B2BPriceMonitor() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    if (user && user.user_type !== 'b2b' && user.user_type !== 'admin') {
      navigate('/b2b')
    }
  }, [user, navigate])

  useEffect(() => {
    if (!token) return
    const load = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API}/api/b2b/price-monitor`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error(res.status)
        const json = await res.json()
        setData(json)
      } catch {
        setError('가격 데이터를 불러올 수 없습니다.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })

  const filtered = (data?.categories ?? []).filter(c => {
    if (filter === 'buy')  return c.signal_type === 'buy'
    if (filter === 'drop') return ['buy', 'watch'].includes(c.signal_type)
    if (filter === 'rise') return ['wait', 'caution'].includes(c.signal_type)
    return true
  })

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>

        {/* 리포트 헤더 */}
        <div className={s.reportHeader}>
          <div className={s.reportHeaderTop}>
            <div>
              <p className={s.reportLabel}>B2B PRICE MONITOR</p>
              <h1 className={s.reportTitle}>카테고리 가격 변동 모니터</h1>
              <p className={s.reportMeta}>{today} · 네이버 쇼핑 실시간 가격 기준</p>
            </div>
            {data && (
              <div className={s.summaryBadges}>
                <div className={s.summaryBadge} style={{ borderColor: '#10b981', color: '#10b981' }}>
                  <span className={s.summaryBadgeNum}>{data.summary.drop_count}</span>
                  <span className={s.summaryBadgeLabel}>하락 카테고리</span>
                </div>
                <div className={s.summaryBadge} style={{ borderColor: '#ef4444', color: '#ef4444' }}>
                  <span className={s.summaryBadgeNum}>{data.summary.rise_count}</span>
                  <span className={s.summaryBadgeLabel}>상승 카테고리</span>
                </div>
              </div>
            )}
          </div>

          {data?.summary?.buy_signals?.length > 0 && (
            <div className={s.buyBanner}>
              <span className={s.buyBannerIcon}>★</span>
              <span className={s.buyBannerText}>
                <strong>매입 적기 카테고리</strong>: {data.summary.buy_signals.join(' · ')}
              </span>
              <span className={s.buyBannerSub}>7일 대비 5% 이상 하락</span>
            </div>
          )}
        </div>

        {/* 필터 탭 */}
        <div className={s.filterRow}>
          {[
            { key: 'all',  label: '전체' },
            { key: 'buy',  label: '매입 적기' },
            { key: 'drop', label: '하락 중' },
            { key: 'rise', label: '상승 중' },
          ].map(f => (
            <button key={f.key}
              className={`${s.filterBtn} ${filter === f.key ? s.filterBtnActive : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading && (
          <div className={s.loadingWrap}>
            <div className={s.spinner} />
            <p>가격 변동 데이터 로딩 중...</p>
          </div>
        )}

        {error && (
          <div className={s.errorCard}>
            <p className={s.errorIcon}>⚠</p>
            <p className={s.errorText}>{error}</p>
            <button className={s.errorBtn} onClick={() => navigate('/b2b/price?category=에어컨')}>
              가격 분석 페이지로 이동
            </button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className={s.emptyCard}>
            <p>해당 조건의 카테고리가 없습니다.</p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className={s.categoryGrid}>
            {filtered.map(cat => {
              const cfg = SIGNAL_CFG[cat.signal_type] ?? SIGNAL_CFG.neutral
              const fmt = (n) => n ? `${Math.round(n / 10000)}만원` : '-'
              return (
                <div key={cat.category} className={s.categoryCard}
                  onClick={() => navigate(`/b2b/price?category=${cat.category}`)}>

                  <div className={s.cardHead}>
                    <span className={s.cardCategory}>{cat.category}</span>
                    <span className={s.signalBadge} style={{ background: cfg.bg, color: cfg.color }}>
                      {cfg.icon} {cfg.label}
                    </span>
                  </div>

                  <div className={s.cardPriceRow}>
                    <div>
                      <p className={s.cardAvgPrice}>{fmt(cat.avg_price)}</p>
                      <p className={s.cardMinPrice}>브랜드 최저 {fmt(cat.min_price)}</p>
                    </div>
                    <MiniSparkline history={cat.history} />
                  </div>

                  <div className={s.changeRow}>
                    <div className={s.changeItem}>
                      <span className={s.changeLabel}>전일 대비</span>
                      {cat.day_change_pct != null ? (
                        <span className={s.changeVal}
                          style={{ color: cat.day_change_pct <= 0 ? '#10b981' : '#ef4444' }}>
                          {cat.day_change_pct > 0 ? '+' : ''}{cat.day_change_pct}%
                        </span>
                      ) : (
                        <span className={s.changeValNA}>{cat.realtime ? '수집 전' : '데이터 부족'}</span>
                      )}
                    </div>
                    <div className={s.changeDivider} />
                    <div className={s.changeItem}>
                      <span className={s.changeLabel}>7일 대비</span>
                      {cat.week_change_pct != null ? (
                        <span className={s.changeVal}
                          style={{ color: cat.week_change_pct <= 0 ? '#10b981' : '#ef4444' }}>
                          {cat.week_change_pct > 0 ? '+' : ''}{cat.week_change_pct}%
                        </span>
                      ) : (
                        <span className={s.changeValNA}>{cat.realtime ? '수집 전' : '데이터 부족'}</span>
                      )}
                    </div>
                  </div>

                  {cat.brand_changes?.length > 0 && (
                    <div className={s.brandChanges}>
                      {cat.brand_changes.map(b => (
                        <div key={b.brand} className={s.brandChangeRow}>
                          <span className={s.brandName}>{b.brand}</span>
                          <span className={s.brandChangeBar}>
                            <span className={s.brandChangeBarFill}
                              style={{
                                width: `${Math.min(Math.abs(b.change_pct) * 8, 100)}%`,
                                background: b.change_pct <= 0 ? '#10b981' : '#ef4444',
                              }} />
                          </span>
                          <span className={s.brandChangePct}
                            style={{ color: b.change_pct <= 0 ? '#10b981' : '#ef4444' }}>
                            {b.change_pct > 0 ? '+' : ''}{b.change_pct}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  <p className={s.cardUpdated}>기준 {cat.last_updated} · 상세보기 →</p>
                </div>
              )
            })}
          </div>
        )}

        <div className={s.pageFooter}>
          <span>데이터 기준: 네이버 쇼핑 API · 일 1회 스냅샷 저장</span>
          <span>{today}</span>
        </div>
      </div>
    </div>
  )
}
