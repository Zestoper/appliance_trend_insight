import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import s from '../styles/B2BAnalysis.module.css'
import { API_BASE } from '../config'

const SIGNAL_STYLE = {
  buy:     { icon: '✅', color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.3)'  },
  wait:    { icon: '⏳', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)' },
  avoid:   { icon: '⛔', color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)' },
  neutral: { icon: '📊', color: '#818cf8', bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)' },
}

const FAIRNESS_STYLE = {
  cheap:     { label: '저렴한 편', icon: '💰', color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.3)'  },
  fair:      { label: '적정 가격', icon: '⚖️', color: '#818cf8', bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)' },
  expensive: { label: '비싼 편',   icon: '📈', color: '#f87171', bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)' },
}

function fmtP(p) {
  if (!p && p !== 0) return '-'
  if (p >= 10000) return `${Math.round(p / 10000).toLocaleString()}만원`
  return `${p.toLocaleString()}원`
}

// ── Y축 눈금 + 라벨 (공용) ────────────────────────────────────────────────
function YAxis({ minV, maxV, pX, pY, H, W, axisLabel, tickFormat }) {
  const fmt = tickFormat || Math.round
  const ticks = [maxV, (minV + maxV) / 2, minV]
  return (
    <>
      <text x={pX} y="9" textAnchor="start" fontSize="9" fill="#9ca3af">{axisLabel}</text>
      {ticks.map((t, i) => {
        const y = pY + (i / (ticks.length - 1)) * (H - pY * 2)
        return (
          <g key={i}>
            <line x1={pX} y1={y} x2={W} y2={y} stroke="currentColor" strokeOpacity="0.08" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <text x={pX - 6} y={y + 3} textAnchor="end" fontSize="9" fill="#9ca3af">{fmt(t)}</text>
          </g>
        )
      })}
    </>
  )
}

// ── 관심도 추세 + 예측 차트 (실제 데이터 · 선형회귀 추세선 · Prophet 예측) ──
function ForecastChart({ history, linearTrend, prophetForecast, axisLabel = '관심도 지수' }) {
  if (!history || history.length < 2) return <div className={s.noData}>예측에 필요한 데이터가 부족합니다</div>
  const forecast = prophetForecast || []
  const n = history.length + forecast.length
  const W = 500, H = 220, pX = 34, pY = 28
  const vals = [
    ...history.map(d => d.ratio),
    ...(linearTrend || []).map(d => d.ratio),
    ...forecast.flatMap(d => [d.ratio, d.lower, d.upper]),
  ]
  const minV = 0, maxV = Math.max(...vals, 1)
  const toX = i => pX + (i / Math.max(n - 1, 1)) * (W - pX - 8)
  const toY = v => pY + (H - pY * 2) * (1 - (v - minV) / (maxV - minV))

  const histPts = history.map((d, i) => [toX(i), toY(d.ratio)])
  const histLine = histPts.map(p => p.join(',')).join(' ')

  const trendPts = (linearTrend || []).map((d, i) => [toX(i), toY(d.ratio)])
  const trendLine = trendPts.map(p => p.join(',')).join(' ')

  const fcStartIdx = history.length - 1
  const fcPts = forecast.map((d, i) => [toX(fcStartIdx + 1 + i), toY(d.ratio)])
  const fcLine = [histPts.at(-1), ...fcPts].map(p => p.join(',')).join(' ')

  const bandTop = forecast.map((d, i) => [toX(fcStartIdx + 1 + i), toY(d.upper)])
  const bandBot = forecast.map((d, i) => [toX(fcStartIdx + 1 + i), toY(d.lower)])
  const band = [histPts.at(-1), ...bandTop, ...[...bandBot].reverse()].map(p => p.join(',')).join(' ')

  const nowX = toX(fcStartIdx)
  const labelIdx = [0, Math.floor(history.length / 2), history.length - 1]
  const xLabelY = H - pY + 14

  return (
    <div>
      <div className={s.chartLegend}>
        <span className={s.dot} style={{ background: '#ef4444' }} /> 실제 데이터
        <span className={s.dot} style={{ background: '#9ca3af', marginLeft: 10 }} /> 선형회귀 추세선
        <span className={s.dot} style={{ background: '#22c55e', marginLeft: 10 }} /> Prophet 예측
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 260 }}>
        <YAxis minV={minV} maxV={maxV} pX={pX} pY={pY} H={H} W={W} axisLabel={axisLabel} />
        {forecast.length > 0 && <polygon points={band} fill="rgba(34,197,94,0.1)" />}
        <line x1={nowX} y1={pY} x2={nowX} y2={H - pY} stroke="#818cf8" strokeWidth="1"
          strokeDasharray="3,3" vectorEffect="non-scaling-stroke" />
        {trendLine && (
          <polyline points={trendLine} fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeDasharray="4,3"
            strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        )}
        <polyline points={histLine} fill="none" stroke="#ef4444" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {forecast.length > 0 && (
          <polyline points={fcLine} fill="none" stroke="#22c55e" strokeWidth="2" strokeDasharray="5,4"
            strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        )}
        <circle cx={histPts.at(-1)[0]} cy={histPts.at(-1)[1]} r="4" fill="#ef4444" vectorEffect="non-scaling-stroke" />
        {labelIdx.map((i, li) => (
          <text key={i} x={toX(i)} y={xLabelY} fontSize="9" fill="currentColor" opacity="0.6"
            textAnchor={li === 0 ? 'start' : li === labelIdx.length - 1 ? 'end' : 'middle'}>
            {history[i]?.period?.slice(5) ?? ''}
          </text>
        ))}
        {forecast.length > 0 && (
          <text x={toX(fcStartIdx + forecast.length)} y={xLabelY} fontSize="9" fill="#22c55e" textAnchor="end">
            {forecast.at(-1)?.period?.slice(5) ?? ''} 예측
          </text>
        )}
      </svg>
    </div>
  )
}

// ── 작은 스파크라인 (AI 수요 예측 카드 옆에 붙는 미니 그래프) ────────────────
function Sparkline({ data }) {
  if (!data || data.length < 2) return null
  const W = 120, H = 44, p = 3
  const vals = data.map(d => d.ratio)
  const minV = Math.min(...vals), maxV = Math.max(...vals, minV + 1)
  const toX = i => p + (i / (data.length - 1)) * (W - p * 2)
  const toY = v => p + (H - p * 2) * (1 - (v - minV) / (maxV - minV))
  const pts = data.map((d, i) => [toX(i), toY(d.ratio)])
  const line = pts.map(pt => pt.join(',')).join(' ')
  const area = [`${pts[0][0]},${H}`, ...pts.map(pt => pt.join(',')), `${pts.at(-1)[0]},${H}`].join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: 120, height: 44, flexShrink: 0 }}>
      <polygon points={area} fill="rgba(34,197,94,0.12)" />
      <polyline points={line} fill="none" stroke="#22c55e" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

// ── 가격 변동 그래프 (실제 이력 축적분만 표시) ────────────────────────────
function PriceHistoryChart({ history }) {
  if (!history || history.length < 2) {
    return <div className={s.noData}>가격 이력이 아직 충분히 쌓이지 않았습니다 — 조회가 누적되면 표시됩니다</div>
  }
  const W = 500, H = 160, pX = 44, pY = 24
  const vals = history.flatMap(h => [h.min_price, h.avg_price])
  const minV = Math.min(...vals), maxV = Math.max(...vals, minV + 1)
  const toX = i => pX + (i / (history.length - 1)) * (W - pX - 8)
  const toY = v => pY + (H - pY * 2) * (1 - (v - minV) / (maxV - minV))
  const avgPts = history.map((h, i) => [toX(i), toY(h.avg_price)])
  const minPts = history.map((h, i) => [toX(i), toY(h.min_price)])
  const avgLine = avgPts.map(p => p.join(',')).join(' ')
  const minLine = minPts.map(p => p.join(',')).join(' ')
  const labels = [0, Math.floor(history.length / 2), history.length - 1]
  const fmtWon = v => v >= 10000 ? `${Math.round(v / 10000)}만` : v
  return (
    <div>
      <div className={s.chartLegend}>
        <span className={s.dot} style={{ background: '#818cf8' }} /> 평균가
        <span className={s.dot} style={{ background: '#22c55e', marginLeft: 10 }} /> 최저가
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 190 }}>
        <YAxis minV={minV} maxV={maxV} pX={pX} pY={pY} H={H} W={W} axisLabel="가격(원)" tickFormat={fmtWon} />
        <polyline points={minLine} fill="none" stroke="#22c55e" strokeWidth="1.5" strokeDasharray="4,3"
          vectorEffect="non-scaling-stroke" />
        <polyline points={avgLine} fill="none" stroke="#818cf8" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <circle cx={avgPts.at(-1)[0]} cy={avgPts.at(-1)[1]} r="4" fill="#6366f1" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className={s.xAxis}>
        {labels.map(i => <span key={i}>{history[i]?.date?.slice(5) ?? ''}</span>)}
      </div>
    </div>
  )
}

export default function B2BAnalysis() {
  const navigate = useNavigate()
  const { user, token } = useAuth()
  const inputRef  = useRef(null)
  const [query,      setQuery]      = useState('')
  const [products,   setProducts]   = useState(null)
  const [selected,   setSelected]   = useState(null)
  const [data,       setData]       = useState(null)
  const [searching,  setSearching]  = useState(false)
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState(null)
  const [sentimentTab, setSentimentTab] = useState('pos')
  const [reviewsExpanded, setReviewsExpanded] = useState(false)
  const [brandFilter, setBrandFilter]   = useState('')
  const [priceMax,    setPriceMax]      = useState('')
  const [energyFilter, setEnergyFilter] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'

  async function searchProducts(q) {
    const trimmed = (q || query).trim()
    if (!trimmed) return
    setSearching(true)
    setError(null)
    setData(null)
    setSelected(null)
    setProducts(null)
    setBrandFilter('')
    setPriceMax('')
    setEnergyFilter('')
    try {
      const res  = await fetch(`${API_BASE}/api/b2b/product-search?q=${encodeURIComponent(trimmed)}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const json = await res.json()
      setProducts(json.items || [])
    } catch {
      setError('서버에 연결할 수 없습니다')
    } finally {
      setSearching(false)
    }
  }

  async function analyzeProduct(product, force = false) {
    setSelected(product)
    setLoading(true)
    setError(null)
    if (!force) setData(null)
    try {
      const res  = await fetch(
        `${API_BASE}/api/b2b/search-analysis?q=${encodeURIComponent(product.title)}&hint=${encodeURIComponent(query)}${force ? '&force=true' : ''}`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
      const json = await res.json()
      setData(json)
    } catch {
      setError('서버에 연결할 수 없습니다')
    } finally {
      setLoading(false)
    }
  }

  async function refreshAnalysis() {
    if (!selected || refreshing) return
    setRefreshing(true)
    try {
      await analyzeProduct(selected, true)
    } finally {
      setRefreshing(false)
    }
  }

  function exportPdf() {
    if (!selected) return
    window.print()
  }

  function backToProducts() {
    setSelected(null)
    setData(null)
  }

  function onKeyDown(e) {
    if (e.nativeEvent.isComposing) return
    if (e.key === 'Enter') searchProducts()
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

  const info      = data?.product_info
  const report    = data?.ai_report
  const sig       = report?.conclusion ? (SIGNAL_STYLE[report.conclusion] ?? SIGNAL_STYLE.neutral) : null
  const priceChg  = data?.price_change
  const fairness  = data?.price_fairness
  const fairSig   = fairness?.type ? FAIRNESS_STYLE[fairness.type] : null
  const demand    = data?.demand_forecast
  const comp      = data?.competitor_comparison
  const sentiment = data?.review_sentiment

  const brandOptions = products ? [...new Set(products.map(p => p.brand).filter(Boolean))].sort() : []
  const energyOptions = products ? [...new Set(products.map(p => p.energy_grade).filter(Boolean))].sort() : []
  const filteredProducts = (products || []).filter(p =>
    (!brandFilter || p.brand === brandFilter) &&
    (!priceMax || p.price <= Number(priceMax) * 10000) &&
    (!energyFilter || p.energy_grade === Number(energyFilter))
  )
  const sentimentReviews = (sentiment?.reviews || []).filter(r => r.sentiment === sentimentTab)

  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.layout}>
        <div className={s.main}>

          {/* ── 헤더 + 검색 ── */}
          <div className={s.header}>
            <span className={s.badge}>B2B 분석</span>
            <h1 className={s.title}>제품 검색 기반 시장 분석</h1>
            <p className={s.subtitle}>제품명을 검색해 목록에서 정확한 상품을 고르면 그 상품 하나에 대한 분석을 보여드립니다</p>
          </div>

          {!selected && (
            <>
              <div className={s.searchWrap}>
                <input
                  ref={inputRef}
                  className={s.searchInput}
                  placeholder="예: 삼성 비스포크 냉장고, LG 오브제 세탁기"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={onKeyDown}
                />
                <button className={s.searchBtn} onClick={() => searchProducts()}>검색</button>
              </div>

              {!products && !searching && (
                <div className={s.exampleWrap}>
                  {['삼성 비스포크 냉장고', 'LG 오브제 세탁기', '다이슨 에어랩', '위닉스 공기청정기'].map(ex => (
                    <button key={ex} className={s.exampleTag} onClick={() => { setQuery(ex); searchProducts(ex) }}>
                      {ex}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {searching && (
            <div className={s.loadingWrap}>
              <div className={s.spinner} />
              <p>"{query}" 관련 상품을 찾는 중...</p>
            </div>
          )}
          {error && <div className={s.error}>{error}</div>}

          {/* ── 상품 선택 목록 ── */}
          {products && !selected && !searching && (
            products.length > 0 ? (
              <>
                <div className={s.filterBar}>
                  <select className={s.filterSelect} value={brandFilter} onChange={e => setBrandFilter(e.target.value)}>
                    <option value="">브랜드 전체</option>
                    {brandOptions.map(b => <option key={b} value={b}>{b}</option>)}
                  </select>
                  <input
                    className={s.filterInput}
                    type="number"
                    placeholder="최대 가격(만원)"
                    value={priceMax}
                    onChange={e => setPriceMax(e.target.value)}
                  />
                  {energyOptions.length > 1 && (
                    <select className={s.filterSelect} value={energyFilter} onChange={e => setEnergyFilter(e.target.value)}>
                      <option value="">에너지효율 전체</option>
                      {energyOptions.map(g => <option key={g} value={g}>{g}등급</option>)}
                    </select>
                  )}
                  {(brandFilter || priceMax || energyFilter) && (
                    <button className={s.filterClear} onClick={() => { setBrandFilter(''); setPriceMax(''); setEnergyFilter('') }}>
                      필터 초기화
                    </button>
                  )}
                  <span className={s.filterCount}>{filteredProducts.length}개 상품</span>
                </div>
                {filteredProducts.length > 0 ? (
                  <div className={s.pickGrid}>
                    {filteredProducts.map((p, i) => (
                      <button key={i} className={s.pickCard} onClick={() => analyzeProduct(p)}>
                        <div className={s.pickImageWrap}>
                          {p.image
                            ? <img className={s.pickImage} src={p.image} alt={p.title} />
                            : <div className={s.pickImagePlaceholder} />}
                        </div>
                        <div className={s.pickInfo}>
                          {p.brand && <span className={s.pickBrand}>{p.brand}</span>}
                          <span className={s.pickTitle}>{p.title}</span>
                          <span className={s.pickPrice}>{fmtP(p.price)}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className={s.noData}>필터 조건에 맞는 상품이 없습니다</div>
                )}
              </>
            ) : (
              <div className={s.noData}>검색된 상품이 없습니다 — 다른 검색어로 시도해보세요</div>
            )
          )}

          {/* ── 선택한 상품 표시 + 분석 결과 ── */}
          {selected && (
            <div className={s.selectedBar}>
              {selected.image
                ? <img className={s.selectedImage} src={selected.image} alt={selected.title} />
                : <div className={s.selectedImagePlaceholder} />}
              <div className={s.selectedInfo}>
                {selected.brand && <span className={s.pickBrand}>{selected.brand}</span>}
                <span className={s.selectedTitle}>{selected.title}</span>
              </div>
              {data && !data.unsupported && (
                <>
                  <button className={s.actionBtn} onClick={refreshAnalysis} disabled={refreshing || loading}>
                    {refreshing ? '업데이트 중...' : '업데이트'}
                  </button>
                  <button className={s.actionBtn} onClick={exportPdf} disabled={loading}>출력</button>
                </>
              )}
              <button className={s.backBtn} onClick={backToProducts}>다른 상품 선택</button>
            </div>
          )}

          {loading && (
            <div className={s.loadingWrap}>
              <div className={s.spinner} />
              <p>선택하신 상품 분석 중... (시장 현황·리뷰·트렌드·가격 동시 수집)</p>
            </div>
          )}

          {data && !loading && data.unsupported && (
            <div className={s.card}>
              <div className={s.noData}>{data.message}</div>
            </div>
          )}

          {data && !loading && !data.unsupported && (
            <div className={s.printArea}>
              {(data.model_number || data.category) && (
                <div className={s.resultHeader}>
                  {data.model_number && <span className={s.modelBadge}>{data.model_number}</span>}
                  {data.category && <span className={s.catBadge}>{data.category}</span>}
                </div>
              )}

              <div className={s.grid}>

                {/* 1. 제품 기본 정보 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>제품 기본 정보</h2>
                      <p className={s.cardSub}>실시간 수집된 제품 정보</p>
                    </div>
                  </div>
                  <div className={s.productInfoWrap}>
                    {info?.image
                      ? <img className={s.productInfoImage} src={info.image} alt={info.name} />
                      : <div className={s.productInfoImagePlaceholder} />}
                    <div className={s.productInfoGrid}>
                      <div className={s.infoRow}>
                        <span className={s.infoLabel}>제품명</span>
                        <span className={s.infoValue}>{info?.name}</span>
                      </div>
                      <div className={s.infoRow}>
                        <span className={s.infoLabel}>제조사</span>
                        <span className={s.infoValue}>{info?.brand || '확인 안됨'}</span>
                      </div>
                      <div className={s.infoRow}>
                        <span className={s.infoLabel}>출시일</span>
                        <span className={s.infoValue}>{info?.release_date || '확인 안됨'}</span>
                      </div>
                      <div className={s.infoRow}>
                        <span className={s.infoLabel}>출시가격</span>
                        <span className={s.infoValue}>{info?.launch_price ? fmtP(info.launch_price) : '확인 안됨'}</span>
                      </div>
                      <div className={s.infoRow}>
                        <span className={s.infoLabel}>현재가격</span>
                        <span className={s.infoValue} style={{ color: '#22c55e', fontWeight: 800 }}>
                          {info?.current_price ? fmtP(info.current_price) : '데이터 부족'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. AI 종합 리포트 */}
                <div className={`${s.card} ${sig ? s.cardAccent : ''}`}
                  style={sig ? { borderLeftColor: sig.color, background: sig.bg } : undefined}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>AI 종합 리포트</h2>
                      <p className={s.cardSub}>가격·수요·리뷰를 종합한 AI 분석</p>
                    </div>
                    {sig && (
                      <span className={s.signalBadge} style={{ color: sig.color, background: sig.bg, border: `1px solid ${sig.border}` }}>
                        {sig.icon} {report.conclusion_label}
                      </span>
                    )}
                  </div>
                  {report?.summary
                    ? <p className={s.reportSummary}>{report.summary}</p>
                    : <div className={s.noData}>리포트를 생성하는 데 필요한 데이터가 부족합니다</div>}
                  {report?.conclusion_reason && (
                    <div className={s.reasonBox} style={{ borderColor: sig?.border }}>
                      <span style={{ marginRight: 6 }}>{sig?.icon}</span>
                      {report.conclusion_reason}
                    </div>
                  )}
                </div>

                {/* 3-1. 검색량 추이 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>검색량 추이 · 예측</h2>
                      <p className={s.cardSub}>
                        {data.category || '카테고리'} · week 단위 · DataLab 검색 관심도 + Prophet
                      </p>
                    </div>
                    {data.interest_forecast?.rag_enhanced && (
                      <span className={s.ragBadge}>RAG 강화</span>
                    )}
                  </div>
                  <ForecastChart
                    history={data.interest_forecast?.history}
                    linearTrend={data.interest_forecast?.linear_trend}
                    prophetForecast={data.interest_forecast?.prophet_forecast}
                  />
                  {data.interest_forecast?.reason && (
                    <div className={s.reasonBox}>
                      <span style={{ marginRight: 6 }}>📈</span>
                      {data.interest_forecast.reason}
                    </div>
                  )}
                </div>

                {/* 4. 가격 변동 분석 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>가격 변동 분석</h2>
                      <p className={s.cardSub}>
                        {priceChg?.change_pct != null
                          ? (priceChg.change_pct !== 0
                              ? `이력 기간 중 ${priceChg.change_pct > 0 ? '+' : ''}${priceChg.change_pct}% 변동`
                              : (priceChg.range_pct
                                  ? `이력 기간 순변동 0% (최대 ${priceChg.range_pct}% 등락 있었음)`
                                  : '이력 기간 중 변동 없음'))
                          : '가격 이력 누적 중'}
                      </p>
                    </div>
                  </div>
                  <PriceHistoryChart history={priceChg?.history} />
                  {priceChg?.reason && (
                    <div className={s.reasonBox}>
                      <span style={{ marginRight: 6 }}>📉</span>
                      {priceChg.reason}
                    </div>
                  )}
                </div>

                {/* 5. 가격 적정성 분석 */}
                <div className={`${s.card} ${fairSig ? s.cardAccent : ''}`}
                  style={fairSig ? { borderLeftColor: fairSig.color, background: fairSig.bg } : undefined}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>가격 적정성 분석</h2>
                      <p className={s.cardSub}>역대 평균가 대비 현재가 판단</p>
                    </div>
                    {fairSig && (
                      <span className={s.signalBadge} style={{ color: fairSig.color, background: fairSig.bg, border: `1px solid ${fairSig.border}` }}>
                        {fairSig.icon} {fairness.label}
                      </span>
                    )}
                  </div>
                  {fairness?.current_price ? (
                    <div className={s.priceStats}>
                      <div className={s.priceStat}>
                        <span className={s.psLabel}>현재가</span>
                        <span className={s.psValue}>{fmtP(fairness.current_price)}</span>
                      </div>
                      <div className={s.priceStat}>
                        <span className={s.psLabel}>역대 평균가</span>
                        <span className={s.psValue}>{fmtP(fairness.hist_avg_price)}</span>
                      </div>
                      <div className={s.priceStat}>
                        <span className={s.psLabel}>평균 대비</span>
                        <span className={s.psValue} style={{ color: fairSig?.color }}>
                          {fairness.vs_hist_pct > 0 ? '+' : ''}{fairness.vs_hist_pct}%
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className={s.noData}>가격 데이터가 부족합니다</div>
                  )}
                  {fairness?.reason && (
                    <div className={s.reasonBox} style={{ borderColor: fairSig?.border }}>{fairness.reason}</div>
                  )}
                </div>

                {/* 6. AI 수요 예측 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>AI 수요 예측</h2>
                      <p className={s.cardSub}>
                        {demand?.forecast_change_pct != null
                          ? `예측 구간 관심도 ${demand.forecast_change_pct > 0 ? '+' : ''}${demand.forecast_change_pct}%`
                          : 'Prophet 예측 기반'}
                      </p>
                    </div>
                  </div>
                  {demand?.headline ? (
                    <div className={s.demandRow}>
                      <p className={s.demandHeadline}>{demand.headline}</p>
                      <Sparkline data={
                        data.sales_forecast?.prophet_forecast?.length > 0
                          ? data.sales_forecast.prophet_forecast
                          : data.interest_forecast?.prophet_forecast
                      } />
                    </div>
                  ) : (
                    <div className={s.noData}>예측에 필요한 데이터가 부족합니다</div>
                  )}
                  {demand?.reason && <div className={s.reasonBox}>{demand.reason}</div>}
                </div>

                {/* 7. 경쟁 제품 비교 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>경쟁 제품 비교</h2>
                      <p className={s.cardSub}>
                        {comp?.competitor?.matched_capacity
                          ? '비슷한 스펙(용량)의 다른 브랜드 제품과 1:1 비교'
                          : '비슷한 가격대의 다른 브랜드 제품과 비교'}
                      </p>
                    </div>
                  </div>
                  {comp?.competitor ? (
                    <>
                      <div className={s.compGrid}>
                        <div className={s.compCol}>
                          <div className={s.compColHead}>
                            {info?.image && <img src={info.image} alt="" className={s.compThumb} />}
                            <p className={s.compColTitle}>검색하신 제품</p>
                          </div>
                          <p className={s.compMeta}>
                            {data.model_number && <span>{data.model_number}</span>}
                            {info?.current_price != null && <span> · {fmtP(info.current_price)}</span>}
                          </p>
                          <ul className={s.prosConsList}>
                            {comp.selected_pros?.map((p, i) => <li key={`p${i}`} className={s.prosItem}>+ {p}</li>)}
                            {comp.selected_cons?.map((c, i) => <li key={`c${i}`} className={s.consItem}>− {c}</li>)}
                          </ul>
                        </div>
                        <div className={s.compCol}>
                          <div className={s.compColHead}>
                            {comp.competitor.image && <img src={comp.competitor.image} alt="" className={s.compThumb} />}
                            <p className={s.compColTitle}>
                              <a href={comp.competitor.link} target="_blank" rel="noopener noreferrer">
                                {comp.competitor.brand} (경쟁 제품)
                              </a>
                              {comp.competitor.matched_capacity && (
                                <span className={s.specNote}> · {comp.competitor.matched_capacity}L</span>
                              )}
                            </p>
                          </div>
                          <p className={s.compMeta}>
                            {comp.competitor.model_number && <span>{comp.competitor.model_number}</span>}
                            {comp.competitor.price != null && <span> · {fmtP(comp.competitor.price)}</span>}
                          </p>
                          <ul className={s.prosConsList}>
                            {comp.competitor_pros?.map((p, i) => <li key={`p${i}`} className={s.prosItem}>+ {p}</li>)}
                            {comp.competitor_cons?.map((c, i) => <li key={`c${i}`} className={s.consItem}>− {c}</li>)}
                          </ul>
                        </div>
                      </div>
                      {comp.recommended && (
                        <div className={s.reasonBox}>
                          <strong>{comp.recommended === 'selected' ? '검색하신 제품' : `${comp.competitor.brand} 제품`} 추천</strong>
                          {comp.recommendation_reason && <> — {comp.recommendation_reason}</>}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className={s.noData}>비교할 경쟁 제품을 찾지 못했습니다</div>
                  )}
                </div>

                {/* 8. 소비자 리뷰 감성 분석 */}
                <div className={s.card}>
                  <div className={s.cardHead}>
                    <div>
                      <h2 className={s.cardTitle}>소비자 리뷰 감성 분석</h2>
                      <p className={s.cardSub}>블로그·카페 실제 후기 기반</p>
                    </div>
                    {sentiment?.score != null && (
                      <span className={s.sentScore}
                        style={{ color: sentiment.score >= 60 ? '#22c55e' : sentiment.score >= 40 ? '#f59e0b' : '#f87171' }}>
                        {sentiment.score}점
                      </span>
                    )}
                  </div>
                  {sentiment?.score != null ? (
                    <>
                      <div className={s.sentBar}>
                        <div className={s.sentBarFill}
                          style={{ width: `${sentiment.score}%`,
                            background: sentiment.score >= 60
                              ? 'linear-gradient(90deg,#22c55e,#16a34a)'
                              : sentiment.score >= 40
                              ? 'linear-gradient(90deg,#f59e0b,#d97706)'
                              : 'linear-gradient(90deg,#f87171,#dc2626)' }} />
                      </div>
                      <div className={s.sentCount}>
                        <button
                          className={`${s.sentTab} ${sentimentTab === 'pos' ? s.sentTabActivePos : ''}`}
                          onClick={() => { setSentimentTab('pos'); setReviewsExpanded(false) }}
                        >
                          긍정 {sentiment.pos}
                        </button>
                        <button
                          className={`${s.sentTab} ${sentimentTab === 'neg' ? s.sentTabActiveNeg : ''}`}
                          onClick={() => { setSentimentTab('neg'); setReviewsExpanded(false) }}
                        >
                          부정 {sentiment.neg}
                        </button>
                      </div>
                      {sentimentReviews.length > 0 ? (
                        <>
                          <div className={s.reviewList}>
                            {(reviewsExpanded ? sentimentReviews : sentimentReviews.slice(0, 4)).map((r, i) => (
                              <a key={i} href={r.link} target="_blank" rel="noopener noreferrer" className={s.reviewItem}>
                                <div className={s.reviewMeta}>
                                  <span className={s.reviewSource}>{r.source}</span>
                                </div>
                                <p className={s.reviewText}>{r.text.slice(0, 80)}…</p>
                              </a>
                            ))}
                          </div>
                          {sentimentReviews.length > 4 && (
                            <button className={s.showMoreBtn} onClick={() => setReviewsExpanded(e => !e)}>
                              {reviewsExpanded ? '접기' : `${sentimentReviews.length}개 전체 보기`}
                            </button>
                          )}
                        </>
                      ) : (
                        <div className={s.noData}>{sentimentTab === 'pos' ? '긍정' : '부정'} 리뷰가 없습니다</div>
                      )}
                      {(sentiment.positive_summary || sentiment.negative_summary) && (
                        <div className={s.sentSummaryWrap}>
                          {sentiment.positive_summary && (
                            <div className={s.sentSummaryBox} style={{ borderColor: 'rgba(34,197,94,0.3)' }}>
                              <p className={s.sentSummaryTitle} style={{ color: '#22c55e' }}>👍 긍정 의견 요약</p>
                              <p className={s.sentSummaryText}>{sentiment.positive_summary}</p>
                            </div>
                          )}
                          {sentiment.negative_summary && (
                            <div className={s.sentSummaryBox} style={{ borderColor: 'rgba(248,113,113,0.3)' }}>
                              <p className={s.sentSummaryTitle} style={{ color: '#f87171' }}>👎 부정 의견 요약</p>
                              <p className={s.sentSummaryText}>{sentiment.negative_summary}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className={s.noData}>수집된 리뷰가 부족합니다</div>
                  )}
                </div>

              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
