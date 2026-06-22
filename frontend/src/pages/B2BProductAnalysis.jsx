import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import s from '../styles/B2BProductAnalysis.module.css'
import { API_BASE } from '../config'

const SIGNAL_STYLE = {
  buy:     { label: '구매 추천', color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.3)'  },
  wait:    { label: '관망 권장', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)' },
  neutral: { label: '적정가',   color: '#818cf8', bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)' },
}

function fmtP(p) {
  if (!p && p !== 0) return '-'
  if (p >= 10000) return `${Math.round(p / 10000).toLocaleString()}만원`
  return `${p.toLocaleString()}원`
}

// ── 가격 히스토리 차트 ─────────────────────────────────────────────
function PriceChart({ history }) {
  if (!history || history.length < 2) return (
    <div className={s.noData}>히스토리 데이터가 쌓이면 표시됩니다</div>
  )
  const W = 500, H = 90, pX = 8, pY = 10
  const avgs = history.map(h => h.avg_price)
  const mins = history.map(h => h.min_price)
  const all  = [...avgs, ...mins]
  const minV = Math.min(...all), maxV = Math.max(...all, minV + 1)
  const toX  = i => pX + (i / (history.length - 1)) * (W - pX * 2)
  const toY  = v => pY + (H - pY * 2) * (1 - (v - minV) / (maxV - minV))
  const avgPts = history.map((h, i) => [toX(i), toY(h.avg_price)])
  const minPts = history.map((h, i) => [toX(i), toY(h.min_price)])
  const avgLine = avgPts.map(p => p.join(',')).join(' ')
  const minLine = minPts.map(p => p.join(',')).join(' ')
  const band = [...avgPts, ...[...minPts].reverse()].map(p => p.join(',')).join(' ')
  const labels = [0, Math.floor(history.length / 2), history.length - 1]
  return (
    <div>
      <div className={s.chartLegend}>
        <span className={s.dot} style={{ background: '#818cf8' }} /> 평균가
        <span className={s.dot} style={{ background: '#22c55e', marginLeft: 10 }} /> 최저가
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 80 }}>
        <polygon points={band} fill="rgba(99,102,241,0.08)" />
        <polyline points={minLine} fill="none" stroke="#22c55e" strokeWidth="1.5"
          strokeDasharray="4,3" vectorEffect="non-scaling-stroke" />
        <polyline points={avgLine} fill="none" stroke="#818cf8" strokeWidth="2"
          vectorEffect="non-scaling-stroke" />
        <circle cx={avgPts.at(-1)[0]} cy={avgPts.at(-1)[1]} r="4" fill="#6366f1"
          vectorEffect="non-scaling-stroke" />
      </svg>
      <div className={s.xAxis}>
        {labels.map(i => <span key={i}>{history[i]?.date?.slice(5) ?? ''}</span>)}
      </div>
    </div>
  )
}

// ── 검색 트렌드 차트 ──────────────────────────────────────────────
function TrendChart({ data }) {
  if (!data || data.length === 0) return <div className={s.noData}>트렌드 데이터 없음</div>
  const W = 500, H = 100, pX = 8, pY = 10
  const vals = data.map(d => d.ratio)
  const minV = 0, maxV = Math.max(...vals, 1)
  const toX  = i => pX + (i / (data.length - 1)) * (W - pX * 2)
  const toY  = v => pY + (H - pY * 2) * (1 - (v - minV) / (maxV - minV))
  const pts   = data.map((d, i) => [toX(i), toY(d.ratio)])
  const line  = pts.map(p => p.join(',')).join(' ')
  const area  = [`${pts[0][0]},${H}`, ...pts.map(p => p.join(',')), `${pts.at(-1)[0]},${H}`].join(' ')
  const labels = [0, Math.floor(data.length / 2), data.length - 1]
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 90 }}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polygon points={area} fill="url(#trendGrad)" />
        <polyline points={line} fill="none" stroke="#818cf8" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <circle cx={pts.at(-1)[0]} cy={pts.at(-1)[1]} r="4" fill="#6366f1"
          vectorEffect="non-scaling-stroke" />
      </svg>
      <div className={s.xAxis}>
        {labels.map(i => <span key={i}>{data[i]?.period?.slice(5) ?? ''}</span>)}
      </div>
    </div>
  )
}

// ── 경쟁 제품 바 차트 ────────────────────────────────────────────
function CompetitorChart({ competitors }) {
  if (!competitors || competitors.length === 0) return (
    <div className={s.noData}>카테고리 감지 후 표시됩니다</div>
  )
  const maxP = Math.max(...competitors.map(c => c.price), 1)
  const COLORS = ['#6366f1', '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
  return (
    <div className={s.competitorList}>
      {competitors.map((c, i) => (
        <div key={i} className={s.competitorRow}>
          <div className={s.competitorInfo}>
            <span className={s.competitorBrand}>{c.brand || '기타'}</span>
            <span className={s.competitorTitle}>{c.title}</span>
          </div>
          <div className={s.competitorBarWrap}>
            <div className={s.competitorBarTrack}>
              <div className={s.competitorBarFill}
                style={{ width: `${(c.price / maxP) * 100}%`, background: COLORS[i % COLORS.length] }} />
            </div>
            <span className={s.competitorPrice}>{fmtP(c.price)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── 메인 페이지 ────────────────────────────────────────────────────
export default function B2BProductAnalysis() {
  const navigate = useNavigate()
  const { user }  = useAuth()
  const inputRef  = useRef(null)
  const [query,   setQuery]   = useState('')
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'

  async function search(q) {
    const trimmed = (q || query).trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const res  = await fetch(`${API_BASE}/api/b2b/product-analysis?q=${encodeURIComponent(trimmed)}`)
      const json = await res.json()
      setData(json)
    } catch {
      setError('서버에 연결할 수 없습니다')
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.nativeEvent.isComposing) return
    if (e.key === 'Enter') search()
  }

  if (!isB2BActive) {
    return (
      <div className={s.page}>
        <Navbar />
        <div className={s.accessDenied}>
          <p className={s.accessTitle}>{!user ? '로그인이 필요합니다' : 'B2B 계정 전용입니다'}</p>
          <button className={s.accessBtn} onClick={() => navigate(!user ? '/login' : '/b2b')}>
            {!user ? '로그인' : 'B2B 홈으로'}
          </button>
        </div>
      </div>
    )
  }

  const p = data?.price
  const sig = p ? (SIGNAL_STYLE[p.signal_type] ?? SIGNAL_STYLE.neutral) : null

  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.layout}>
        <div className={s.main}>

          {/* ── 헤더 + 검색 ── */}
          <div className={s.header}>
            <span className={s.badge}>제품 분석</span>
            <h1 className={s.title}>B2B 제품 상세 분석</h1>
            <p className={s.subtitle}>제품명 또는 모델번호를 입력하면 가격·트렌드·리뷰·경쟁사를 한눈에 분석합니다</p>
          </div>

          <div className={s.searchWrap}>
            <input
              ref={inputRef}
              className={s.searchInput}
              placeholder="예: 삼성 비스포크 냉장고 4도어 905L 또는 RM70F90R2ZD"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button className={s.searchBtn} onClick={() => search()}>분석하기</button>
          </div>

          {/* 예시 태그 */}
          {!data && !loading && (
            <div className={s.exampleWrap}>
              {['삼성 비스포크 냉장고', 'LG 오브제 세탁기', '다이슨 에어랩', '삼성 갤럭시 북'].map(ex => (
                <button key={ex} className={s.exampleTag}
                  onClick={() => { setQuery(ex); search(ex) }}>
                  {ex}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className={s.loadingWrap}>
              <div className={s.spinner} />
              <p>"{query}" 분석 중... (가격·트렌드·리뷰·경쟁사 동시 수집)</p>
            </div>
          )}
          {error && <div className={s.error}>{error}</div>}

          {/* ── 결과 ── */}
          {data && !loading && (
            <>
              <div className={s.resultHeader}>
                <div>
                  <span className={s.resultQuery}>"{data.query}"</span>
                  {data.model_number && <span className={s.modelBadge}>{data.model_number}</span>}
                  {data.category && <span className={s.catBadge}>{data.category}</span>}
                </div>
              </div>

              <div className={s.grid}>

                {/* 1. 가격 인텔리전스 */}
                <div className={`${s.card} ${s.cardPrice}`}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>가격 인텔리전스</h2>
                      <p className={s.cardSub}>멀티몰 최저가 비교 · 히스토리</p>
                    </div>
                    {sig && (
                      <span className={s.signalBadge}
                        style={{ color: sig.color, background: sig.bg, border: `1px solid ${sig.border}` }}>
                        {sig.label}
                      </span>
                    )}
                  </div>

                  {!p ? (
                    <div className={s.noData}>가격 데이터를 불러올 수 없습니다</div>
                  ) : (
                    <>
                      <div className={s.priceStats}>
                        <div className={s.priceStat}>
                          <span className={s.psLabel}>현재 최저가</span>
                          <span className={s.psValue} style={{ color: '#22c55e' }}>{fmtP(p.min_price)}</span>
                          <span className={s.psNote}>{p.cheapest_mall}</span>
                        </div>
                        <div className={s.priceStat}>
                          <span className={s.psLabel}>누적 평균가</span>
                          <span className={s.psValue}>{fmtP(p.hist_avg)}</span>
                          <span className={s.psNote}>전체 기간 평균</span>
                        </div>
                        <div className={s.priceStat}>
                          <span className={s.psLabel}>역대 최저가</span>
                          <span className={s.psValue}>{fmtP(p.hist_min)}</span>
                          <span className={s.psNote}>역대 최저</span>
                        </div>
                      </div>

                      {p.reason && (
                        <div className={s.reasonBox} style={{ borderColor: sig?.border }}>
                          <span style={{ marginRight: 6 }}>
                            {p.signal_type === 'buy' ? '✅' : p.signal_type === 'wait' ? '⏳' : '📊'}
                          </span>
                          {p.reason}
                        </div>
                      )}

                      <div className={s.mallList}>
                        <p className={s.mallListLabel}>쇼핑몰별 현재가</p>
                        {p.malls.map((m, i) => (
                          <div key={i} className={`${s.mallRow} ${i === 0 ? s.mallRowBest : ''}`}>
                            <span className={s.mallName}>{m.mall}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              {i === 0 && <span className={s.bestTag}>최저</span>}
                              <span className={s.mallPrice}>{fmtP(m.price)}</span>
                              <a href={m.link} target="_blank" rel="noopener noreferrer"
                                className={s.mallLink}>보기 →</a>
                            </div>
                          </div>
                        ))}
                      </div>

                      {p.price_history.length >= 2 && (
                        <div style={{ marginTop: 16 }}>
                          <p className={s.mallListLabel}>가격 추이</p>
                          <PriceChart history={p.price_history} />
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* 2. 검색 트렌드 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>검색 트렌드</h2>
                      <p className={s.cardSub}>최근 90일 주별 관심도 (네이버 DataLab)</p>
                    </div>
                  </div>
                  <TrendChart data={data.trend} />
                  {data.trend?.length > 0 && (
                    <div className={s.trendStats}>
                      <div className={s.trendStat}>
                        <span>최고 관심도</span>
                        <strong>{Math.max(...data.trend.map(d => d.ratio)).toFixed(1)}</strong>
                      </div>
                      <div className={s.trendStat}>
                        <span>최근 관심도</span>
                        <strong>{data.trend.at(-1)?.ratio.toFixed(1)}</strong>
                      </div>
                      <div className={s.trendStat}>
                        <span>평균 관심도</span>
                        <strong>{(data.trend.reduce((a, d) => a + d.ratio, 0) / data.trend.length).toFixed(1)}</strong>
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. 리뷰 감성 분석 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>리뷰 감성 분석</h2>
                      <p className={s.cardSub}>블로그·카페 사용후기 기반</p>
                    </div>
                    <span className={s.sentScore}
                      style={{ color: data.sentiment.score >= 60 ? '#22c55e' : data.sentiment.score >= 40 ? '#f59e0b' : '#f87171' }}>
                      {data.sentiment.score}점
                    </span>
                  </div>

                  <div className={s.sentBar}>
                    <div className={s.sentBarFill}
                      style={{ width: `${data.sentiment.score}%`,
                        background: data.sentiment.score >= 60
                          ? 'linear-gradient(90deg,#22c55e,#16a34a)'
                          : data.sentiment.score >= 40
                          ? 'linear-gradient(90deg,#f59e0b,#d97706)'
                          : 'linear-gradient(90deg,#f87171,#dc2626)' }} />
                  </div>
                  <div className={s.sentCount}>
                    <span style={{ color: '#22c55e' }}>긍정 {data.sentiment.pos}</span>
                    <span style={{ color: '#f87171' }}>부정 {data.sentiment.neg}</span>
                  </div>

                  {data.sentiment.keywords.length > 0 && (
                    <div className={s.kwCloud}>
                      {data.sentiment.keywords.map((kw, i) => (
                        <span key={i} className={s.kwTag}
                          style={{ fontSize: Math.max(10, Math.min(16, 10 + kw.count)) }}>
                          {kw.word}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className={s.reviewList}>
                    {data.reviews.slice(0, 4).map((r, i) => (
                      <a key={i} href={r.link} target="_blank" rel="noopener noreferrer"
                        className={s.reviewItem}>
                        <div className={s.reviewMeta}>
                          <span className={s.reviewSource}>{r.source}</span>
                          <span className={s.reviewTitle}>{r.title.slice(0, 30)}</span>
                        </div>
                        <p className={s.reviewText}>{r.review.slice(0, 80)}…</p>
                      </a>
                    ))}
                  </div>
                </div>

                {/* 4. 경쟁 제품 비교 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>경쟁 제품 비교</h2>
                      <p className={s.cardSub}>
                        {data.category ? `${data.category} 카테고리 브랜드별 최저가` : '카테고리 미감지 — 제품명에 카테고리 포함 필요'}
                      </p>
                    </div>
                  </div>
                  <CompetitorChart competitors={data.competitors} />
                </div>

              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
