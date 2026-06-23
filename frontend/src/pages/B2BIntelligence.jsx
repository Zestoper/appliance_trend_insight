import { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'
import s from '../styles/B2BIntelligence.module.css'

/* ─────────────── 상수 ─────────────── */
const CATEGORIES = ['에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기', 'TV', '전기밥솥', '전자레인지']
const PERIODS    = [{ v: '1m', l: '1개월' }, { v: '3m', l: '3개월' }, { v: '6m', l: '6개월' }, { v: '1y', l: '1년' }]
const PERIOD_LABEL = { '1m': '최근 1개월', '3m': '최근 3개월', '6m': '최근 6개월', '1y': '최근 1년' }
const BRAND_COLORS = ['#6366f1', '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
const TIERS = ['전체', '저가', '중저가', '중고가', '고가']
const TIER_COLOR = {
  '저가':  { text: '#10b981', bg: '#10b98118' },
  '중저가': { text: '#3b82f6', bg: '#3b82f618' },
  '중고가': { text: '#a855f7', bg: '#a855f718' },
  '고가':  { text: '#f59e0b', bg: '#f59e0b18' },
}

/* 실제 가격 목록 → P25/P50/P75 분위수 계산 */
function calcTierThresholds(prices) {
  const valid = prices.filter(p => p > 0).sort((a, b) => a - b)
  if (valid.length < 4) return null
  const at = r => valid[Math.floor(valid.length * r)]
  return { p25: at(0.25), p50: at(0.50), p75: at(0.75) }
}

function getDynamicTier(price, thresholds) {
  if (price == null || !thresholds) return null
  if (price < thresholds.p25) return '저가'
  if (price < thresholds.p50) return '중저가'
  if (price < thresholds.p75) return '중고가'
  return '고가'
}

const PROD_EXAMPLES = {
  '에어컨':    ['삼성 비스포크 무풍', 'LG 휘센 타워', '캐리어 인버터', '위니아 스탠드'],
  '냉장고':    ['삼성 비스포크 4도어', 'LG 디오스 오브제', '위니아 김치냉장고', '삼성 양문형'],
  '세탁기':    ['삼성 그랑데AI', 'LG 트롬 오브제', '캐리어 드럼세탁기', 'LG 미니워시'],
  '건조기':    ['삼성 그랑데AI 건조기', 'LG 트롬 건조기', '캐리어 히트펌프', '위니아 건조기'],
  '공기청정기': ['삼성 블루스카이', 'LG 퓨리케어', '코웨이 공기청정기', '위닉스 제로'],
  '로봇청소기': ['삼성 비스포크 AI', 'LG 코드제로 R9', '에코백스 디봇', '로보락 S8'],
  '식기세척기': ['삼성 비스포크 식세기', 'LG 디오스 식기세척기', '위니아 식기세척기', '쿠쿠 식기세척기'],
  'TV':        ['삼성 QLED 85인치', 'LG 올레드 65인치', '삼성 Neo QLED', 'LG 나노셀 75인치'],
  '전기밥솥':  ['쿠쿠 압력밥솥', '쿠첸 프리미엄', '삼성 전기밥솥', 'LG 전기밥솥'],
  '전자레인지': ['LG 광파오븐', '삼성 전자레인지', '위니아 전자레인지', '파나소닉 오븐레인지'],
}
/* signal_type(영문) 또는 signal(한글) 둘 다 처리 */
const SIGNAL_COLOR = {
  buy: '#10b981', watch: '#3b82f6', neutral: '#6b7280', caution: '#f59e0b', wait: '#ef4444',
  '매입 적기': '#10b981', '구매 추천': '#10b981',
  '하락 추세': '#3b82f6', '관망 권장': '#f59e0b',
  '상승 추세': '#f59e0b', '가격 상승': '#ef4444',
  '보합': '#6b7280', '적정가': '#6b7280',
}
const SIGNAL_LABEL = {
  buy: '매입 적기', watch: '하락 추세', neutral: '보합', caution: '상승 추세', wait: '가격 상승',
}

const fmtWon = p => p == null ? '-' : p >= 10000 ? `${Math.round(p / 10000).toLocaleString()}만원` : `${p.toLocaleString()}원`

/* ─────────────── 차트 유틸 ─────────────── */
function calcRegression(ys) {
  const n = ys.length
  if (n < 2) return null
  const xm = (n - 1) / 2, ym = ys.reduce((a, b) => a + b, 0) / n
  const ssxy = ys.reduce((a, y, i) => a + (i - xm) * (y - ym), 0)
  const ssxx = ys.reduce((a, _, i) => a + (i - xm) ** 2, 0)
  const slope = ssxy / ssxx, intercept = ym - slope * xm
  return { slope, intercept }
}

/* ─────────────── 공통 컴포넌트 ─────────────── */
function SectionHead({ num, title, sub }) {
  return (
    <div className={s.sectionHead}>
      <div className={s.sectionHeadLeft}>
        <span className={s.sectionNum}>{num}</span>
        <div>
          <span className={s.sectionTitle}>{title}</span>
          {sub && <span className={s.sectionSub}>{sub}</span>}
        </div>
      </div>
      <span className={s.sectionLine} />
    </div>
  )
}

function StatCard({ label, value, sub, color, large }) {
  return (
    <div className={s.statCard}>
      <p className={s.statLabel}>{label}</p>
      <p className={s.statValue} style={{ color: color || 'var(--b2b-text)', fontSize: large ? '28px' : '22px' }}>{value}</p>
      {sub && <p className={s.statSub}>{sub}</p>}
    </div>
  )
}

/* ─────────────── 관심도 추이 차트 ─────────────── */
function TrendChart({ data }) {
  if (!data || data.length < 2) return <div className={s.noData}>데이터 없음</div>
  const W = 560, H = 160, P = { t: 10, b: 28, l: 38, r: 20 }
  const ratios = data.map(d => d.ratio)
  const mn = Math.min(...ratios), mx = Math.max(...ratios), rng = mx - mn || 1
  const px = i => P.l + (i / (data.length - 1)) * (W - P.l - P.r)
  const py = v => P.t + (1 - (v - mn) / rng) * (H - P.t - P.b)
  const pathD = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${px(i).toFixed(1)} ${py(d.ratio).toFixed(1)}`).join(' ')
  const pts = data.map((d, i) => ({ x: px(i), y: py(d.ratio) }))
  const xlbls = [0, Math.floor(data.length * 0.33), Math.floor(data.length * 0.66), data.length - 1]
    .map(i => ({ x: px(i), l: (data[i]?.period ?? '').slice(5, 10) }))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      {[0.33, 0.66].map(t => <line key={t} x1={P.l} x2={W - P.r} y1={P.t + t * (H - P.t - P.b)} y2={P.t + t * (H - P.t - P.b)} stroke="var(--b2b-line)" strokeWidth="1" />)}
      <path d={pathD} fill="none" stroke="#6366f1" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={pts[0].x} cy={pts[0].y} r="3.5" fill="#6366f1" />
      <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r="3.5" fill="#6366f1" />
      {xlbls.map((xl, i) => <text key={i} x={xl.x} y={H - 6} textAnchor="middle" fontSize="9" fill="var(--b2b-muted)">{xl.l}</text>)}
      <text x={P.l + 4} y={P.t + 8} fontSize="8" fill="var(--b2b-muted)" opacity="0.7">관심도 지수</text>
    </svg>
  )
}

/* ─────────────── 수요 예측 차트 ─────────────── */
function ForecastChart({ history, forecast, trainLastRatio }) {
  const reg = useMemo(() => history?.length >= 2 ? calcRegression(history.map(d => d.ratio)) : null, [history])
  if (!history || history.length < 2) return <div className={s.noData}>예측 데이터 없음</div>
  const W = 600, H = 160, pL = 38, pR = 16, pT = 12, pB = 28
  const sf = trainLastRatio && history[history.length - 1]?.ratio > 0 ? history[history.length - 1].ratio / trainLastRatio : 1
  const toD = v => (v ?? 0) * sf
  const histV = history.map(d => d.ratio)
  const fcastV = (forecast ?? []).flatMap(d => [toD(d.yhat ?? d.predicted), toD(d.upper ?? d.ci_high)].filter(v => v > 0))
  const allV = [...histV, ...fcastV].filter(v => isFinite(v) && v >= 0)
  if (!allV.length) return null
  const maxV = Math.max(...allV) * 1.06, minV = Math.max(0, Math.min(...allV) * 0.9), rng = maxV - minV || 1
  const total = history.length + (forecast?.length ?? 0)
  const toX = i => pL + (i / Math.max(total - 1, 1)) * (W - pL - pR)
  const toY = v => pT + (H - pT - pB) * (1 - (v - minV) / rng)
  const histLine  = history.map((d, i) => `${toX(i).toFixed(1)},${toY(d.ratio).toFixed(1)}`).join(' ')
  const fcastPts  = (forecast ?? []).map((d, i) => ({ x: toX(history.length + i), y: toY(toD(d.yhat ?? d.predicted ?? 0)) }))
  const fcastLine = fcastPts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const regLine   = reg ? history.map((_, i) => `${toX(i).toFixed(1)},${toY(Math.max(minV, reg.slope * i + reg.intercept)).toFixed(1)}`).join(' ') : null
  const divX = toX(history.length - 1)
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
        {[0.33, 0.66].map(t => <line key={t} x1={pL} x2={W - pR} y1={pT + t * (H - pT - pB)} y2={pT + t * (H - pT - pB)} stroke="var(--b2b-line)" strokeWidth="1" />)}
        <line x1={divX} y1={pT - 4} x2={divX} y2={H - pB + 4} stroke="rgba(99,102,241,0.3)" strokeWidth="1" strokeDasharray="4 3" />
        <polyline points={histLine} fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {fcastPts.length > 0 && (
          <polyline points={`${toX(history.length-1).toFixed(1)},${toY(history[history.length-1].ratio).toFixed(1)} ${fcastLine}`}
            fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="6 3" strokeLinecap="round" strokeLinejoin="round" />
        )}
        {regLine && <polyline points={regLine} fill="none" stroke="#94a3b8" strokeWidth="1" strokeDasharray="4 3" opacity="0.6" />}
        {fcastPts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="2.5" fill="#10b981" />)}
        <text x={pL + 4} y={pT + 8} fontSize="8" fill="var(--b2b-muted)" opacity="0.7">관심도 지수</text>
        {[0, Math.floor(history.length * 0.5), history.length - 1].map(i => (
          <text key={i} x={toX(i)} y={H - 6} textAnchor="middle" fontSize="9" fill="var(--b2b-muted)">{(history[i]?.period ?? '').slice(5)}</text>
        ))}
        {forecast?.length > 0 && (
          <text x={toX(total - 1)} y={H - 6} textAnchor="end" fontSize="9" fill="#10b981">{(forecast[forecast.length - 1]?.period ?? '').slice(5)}</text>
        )}
      </svg>
      <div className={s.chartLegend}>
        <span><span className={s.legendDot} style={{ background: '#6366f1' }} />실제</span>
        <span><span className={s.legendDash} style={{ background: '#10b981' }} />예측</span>
        <span><span className={s.legendDash} style={{ background: '#94a3b8' }} />추세선</span>
      </div>
    </div>
  )
}

/* ─────────────── 가격 이력 차트 ─────────────── */
function PriceHistoryChart({ data }) {
  if (!data || data.length < 2) return <div className={s.noData}>가격 이력 없음</div>
  const W = 500, H = 140, P = { t: 10, b: 28, l: 54, r: 16 }
  const prices = data.map(d => d.avg_price)
  const mn = Math.min(...prices), mx = Math.max(...prices), rng = mx - mn || 1
  const px = i => P.l + (i / (data.length - 1)) * (W - P.l - P.r)
  const py = v => P.t + (1 - (v - mn) / rng) * (H - P.t - P.b)
  const pts = data.map((d, i) => `${px(i).toFixed(1)},${py(d.avg_price).toFixed(1)}`).join(' ')
  const trend = prices[prices.length - 1] <= prices[0] ? '#10b981' : '#ef4444'
  const yvs = [mx, (mx + mn) / 2, mn].map(v => ({ v, y: py(v) }))
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      {[0.33, 0.66].map(t => <line key={t} x1={P.l} x2={W - P.r} y1={P.t + t * (H - P.t - P.b)} y2={P.t + t * (H - P.t - P.b)} stroke="var(--b2b-line)" strokeWidth="1" />)}
      <polyline points={pts} fill="none" stroke={trend} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {yvs.map(({ v, y }) => <text key={v} x={P.l - 5} y={y + 4} textAnchor="end" fontSize="9" fill="var(--b2b-muted)">{Math.round(v / 10000)}만</text>)}
      {[0, data.length - 1].map(i => (
        <text key={i} x={px(i)} y={H - 6} textAnchor={i === 0 ? 'start' : 'end'} fontSize="9" fill="var(--b2b-muted)">{data[i]?.date?.slice(5)}</text>
      ))}
    </svg>
  )
}

/* ─────────────── 브랜드 도넛 ─────────────── */
function BrandDonut({ brands }) {
  if (!brands?.length) return null
  const R = 40, cx = 50, cy = 50, sw = 14
  let cum = 0
  const slices = brands.slice(0, 6).map((b, i) => {
    const start = cum; cum += b.pct
    return { ...b, start, color: BRAND_COLORS[i % BRAND_COLORS.length] }
  })
  function arc(sp, pct) {
    if (pct >= 100) pct = 99.99
    const a1 = (sp / 100) * 2 * Math.PI - Math.PI / 2
    const a2 = ((sp + pct) / 100) * 2 * Math.PI - Math.PI / 2
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1)
    const x2 = cx + R * Math.cos(a2), y2 = cy + R * Math.sin(a2)
    return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 ${pct > 50 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
  }
  return (
    <div className={s.donutWrap}>
      <svg width={100} height={100} style={{ flexShrink: 0 }}>
        {slices.map((sl, i) => <path key={i} d={arc(sl.start, sl.pct)} fill="none" stroke={sl.color} strokeWidth={sw} strokeLinecap="butt" />)}
      </svg>
      <div className={s.donutLegend}>
        {slices.map((sl, i) => (
          <div key={i} className={s.donutRow}>
            <span className={s.donutDot} style={{ background: sl.color }} />
            <span className={s.donutBrand}>{sl.brand}</span>
            <span className={s.donutPct}>{sl.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─────────────── 메인 페이지 ─────────────── */
export default function B2BIntelligence() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const printRef = useRef(null)

  const [category, setCategory] = useState('에어컨')
  const [period,   setPeriod]   = useState('3m')

  const [dash,          setDash]          = useState(null)
  const [trendCtx,      setTrendCtx]      = useState(null)
  const [report,        setReport]        = useState(null)
  const [price,         setPrice]         = useState(null)
  const [forecast,      setForecast]      = useState(null)
  const [shopInsight,   setShopInsight]   = useState(null)
  const [newsItems,     setNewsItems]     = useState([])

  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)
  const [fetchedAt, setFetchedAt] = useState(null)

  /* 상품 분석 */
  const [prodQuery,      setProdQuery]      = useState('')
  const [prodResult,     setProdResult]     = useState(null)
  const [prodLoading,    setProdLoading]    = useState(false)
  const [prodError,      setProdError]      = useState(null)
  const [prodTierFilter,  setProdTierFilter]  = useState('전체')
  const [sentFilter,      setSentFilter]      = useState(null) // null | 'pos' | 'neg'
  const [accuracy,        setAccuracy]        = useState(null)
  const prodRef = useRef(null)

  /* 가격 알림 */
  const [alertModal,  setAlertModal]  = useState(false)
  const [alertPrice,  setAlertPrice]  = useState('')
  const [alerts,      setAlerts]      = useState([])
  const [alertSaving, setAlertSaving] = useState(false)

  const isB2B = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'

  useEffect(() => {
    if (user && !isB2B) navigate('/b2b')
  }, [user, isB2B, navigate])

  useEffect(() => {
    setProdQuery(''); setProdResult(null); setProdError(null); setProdTierFilter('전체')
  }, [category])

  useEffect(() => {
    if (!token || !isB2B) return
    fetch(`${API_BASE}/api/b2b/prediction-accuracy?days=90`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null).then(d => setAccuracy(d)).catch(() => {})
  }, [token, isB2B])

  useEffect(() => {
    if (!token || !isB2B) return
    const go = async () => {
      setLoading(true); setError(null)
      const h = { Authorization: `Bearer ${token}` }
      try {
        const [d, tc, r, p, f, si, ni] = await Promise.all([
          fetch(`${API_BASE}/api/b2b/dashboard?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json()),
          fetch(`${API_BASE}/api/b2b/trend-context?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json()),
          fetch(`${API_BASE}/api/b2b/ai-report?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json()),
          fetch(`${API_BASE}/api/b2b/price?category=${encodeURIComponent(category)}`, { headers: h }).then(r => r.json()),
          fetch(`${API_BASE}/api/b2b/demand-forecast?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json()),
          fetch(`${API_BASE}/api/b2b/shopping-insight?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json()).catch(() => null),
          fetch(`${API_BASE}/api/b2b/news?category=${encodeURIComponent(category)}`, { headers: h }).then(r => r.json()).catch(() => []),
        ])
        setDash(d); setTrendCtx(tc); setReport(r); setPrice(p); setForecast(f)
        setShopInsight(si); setNewsItems(Array.isArray(ni) ? ni : [])
        setFetchedAt(new Date())
      } catch { setError('데이터를 불러오는 중 오류가 발생했습니다.') }
      finally { setLoading(false) }
    }
    go()
  }, [category, period, token, isB2B])

  const loadAlerts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/b2b/alerts`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) setAlerts(await res.json())
    } catch {}
  }

  const saveAlert = async () => {
    const p = parseInt(alertPrice.replace(/,/g, ''), 10)
    if (!p || p <= 0) return
    setAlertSaving(true)
    try {
      await fetch(`${API_BASE}/api/b2b/alerts`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, target_price: p }),
      })
      await loadAlerts()
      setAlertPrice('')
    } finally { setAlertSaving(false) }
  }

  const deleteAlert = async (id) => {
    await fetch(`${API_BASE}/api/b2b/alerts/${id}`, {
      method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
    })
    setAlerts(prev => prev.filter(a => a.alert_id !== id))
  }

  const downloadExcel = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/b2b/export-report?category=${encodeURIComponent(category)}&period=${period}`,
        { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) { alert('먼저 AI 리포트를 생성해주세요.'); return }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = `가전무쌍_${category}_${new Date().toISOString().slice(0,10)}.xlsx`
      a.click(); URL.revokeObjectURL(url)
    } catch { alert('다운로드 중 오류가 발생했습니다.') }
  }

  const searchProduct = async (q = prodQuery) => {
    const query = q.trim()
    if (!query) return
    setProdLoading(true); setProdError(null); setProdResult(null); setSentFilter(null)
    setTimeout(() => prodRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    try {
      const url = `${API_BASE}/api/b2b/product-analysis?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error(res.status)
      setProdResult(await res.json())
    } catch { setProdError('상품 분석 중 오류가 발생했습니다.') }
    finally { setProdLoading(false) }
  }

  /* 파생 데이터 */
  const rep       = report?.report   ?? {}
  const metrics   = report?.metrics  ?? {}
  const priceSum  = price?.summary   ?? {}
  const priceIns  = price?.price_insight ?? {}
  const brands    = dash?.brands     ?? []
  const keywords  = dash?.keywords   ?? []
  const complaints = dash?.complaints ?? []
  const complaintSummary = dash?.complaint_summary ?? []
  const ytVideos  = dash?.youtube_videos ?? []
  const newsSources = dash?.news_sources ?? []
  const trend     = dash?.trend      ?? []
  const age       = dash?.age_distribution ?? []
  const hist        = forecast?.history  ?? []
  const fcast       = forecast?.forecast ?? []
  const monthly     = forecast?.influence?.monthly_effects ?? []
  const timing      = forecast?.timing_signal
  const priceDist   = price?.price_distribution ?? []
  const topDeals    = price?.top_deals ?? []
  const confidence  = forecast?.confidence
  const inflection  = forecast?.inflection_period
  const recommendation = forecast?.recommendation
  const modelInfo   = forecast?.model_info
  const today     = fetchedAt ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) : ''

  const signalKey   = priceIns.signal_type ?? priceIns.signal ?? ''
  const signalColor = SIGNAL_COLOR[signalKey] ?? '#6b7280'
  const signalLabel = SIGNAL_LABEL[signalKey] ?? priceIns.signal ?? '-'

  if (!isB2B && user) return null

  return (
    <div className={s.page} ref={printRef}>
      <Navbar />

      {/* ── 스티키 컨트롤 바 ── */}
      <div className={s.controlBar}>
        <div className={s.controlLeft}>
          {CATEGORIES.map(c => (
            <button key={c} className={`${s.catBtn} ${category === c ? s.catBtnActive : ''}`} onClick={() => setCategory(c)}>{c}</button>
          ))}
        </div>
        <div className={s.controlRight}>
          {PERIODS.map(p => (
            <button key={p.v} className={`${s.periodBtn} ${period === p.v ? s.periodBtnActive : ''}`} onClick={() => setPeriod(p.v)}>{p.l}</button>
          ))}
          <button className={s.dlBtn} onClick={downloadExcel}>↓ 엑셀</button>
          {(!accuracy || accuracy.total_predictions === 0) && (
            <button className={s.backtestBtn} onClick={async () => {
              const r = await fetch(`${API_BASE}/api/b2b/run-backtest`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
              const d = await r.json()
              alert(`백테스트 완료: ${d.inserted}건 삽입`)
              fetch(`${API_BASE}/api/b2b/prediction-accuracy?days=90`, { headers: { Authorization: `Bearer ${token}` } })
                .then(r => r.json()).then(setAccuracy)
            }}>적중률 데이터 생성</button>
          )}
          <button className={s.alertBtn} onClick={() => { setAlertModal(true); loadAlerts() }}>알림 설정</button>
          <button className={s.printBtn} onClick={() => window.print()}>⎙ 인쇄</button>
        </div>
      </div>

      <div className={s.container}>

        {loading && (
          <div className={s.loadingScreen}>
            <div className={s.spinner} />
            <p>{category} 시장 분석 리포트 생성 중...</p>
            <span>5개 데이터 소스 병렬 수집 중</span>
          </div>
        )}

        {error && <div className={s.errorBox}>{error}</div>}

        {!loading && !error && (dash || report) && (
          <>
            {/* ── 리포트 헤더 ── */}
            <div className={s.reportHeader}>
              <div className={s.headerMeta}>
                <span className={s.headerBadge}>B2B MARKET INTELLIGENCE</span>
                <h1 className={s.headerTitle}>{category} 시장 분석 리포트</h1>
                <p className={s.headerSub}>{today} · {PERIOD_LABEL[period]} · DataLab + Naver Shopping + Groq AI</p>
              </div>
              <div className={s.headerKpis}>
                <div className={s.headerKpi}>
                  <span className={s.kpiLabel}>트렌드 지수</span>
                  <span className={s.kpiValue} style={{ color: '#6366f1' }}>{metrics.trend_score ?? '-'}</span>
                </div>
                <div className={s.headerKpiBorder} />
                <div className={s.headerKpi}>
                  <span className={s.kpiLabel}>성장률</span>
                  <span className={s.kpiValue} style={{ color: (metrics.growth_rate ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
                    {metrics.growth_rate != null ? `${metrics.growth_rate > 0 ? '+' : ''}${metrics.growth_rate}%` : '-'}
                  </span>
                </div>
                <div className={s.headerKpiBorder} />
                <div className={s.headerKpi}>
                  <span className={s.kpiLabel}>가격 신호</span>
                  <span className={s.kpiValue} style={{ color: signalColor }}>{signalLabel}</span>
                </div>
                <div className={s.headerKpiBorder} />
                <div className={s.headerKpi}>
                  <span className={s.kpiLabel}>평균가</span>
                  <span className={s.kpiValue}>{fmtWon(priceSum.avg_price)}</span>
                </div>
                {accuracy?.overall_accuracy != null && (
                  <>
                    <div className={s.headerKpiBorder} />
                    <div className={s.headerKpi}>
                      <span className={s.kpiLabel}>AI 적중률 <span style={{ fontSize: 10, color: 'var(--b2b-muted)' }}>90일</span></span>
                      <span className={s.kpiValue} style={{
                        color: accuracy.overall_accuracy >= 70 ? '#10b981' : accuracy.overall_accuracy >= 50 ? '#f59e0b' : '#ef4444'
                      }}>{accuracy.overall_accuracy}%</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* ══════════════════════════════════
                SECTION 01 · 핵심 요약
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="01" title="AI 핵심 요약 & 매입 권고" sub="AI 최종 분석 결과" />

              {/* 매입 타이밍 배너 */}
              {timing && (
                <div className={s.timingBanner} style={{ borderColor: SIGNAL_COLOR[timing.type] ?? '#6366f1' }}>
                  <div className={s.timingLeft}>
                    <span className={s.timingIcon} style={{ color: SIGNAL_COLOR[timing.type] }}>◉</span>
                    <div>
                      <p className={s.timingLabel} style={{ color: SIGNAL_COLOR[timing.type] }}>{timing.label}</p>
                      <p className={s.timingMsg}>{timing.message}</p>
                    </div>
                  </div>
                  {timing.days_to_buy > 0 && (
                    <div className={s.timingDays}>
                      <span className={s.timingDaysNum}>D-{timing.days_to_buy}</span>
                      <span className={s.timingDaysSub}>예상 최적 매입일</span>
                    </div>
                  )}
                </div>
              )}

              <div className={s.summaryGrid}>
                {/* AI 권고 카드 */}
                <div className={s.summaryCard + ' ' + s.summaryCardAccent}>
                  <p className={s.summaryCardLabel}>AI 최종 권고</p>
                  <p className={s.summaryCardAction}>{rep.action ?? '-'}</p>
                  {rep.action_reason && <p className={s.summaryCardReason}>{rep.action_reason}</p>}
                  {rep.timing && (
                    <div className={s.summaryCardTag}>
                      <span>매입 타이밍</span>
                      <span>{rep.timing}</span>
                    </div>
                  )}
                </div>

                {/* 핵심 지표 */}
                <div className={s.summaryMeta}>
                  {[
                    { l: '타겟 세그먼트', v: rep.target_segment },
                    { l: '권장 가격대', v: rep.price_range },
                    { l: '재고 조언', v: rep.inventory_advice },
                    { l: '리스크 요인', v: rep.risk_factor },
                  ].filter(i => i.v).map((item, i) => (
                    <div key={i} className={s.summaryMetaRow}>
                      <span className={s.summaryMetaLabel}>{item.l}</span>
                      <span className={s.summaryMetaValue}>{item.v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 기회 & 위험 */}
              {(rep.opportunity || rep.risk_summary) && (
                <div className={s.oppRiskRow}>
                  {rep.opportunity && (
                    <div className={s.oppCard}>
                      <p className={s.oppCardTitle}>▲ 시장 기회</p>
                      {(Array.isArray(rep.opportunity) ? rep.opportunity : [rep.opportunity]).filter(Boolean).map((o, i) => (
                        <p key={i} className={s.oppCardItem}>{o}</p>
                      ))}
                    </div>
                  )}
                  {rep.risk_summary && (
                    <div className={s.riskCard}>
                      <p className={s.riskCardTitle}>▼ 위험 요인</p>
                      {(Array.isArray(rep.risk_summary) ? rep.risk_summary : [rep.risk_summary]).filter(Boolean).map((r, i) => (
                        <p key={i} className={s.riskCardItem}>{r}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 02 · 시장 현황
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="02" title="시장 현황 · 관심도 추이" sub="네이버 DataLab 검색 트렌드" />
              {trend.length === 0 && (
                <div className={s.sectionEmpty}>네이버 DataLab 데이터를 불러오지 못했습니다. 잠시 후 새로고침해주세요.</div>
              )}
              <div className={s.marketRow}>
                <div className={s.marketChart}>
                  <p className={s.chartTitle}>관심도 추이 ({PERIOD_LABEL[period]})</p>
                  <TrendChart data={trend} />
                </div>
                <div className={s.marketRight}>
                  <div className={s.marketStats}>
                    <StatCard label="트렌드 점수" value={metrics.trend_score ?? '-'} sub="100점 기준" color="#6366f1" />
                    <StatCard label="성장률" value={metrics.growth_rate != null ? `${metrics.growth_rate > 0 ? '+' : ''}${metrics.growth_rate}%` : '-'}
                      color={(metrics.growth_rate ?? 0) >= 0 ? '#10b981' : '#ef4444'} />
                  </div>
                  <div className={s.brandSection}>
                    <p className={s.miniTitle}>브랜드 점유율</p>
                    <BrandDonut brands={brands} />
                  </div>
                </div>
              </div>

              {/* 연령 분포 */}
              {age.length > 0 && (
                <div className={s.ageSectionInline}>
                  <p className={s.miniTitle}>주요 소비층</p>
                  <div className={s.ageBarList}>
                    {age.map((a, i) => (
                      <div key={i} className={s.ageBarRow}>
                        <span className={s.ageBarLabel}>{a.label}</span>
                        <div className={s.ageBarTrack}>
                          <div className={s.ageBarFill} style={{ width: `${(a.pct / Math.max(...age.map(x => x.pct))) * 100}%` }} />
                        </div>
                        <span className={s.ageBarPct}>{a.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 쇼핑인사이트 */}
              {shopInsight && !shopInsight.error && (
                <div className={s.shopInsightRow}>
                  {shopInsight.gender?.length > 0 && (
                    <div className={s.shopInsightCard}>
                      <p className={s.miniTitle}>성별 쇼핑 비중</p>
                      {(() => {
                        const m = shopInsight.gender.reduce((a, d) => a + (d.group === 'male' ? d.ratio : 0), 0)
                        const f = shopInsight.gender.reduce((a, d) => a + (d.group === 'female' ? d.ratio : 0), 0)
                        const t = m + f || 1
                        return (
                          <div className={s.genderBar}>
                            <div className={s.genderMale} style={{ width: `${Math.round(m/t*100)}%` }}>남 {Math.round(m/t*100)}%</div>
                            <div className={s.genderFemale} style={{ width: `${Math.round(f/t*100)}%` }}>여 {Math.round(f/t*100)}%</div>
                          </div>
                        )
                      })()}
                    </div>
                  )}
                  {shopInsight.device?.length > 0 && (
                    <div className={s.shopInsightCard}>
                      <p className={s.miniTitle}>기기별 쇼핑 비중</p>
                      {(() => {
                        const devMap = {}
                        shopInsight.device.forEach(d => { devMap[d.group] = (devMap[d.group] || 0) + d.ratio })
                        const total = Object.values(devMap).reduce((a, b) => a + b, 0) || 1
                        const label = { pc: 'PC', mo: '모바일', ta: '태블릿' }
                        const color = { pc: '#6366f1', mo: '#10b981', ta: '#f59e0b' }
                        return Object.entries(devMap).map(([g, v]) => (
                          <div key={g} className={s.ageBarRow}>
                            <span className={s.ageBarLabel}>{label[g] || g}</span>
                            <div className={s.ageBarTrack}>
                              <div className={s.ageBarFill} style={{ width: `${Math.round(v/total*100)}%`, background: color[g] }} />
                            </div>
                            <span className={s.ageBarPct}>{Math.round(v/total*100)}%</span>
                          </div>
                        ))
                      })()}
                    </div>
                  )}
                  {shopInsight.age?.length > 0 && (
                    <div className={s.shopInsightCard}>
                      <p className={s.miniTitle}>연령별 쇼핑 클릭</p>
                      {(() => {
                        const ageMap = {}
                        shopInsight.age.forEach(d => { ageMap[d.group] = (ageMap[d.group] || 0) + d.ratio })
                        const total = Math.max(...Object.values(ageMap)) || 1
                        const ageLabel = { '10s':'10대','20s':'20대','30s':'30대','40s':'40대','50s':'50대','60s':'60대+' }
                        return Object.entries(ageMap).map(([g, v]) => (
                          <div key={g} className={s.ageBarRow}>
                            <span className={s.ageBarLabel}>{ageLabel[g] || g}</span>
                            <div className={s.ageBarTrack}>
                              <div className={s.ageBarFill} style={{ width: `${Math.round(v/total*100)}%` }} />
                            </div>
                            <span className={s.ageBarPct}>{Math.round(v/total*100)}%</span>
                          </div>
                        ))
                      })()}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 03 · 가격 경쟁력
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="03" title="가격 경쟁력 분석" sub="실시간 네이버 쇼핑 기준" />

              <div className={s.priceTopRow}>
                <StatCard label="평균가" value={fmtWon(priceSum.avg_price)} large />
                <StatCard label="최저가" value={fmtWon(priceSum.min_price)} color="#10b981" />
                <StatCard label="최고가" value={fmtWon(priceSum.max_price)} color="#ef4444" />
                <StatCard label="중위가" value={fmtWon(priceSum.median_price)} />
                <StatCard label="조사 상품" value={priceSum.total_products ? `${priceSum.total_products}개` : '-'} />
                <StatCard label="가격 변동"
                  value={priceSum.price_change_pct != null ? `${priceSum.price_change_pct > 0 ? '+' : ''}${priceSum.price_change_pct}%` : '-'}
                  color={(priceSum.price_change_pct ?? 0) <= 0 ? '#10b981' : '#ef4444'} />
              </div>

              <div className={s.priceBottomRow}>
                {/* 브랜드 가격표 */}
                <div className={s.brandTable}>
                  <p className={s.miniTitle}>브랜드별 가격 경쟁력</p>
                  <table className={s.table}>
                    <thead>
                      <tr>
                        <th>브랜드</th>
                        <th>평균가</th>
                        <th>최저가</th>
                        <th>상품수</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(price?.by_brand ?? []).slice(0, 8).map((b, i) => (
                        <tr key={i}>
                          <td>{b.brand}</td>
                          <td>{fmtWon(b.avg_price)}</td>
                          <td style={{ color: '#10b981' }}>{fmtWon(b.min_price)}</td>
                          <td>{b.count}개</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* 가격 이력 */}
                <div className={s.priceHistChart}>
                  <p className={s.miniTitle}>가격 이력 추이</p>
                  <PriceHistoryChart data={price?.price_history} />
                  {priceIns.signal && (
                    <div className={s.priceInsightBox} style={{ borderColor: signalColor }}>
                      <p className={s.priceInsightSignal} style={{ color: signalColor }}>{signalLabel}</p>
                      <p className={s.priceInsightReason}>{priceIns.reason}</p>
                      {priceIns.brand_pick && <p className={s.priceInsightBrand}>추천 브랜드: <strong>{priceIns.brand_pick}</strong></p>}
                    </div>
                  )}
                </div>
              </div>

              {/* 가격 분포 + 최저가 딜 */}
              {(priceDist.length > 0 || topDeals.length > 0) && (
                <div className={s.priceExtraRow}>
                  {priceDist.length > 0 && (
                    <div className={s.distCard}>
                      <p className={s.miniTitle}>가격대별 상품 분포</p>
                      <div className={s.distList}>
                        {(() => {
                          const maxCnt = Math.max(...priceDist.map(d => d.count), 1)
                          return priceDist.map((d, i) => (
                            <div key={i} className={s.distRow}>
                              <span className={s.distLabel}>{d.range}</span>
                              <div className={s.distBar}>
                                <div className={s.distBarFill} style={{ width: `${(d.count / maxCnt) * 100}%` }} />
                              </div>
                              <span className={s.distCount}>{d.count}개</span>
                            </div>
                          ))
                        })()}
                      </div>
                    </div>
                  )}
                  {topDeals.length > 0 && (
                    <div className={s.dealsCard}>
                      <p className={s.miniTitle}>실시간 최저가 딜 TOP 5</p>
                      <div className={s.dealsList}>
                        {topDeals.slice(0, 5).map((d, i) => (
                          <a key={i} href={d.link} target="_blank" rel="noopener noreferrer" className={s.dealItem}>
                            <span className={s.dealRank}>{i + 1}</span>
                            <div className={s.dealInfo}>
                              <span className={s.dealTitle}>{d.title}</span>
                              <span className={s.dealBrand}>{d.brand}</span>
                            </div>
                            <span className={s.dealPrice} style={{ color: '#10b981' }}>{fmtWon(d.price)}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 04 · 수요 예측
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="04" title="수요 예측 · 매입 타이밍" sub="Prophet AI 예측 모델" />

              {forecast?.error && (
                <div className={s.sectionRetry}>
                  <span>수요 예측 로딩 실패 — {forecast.error}</span>
                  <button className={s.retryBtn} onClick={async () => {
                    const h = { Authorization: `Bearer ${token}` }
                    const f = await fetch(`${API_BASE}/api/b2b/demand-forecast?category=${encodeURIComponent(category)}&period=${period}`, { headers: h }).then(r => r.json())
                    setForecast(f)
                  }}>재시도</button>
                </div>
              )}

              {/* 수요 KPI 바 */}
              {(forecast?.trend_direction || forecast?.peak_period || timing) && (
                <div className={s.forecastKpis}>
                  {forecast?.trend_direction && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>트렌드 방향</span>
                      <span className={s.forecastKpiValue} style={{
                        color: forecast.trend_direction === '상승' ? '#10b981' : forecast.trend_direction === '하락' ? '#ef4444' : '#6b7280'
                      }}>{forecast.trend_direction}</span>
                    </div>
                  )}
                  {forecast?.peak_period && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>수요 피크</span>
                      <span className={s.forecastKpiValue}>{forecast.peak_period.slice(0, 7)}</span>
                    </div>
                  )}
                  {timing?.days_to_peak > 0 && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>피크까지</span>
                      <span className={s.forecastKpiValue} style={{ color: '#6366f1' }}>D-{timing.days_to_peak}</span>
                    </div>
                  )}
                  {timing?.expected_change_pct != null && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>예상 변동</span>
                      <span className={s.forecastKpiValue} style={{ color: timing.expected_change_pct >= 0 ? '#10b981' : '#ef4444' }}>
                        {timing.expected_change_pct > 0 ? '+' : ''}{timing.expected_change_pct}%
                      </span>
                    </div>
                  )}
                  {confidence != null && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>예측 신뢰도</span>
                      <span className={s.forecastKpiValue} style={{ color: confidence >= 70 ? '#10b981' : confidence >= 50 ? '#f59e0b' : '#ef4444' }}>
                        {confidence}%
                      </span>
                    </div>
                  )}
                  {inflection && (
                    <div className={s.forecastKpi}>
                      <span className={s.forecastKpiLabel}>변곡점</span>
                      <span className={s.forecastKpiValue} style={{ color: '#a855f7' }}>{inflection.slice(0, 7)}</span>
                    </div>
                  )}
                </div>
              )}

              <div className={s.forecastRow}>
                <div className={s.forecastChart}>
                  <p className={s.chartTitle}>관심도 추세 & 예측</p>
                  <ForecastChart history={hist} forecast={fcast} trainLastRatio={forecast?.train_last_ratio} />
                </div>
                {monthly.length > 0 && (
                  <div className={s.monthlySection}>
                    <p className={s.miniTitle}>월별 수요 영향도</p>
                    <div className={s.monthlyList}>
                      {monthly.slice(0, 12).map((m, i) => {
                        const eff = m.effect ?? 0
                        const isPeak = m.month === forecast?.influence?.peak_month
                        return (
                          <div key={i} className={s.monthlyRow}>
                            <span className={s.monthlyLabel} style={{ color: isPeak ? '#10b981' : 'var(--b2b-text2)' }}>{m.month}월</span>
                            <div className={s.monthlyBar}>
                              {eff >= 0
                                ? <div className={s.monthlyFillPos} style={{ width: `${Math.min(eff * 4, 100)}%` }} />
                                : <div className={s.monthlyFillNeg} style={{ width: `${Math.min(Math.abs(eff) * 4, 100)}%` }} />
                              }
                            </div>
                            <span className={s.monthlyVal} style={{ color: eff >= 0 ? '#10b981' : '#ef4444' }}>
                              {eff >= 0 ? '+' : ''}{eff.toFixed(1)}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* 시나리오 요약 */}
              {forecast?.rag_insight && (
                <div className={s.scenarioRow}>
                  {[
                    { k: 'opportunity', label: '기회 시나리오', color: '#10b981', icon: '▲' },
                    { k: 'risk',        label: '위험 시나리오', color: '#ef4444', icon: '▼' },
                    { k: 'strategy',    label: '대응 전략',     color: '#6366f1', icon: '→' },
                  ].map(({ k, label, color, icon }) => forecast.rag_insight[k] && (
                    <div key={k} className={s.scenarioCard} style={{ borderColor: color + '40' }}>
                      <p className={s.scenarioLabel} style={{ color }}>{icon} {label}</p>
                      <p className={s.scenarioText}>{forecast.rag_insight[k]}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* 매입 추천 + 모델 정보 */}
              {(recommendation || modelInfo) && (
                <div className={s.forecastMeta}>
                  {recommendation && (
                    <div className={s.recommendationBox}>
                      <span className={s.recommendationIcon}>◎</span>
                      <p className={s.recommendationText}>{recommendation}</p>
                    </div>
                  )}
                  {modelInfo && (
                    <div className={s.modelInfoBox}>
                      <span className={s.modelInfoLabel}>분석 모델</span>
                      <span className={s.modelInfoValue}>{modelInfo.used}</span>
                      {modelInfo.rmse?.prophet != null && (
                        <span className={s.modelInfoSub}>Prophet RMSE {modelInfo.rmse.prophet}</span>
                      )}
                      {modelInfo.rmse?.xgb != null && (
                        <span className={s.modelInfoSub}>XGB RMSE {modelInfo.rmse.xgb}</span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 05 · 소비자 분석
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="05" title="소비자 분석 · 니즈 & 불만" sub="검색 데이터 + 리뷰 AI 분석" />

              {keywords.length === 0 && complaints.length === 0 && (
                <div className={s.sectionEmpty}>소비자 데이터를 불러오지 못했습니다. 잠시 후 새로고침해주세요.</div>
              )}
              <div className={s.consumerRow}>
                {/* 관심 키워드 */}
                <div className={s.kwSection}>
                  <p className={s.miniTitle}>주요 관심 키워드</p>
                  {keywords.length > 0 ? (
                    <div className={s.kwList}>
                      {keywords.slice(0, 10).map((kw, i) => (
                        <div key={i} className={s.kwItem}>
                          <span className={s.kwRank}>{i + 1}</span>
                          <span className={s.kwWord}>{kw.word}</span>
                          <div className={s.kwBar}>
                            <div className={s.kwBarFill}
                              style={{ width: `${(kw.count / keywords[0].count) * 100}%` }} />
                          </div>
                          <span className={s.kwCount}>{kw.count}</span>
                        </div>
                      ))}
                    </div>
                  ) : <div className={s.noData}>키워드 없음</div>}
                </div>

                {/* 불만 분석 */}
                <div className={s.complaintSection}>
                  <p className={s.miniTitle}>소비자 불만 분석</p>
                  {complaintSummary.length > 0 ? (
                    <div className={s.complaintList}>
                      {complaintSummary.slice(0, 6).map((c, i) => (
                        <div key={i} className={s.complaintItem}>
                          <div className={s.complaintHead}>
                            <span className={s.complaintTag}>{c.tag}</span>
                            <span className={s.complaintPct} style={{ color: '#ef4444' }}>{c.pct}%</span>
                          </div>
                          <div className={s.complaintBar}>
                            <div className={s.complaintBarFill} style={{ width: `${c.pct}%` }} />
                          </div>
                          {c.brands?.length > 0 && (
                            <p className={s.complaintBrands}>관련 브랜드: {c.brands.join(', ')}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : complaints.length > 0 ? (
                    <div className={s.complaintList}>
                      {complaints.slice(0, 5).map((c, i) => (
                        <div key={i} className={s.complaintItemAlt}>
                          <span className={s.complaintTag}>{c.complaint ?? c.word ?? c}</span>
                        </div>
                      ))}
                    </div>
                  ) : <div className={s.noData}>불만 데이터 없음</div>}

                  {/* AI 제품 제안 */}
                  {rep.product_brief && (
                    <div className={s.productBriefBox}>
                      <p className={s.productBriefLabel}>AI 상품 기획 제안</p>
                      <p className={s.productBriefText}>{rep.product_brief}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* 추천 기능 */}
              {rep.recommended_features?.length > 0 && (
                <div className={s.featuresRow}>
                  <p className={s.miniTitle}>추천 탑재 기능</p>
                  <div className={s.featuresList}>
                    {rep.recommended_features.filter(Boolean).map((f, i) => (
                      <span key={i} className={s.featureChip}>{f}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* 불만 근거 문장 */}
              {complaintSummary.some(c => c.evidence) && (
                <div className={s.evidenceSection}>
                  <p className={s.miniTitle}>불만 근거 상세</p>
                  <div className={s.evidenceList}>
                    {complaintSummary.filter(c => c.evidence).slice(0, 5).map((c, i) => (
                      <div key={i} className={s.evidenceItem}>
                        <span className={s.evidenceTag}>{c.tag}</span>
                        <p className={s.evidenceText}>{c.evidence}</p>
                        {c.brands?.length > 0 && (
                          <p className={s.evidenceBrands}>{c.brands.join(' · ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* YouTube 리뷰 영상 */}
              {ytVideos.length > 0 && (
                <div className={s.ytSection}>
                  <p className={s.miniTitle}>YouTube 리뷰 영상</p>
                  <div className={s.ytGrid}>
                    {ytVideos.slice(0, 6).map((v, i) => (
                      <a key={i} href={v.link} target="_blank" rel="noopener noreferrer" className={s.ytCard}>
                        {v.thumbnail
                          ? <img src={v.thumbnail} alt={v.title} className={s.ytThumb} />
                          : <div className={s.ytThumbFallback}>▶</div>}
                        <div className={s.ytInfo}>
                          <p className={s.ytTitle}>{v.title}</p>
                          <p className={s.ytMeta}>{v.channel} · {v.pubDate}</p>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* 사용 환경 */}
              {trendCtx && (
                <div className={s.contextRow}>
                  {[
                    { title: '주요 구매 목적', data: trendCtx.purpose },
                    { title: '주요 지역',       data: trendCtx.region },
                    { title: '설치 형태',       data: trendCtx.install },
                    { title: '연관 가전',        data: trendCtx.related },
                  ].filter(c => c.data?.length).map(({ title, data }, i) => (
                    <div key={i} className={s.contextCard}>
                      <p className={s.contextTitle}>{title}</p>
                      {data.slice(0, 4).map((d, j) => (
                        <div key={j} className={s.contextBarRow}>
                          <span className={s.contextLabel}>{d.label}</span>
                          <div className={s.contextBar}>
                            <div className={s.contextBarFill} style={{ width: `${d.pct}%` }} />
                          </div>
                          <span className={s.contextPct}>{d.pct}%</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 06 · 뉴스 & 시장 동향
            ══════════════════════════════════ */}
            {newsItems.length > 0 && (
              <section className={s.section}>
                <SectionHead num="06" title="시장 뉴스 & 소비자 동향" sub="네이버 뉴스 · 블로그 최신 정보" />
                <div className={s.newsGrid}>
                  {newsItems.map((n, i) => (
                    <a key={i} href={n.link} target="_blank" rel="noopener noreferrer" className={s.newsCard}>
                      <div className={s.newsCardTop}>
                        <span className={s.newsType} style={{ background: n.type === 'news' ? '#6366f118' : '#10b98118', color: n.type === 'news' ? '#6366f1' : '#10b981' }}>
                          {n.type === 'news' ? '뉴스' : '블로그'}
                        </span>
                        <span className={s.newsDate}>{n.pubDate}</span>
                      </div>
                      <p className={s.newsTitle}>{n.title}</p>
                      <p className={s.newsDesc}>{n.description}</p>
                      <p className={s.newsSource}>{n.source}</p>
                    </a>
                  ))}
                </div>
              </section>
            )}

            {/* ══════════════════════════════════
                SECTION 07 · AI 전략 & 예상 효과
            ══════════════════════════════════ */}
            <section className={s.section}>
              <SectionHead num="07" title="AI 전략 제언 · 실행 플랜" sub="Groq AI 전략 분석" />

              {/* 전략 3열 */}
              {(rep.product_strategy || rep.sales_strategy || rep.service_strategy) && (
                <div className={s.strategyGrid}>
                  {[
                    { label: '상품 전략', value: rep.product_strategy, color: '#6366f1' },
                    { label: '판매 전략', value: rep.sales_strategy,   color: '#3b82f6' },
                    { label: '서비스 전략', value: rep.service_strategy, color: '#06b6d4' },
                  ].filter(s => s.value).map((st, i) => (
                    <div key={i} className={s.strategyCard} style={{ borderTopColor: st.color }}>
                      <p className={s.strategyLabel} style={{ color: st.color }}>{st.label}</p>
                      <p className={s.strategyValue}>{st.value}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* 예상 효과 */}
              {rep.expected_effects?.length > 0 && (
                <div className={s.effectsSection}>
                  <p className={s.miniTitle}>예상 효과</p>
                  <div className={s.effectsList}>
                    {rep.expected_effects.filter(Boolean).map((eff, i) => (
                      <div key={i} className={s.effectItem}>
                        <span className={s.effectIcon}>✓</span>
                        <span>{eff}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI 종합 판단 */}
              {(rep.summary || rep.summary_lines?.length > 0) && (
                <div className={s.conclusionBox}>
                  <p className={s.conclusionTitle}>AI 종합 판단</p>
                  {rep.summary_lines?.length > 0
                    ? rep.summary_lines.map((l, i) => <p key={i} className={s.conclusionLine}>{l}</p>)
                    : <p className={s.conclusionLine}>{rep.summary}</p>
                  }
                  {rep.expected_sales_growth && (
                    <div className={s.conclusionGrowth}>
                      <span>예상 매출 성장</span>
                      <span style={{ color: '#10b981', fontWeight: 900 }}>{rep.expected_sales_growth}</span>
                    </div>
                  )}
                  {rep.projection_summary && rep.projection_summary !== '-' && (
                    <p className={s.projectionSummary}>{rep.projection_summary}</p>
                  )}
                </div>
              )}
            </section>

            {/* ══════════════════════════════════
                SECTION 07 · 상품별 매입 분석
            ══════════════════════════════════ */}
            <section className={s.section} ref={prodRef}>
              <SectionHead num="08" title="상품별 매입 분석" sub="모델명 또는 상품명으로 살지 말지 판단" />

              {/* 검색 바 */}
              <div className={s.prodSearchWrap}>
                <span className={s.prodCatBadge}>{category}</span>
                <input
                  className={s.prodSearchInput}
                  placeholder={`브랜드명 · 모델명으로 검색 (예: 삼성 비스포크 / AF17B7174SZS)`}
                  value={prodQuery}
                  onChange={e => setProdQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && searchProduct()}
                />
                <button className={s.prodSearchBtn} onClick={() => searchProduct()} disabled={prodLoading}>
                  {prodLoading ? '분석 중...' : '매입 분석'}
                </button>
              </div>

              {/* 카테고리별 예시 버튼 */}
              <div className={s.prodExamples}>
                {(PROD_EXAMPLES[category] ?? []).map(ex => (
                  <button key={ex} className={s.prodExampleBtn}
                    onClick={() => { setProdQuery(ex); searchProduct(ex) }}>{ex}</button>
                ))}
              </div>

              {/* 로딩 */}
              {prodLoading && (
                <div className={s.prodLoading}>
                  <div className={s.spinner} />
                  <p>가격·트렌드·리뷰 실시간 분석 중...</p>
                  <span>네이버 쇼핑 · DataLab · 블로그/카페 동시 조회</span>
                </div>
              )}

              {prodError && <div className={s.errorBox}>{prodError}</div>}

              {/* 결과 */}
              {prodResult && !prodLoading && (() => {
                const pr = prodResult.price
                const sig = pr?.signal_type ?? 'neutral'
                const sigColor = { buy: '#10b981', wait: '#ef4444', neutral: '#6b7280' }[sig] ?? '#6b7280'
                const sigBg    = { buy: '#10b98112', wait: '#ef444412', neutral: '#6b728012' }[sig] ?? '#6b728012'
                const sigIcon  = { buy: '▼', wait: '▲', neutral: '─' }[sig] ?? '─'
                const vsHistPct = pr ? Math.round((pr.min_price - pr.hist_avg) / Math.max(pr.hist_avg, 1) * 100) : null

                /* 경쟁 상품 가격 목록으로 분위수 계산 */
                const allPrices = [
                  ...(prodResult.competitors ?? []).map(c => c.price),
                  pr?.min_price,
                ].filter(Boolean)
                const thresholds = calcTierThresholds(allPrices)

                const prodTier = getDynamicTier(pr?.min_price, thresholds)
                const tierCfg  = prodTier ? TIER_COLOR[prodTier] : null
                return (
                  <div className={s.prodResult}>
                    {/* 최상단 판정 배너 */}
                    <div className={s.prodVerdict} style={{ background: sigBg, borderColor: sigColor }}>
                      <div className={s.prodVerdictLeft}>
                        <span className={s.prodVerdictIcon} style={{ color: sigColor }}>{sigIcon}</span>
                        <div>
                          <div className={s.prodVerdictTitleRow}>
                            <p className={s.prodVerdictSignal} style={{ color: sigColor }}>{pr?.signal ?? '데이터 없음'}</p>
                            {tierCfg && (
                              <span className={s.tierBadge} style={{ color: tierCfg.text, background: tierCfg.bg }}>
                                {prodTier}
                              </span>
                            )}
                          </div>
                          <p className={s.prodVerdictReason}>{pr?.reason}</p>
                        </div>
                      </div>
                      <div className={s.prodVerdictMeta}>
                        <p className={s.prodVerdictQuery}>{prodResult.query}</p>
                        {prodResult.model_number && <p className={s.prodVerdictModel}>모델: {prodResult.model_number}</p>}
                        {prodResult.category && <p className={s.prodVerdictCat}>카테고리: {prodResult.category}</p>}
                      </div>
                    </div>

                    <div className={s.prodMainRow}>
                      {/* 왼쪽: 가격 분석 */}
                      {pr && (
                        <div className={s.prodPricePanel}>
                          {/* KPI */}
                          <div className={s.prodKpis}>
                            <div className={s.prodKpi}>
                              <span className={s.prodKpiLabel}>현재 최저가</span>
                              <span className={s.prodKpiValue} style={{ color: '#10b981' }}>{fmtWon(pr.min_price)}</span>
                            </div>
                            <div className={s.prodKpiBorder} />
                            <div className={s.prodKpi}>
                              <span className={s.prodKpiLabel}>역대 평균</span>
                              <span className={s.prodKpiValue}>{fmtWon(pr.hist_avg)}</span>
                            </div>
                            <div className={s.prodKpiBorder} />
                            <div className={s.prodKpi}>
                              <span className={s.prodKpiLabel}>역대 최저</span>
                              <span className={s.prodKpiValue} style={{ color: '#3b82f6' }}>{fmtWon(pr.hist_min)}</span>
                            </div>
                            {vsHistPct != null && (
                              <>
                                <div className={s.prodKpiBorder} />
                                <div className={s.prodKpi}>
                                  <span className={s.prodKpiLabel}>평균 대비</span>
                                  <span className={s.prodKpiValue} style={{ color: vsHistPct <= 0 ? '#10b981' : '#ef4444' }}>
                                    {vsHistPct > 0 ? '+' : ''}{vsHistPct}%
                                  </span>
                                </div>
                              </>
                            )}
                          </div>

                          {/* 쇼핑몰 가격 비교 */}
                          {pr.malls?.length > 0 && (
                            <div className={s.mallTable}>
                              <p className={s.miniTitle}>쇼핑몰 가격 비교</p>
                              <table className={s.table}>
                                <thead>
                                  <tr><th>쇼핑몰</th><th>가격</th><th>링크</th></tr>
                                </thead>
                                <tbody>
                                  {pr.malls.slice(0, 8).map((m, i) => (
                                    <tr key={i} style={i === 0 ? { background: 'rgba(16,185,129,0.05)' } : {}}>
                                      <td style={{ fontWeight: i === 0 ? 800 : 400 }}>
                                        {i === 0 && <span className={s.cheapestBadge}>최저</span>}{m.mall}
                                      </td>
                                      <td style={{ color: i === 0 ? '#10b981' : 'var(--b2b-text)', fontWeight: i === 0 ? 900 : 400 }}>
                                        {fmtWon(m.price)}
                                      </td>
                                      <td>
                                        <a href={m.link} target="_blank" rel="noopener noreferrer" className={s.mallLink}>바로가기 →</a>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}

                          {/* 가격 이력 */}
                          {pr.price_history?.length >= 2 && (
                            <div className={s.prodHistChart}>
                              <p className={s.miniTitle}>이 상품 가격 이력</p>
                              <PriceHistoryChart data={pr.price_history.map(h => ({ date: h.date, avg_price: h.min_price }))} />
                            </div>
                          )}
                        </div>
                      )}

                      {/* 오른쪽: 소비자 반응 + 트렌드 */}
                      <div className={s.prodRightPanel}>
                        {/* 감성 점수 */}
                        {prodResult.sentiment && (
                          <div className={s.sentimentCard}>
                            <p className={s.miniTitle}>소비자 반응</p>
                            <div className={s.sentimentScore}>
                              <div className={s.sentimentGauge}>
                                <div className={s.sentimentFill}
                                  style={{ width: `${prodResult.sentiment.score}%`,
                                    background: prodResult.sentiment.score >= 60 ? '#10b981' : prodResult.sentiment.score >= 40 ? '#f59e0b' : '#ef4444' }} />
                              </div>
                              <span className={s.sentimentNum}
                                style={{ color: prodResult.sentiment.score >= 60 ? '#10b981' : prodResult.sentiment.score >= 40 ? '#f59e0b' : '#ef4444' }}>
                                {prodResult.sentiment.score}점
                              </span>
                            </div>
                            <div className={s.sentimentBars}>
                              <button
                                className={`${s.sentBtn} ${sentFilter === 'pos' ? s.sentBtnActive : ''}`}
                                style={sentFilter === 'pos' ? { color: '#10b981', borderColor: '#10b981', background: '#10b98118' } : {}}
                                onClick={() => setSentFilter(f => f === 'pos' ? null : 'pos')}
                              >긍정 {prodResult.sentiment.pos}건 {sentFilter === 'pos' ? '▲' : '▼'}</button>
                              <button
                                className={`${s.sentBtn} ${sentFilter === 'neg' ? s.sentBtnActive : ''}`}
                                style={sentFilter === 'neg' ? { color: '#ef4444', borderColor: '#ef4444', background: '#ef444418' } : {}}
                                onClick={() => setSentFilter(f => f === 'neg' ? null : 'neg')}
                              >부정 {prodResult.sentiment.neg}건 {sentFilter === 'neg' ? '▲' : '▼'}</button>
                            </div>

                            {/* 클릭 시 해당 리뷰 펼치기 */}
                            {sentFilter && (() => {
                              const filtered = (prodResult.reviews ?? []).filter(r => r.sentiment === sentFilter)
                              return filtered.length > 0 ? (
                                <div className={s.sentReviews}>
                                  {filtered.map((r, i) => (
                                    <a key={i} href={r.link} target="_blank" rel="noopener noreferrer" className={s.sentReviewItem}>
                                      <div className={s.sentReviewHead}>
                                        <span className={s.reviewSource}>{r.source}</span>
                                        <span className={s.sentReviewTitle}>{r.title}</span>
                                      </div>
                                      <p className={s.sentReviewText}>{r.review}</p>
                                    </a>
                                  ))}
                                </div>
                              ) : (
                                <p className={s.sentNoReview}>{sentFilter === 'pos' ? '긍정' : '부정'} 후기를 찾지 못했습니다.</p>
                              )
                            })()}

                            {prodResult.sentiment.keywords?.length > 0 && (
                              <div className={s.sentKws}>
                                {prodResult.sentiment.keywords.slice(0, 10).map((kw, i) => (
                                  <span key={i} className={s.sentKwChip}>{kw.word}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* 관심도 추이 */}
                        {prodResult.trend?.length >= 2 && (
                          <div className={s.prodTrendCard}>
                            <p className={s.miniTitle}>검색 관심도 (최근 3개월)</p>
                            <TrendChart data={prodResult.trend} />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* 실사용 리뷰 */}
                    {prodResult.reviews?.length > 0 && (
                      <div className={s.reviewsSection}>
                        <p className={s.miniTitle}>실사용 후기 ({prodResult.reviews.length}건)</p>
                        <div className={s.reviewGrid}>
                          {prodResult.reviews.slice(0, 6).map((r, i) => (
                            <a key={i} href={r.link} target="_blank" rel="noopener noreferrer" className={s.reviewCard}>
                              <div className={s.reviewHead}>
                                <span className={s.reviewSource}>{r.source}</span>
                                <span className={s.reviewTitle}>{r.title}</span>
                              </div>
                              <p className={s.reviewText}>{r.review}</p>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 경쟁 상품 비교 */}
                    {(() => {
                      const competitors = prodResult.competitors ?? []
                      const tagged = competitors.map(c => ({
                        ...c, tier: getDynamicTier(c.price, thresholds)
                      }))
                      const filtered = prodTierFilter === '전체'
                        ? tagged
                        : tagged.filter(c => c.tier === prodTierFilter)

                      const tierCounts = TIERS.slice(1).reduce((acc, t) => {
                        acc[t] = tagged.filter(c => c.tier === t).length
                        return acc
                      }, {})

                      /* 탭에 표시할 가격 범위 */
                      const tierRange = thresholds ? {
                        '저가':  `~${fmtWon(thresholds.p25)}`,
                        '중저가': `${fmtWon(thresholds.p25)}~${fmtWon(thresholds.p50)}`,
                        '중고가': `${fmtWon(thresholds.p50)}~${fmtWon(thresholds.p75)}`,
                        '고가':  `${fmtWon(thresholds.p75)}~`,
                      } : {}

                      return (
                        <div className={s.competitorSection}>
                          <div className={s.competitorHeader}>
                            <p className={s.miniTitle}>같은 카테고리 경쟁 상품</p>
                            <div className={s.tierTabs}>
                              {TIERS.map(t => {
                                const cnt = t === '전체' ? tagged.length : tierCounts[t] ?? 0
                                const tc = TIER_COLOR[t]
                                return (
                                  <button
                                    key={t}
                                    className={`${s.tierTab} ${prodTierFilter === t ? s.tierTabActive : ''}`}
                                    style={prodTierFilter === t && tc
                                      ? { background: tc.bg, color: tc.text, borderColor: tc.text }
                                      : {}}
                                    onClick={() => setProdTierFilter(t)}
                                  >
                                    <span>{t}</span>
                                    {tierRange[t] && <span className={s.tierTabRange}>{tierRange[t]}</span>}
                                    <span className={s.tierTabCnt}>{cnt}</span>
                                  </button>
                                )
                              })}
                            </div>
                          </div>

                          {filtered.length === 0
                            ? <p className={s.noData}>해당 가격대 상품 없음</p>
                            : (
                              <div className={s.competitorGrid}>
                                {filtered.slice(0, 6).map((c, i) => {
                                  const tc = TIER_COLOR[c.tier]
                                  return (
                                    <a key={i} href={c.link} target="_blank" rel="noopener noreferrer" className={s.competitorCard}>
                                      {c.image && <img src={c.image} alt={c.title} className={s.competitorImg} />}
                                      <div className={s.competitorInfo}>
                                        <div className={s.competitorTopRow}>
                                          <p className={s.competitorBrand}>{c.brand || '브랜드 미상'}</p>
                                          {tc && (
                                            <span className={s.tierBadge} style={{ color: tc.text, background: tc.bg }}>
                                              {c.tier}
                                            </span>
                                          )}
                                        </div>
                                        <p className={s.competitorTitle}>{c.title}</p>
                                        <p className={s.competitorPrice}>{fmtWon(c.price)}</p>
                                      </div>
                                    </a>
                                  )
                                })}
                              </div>
                            )
                          }
                        </div>
                      )
                    })()}
                  </div>
                )
              })()}
            </section>

            {/* ── 리포트 푸터 ── */}
            <div className={s.reportFooter}>
              <div className={s.footerLeft}>
                <span className={s.footerBrand}>가전무쌍 B2B</span>
                <span>네이버 DataLab · 네이버 쇼핑 · Groq AI · Prophet 예측 모델</span>
              </div>
              <span>{today} · {PERIOD_LABEL[period]}</span>
            </div>
          </>
        )}
      </div>

      {/* ── 가격 알림 모달 ── */}
      {alertModal && (
        <div className={s.modalOverlay} onClick={() => setAlertModal(false)}>
          <div className={s.modalBox} onClick={e => e.stopPropagation()}>
            <div className={s.modalHead}>
              <p className={s.modalTitle}>{category} 가격 알림 설정</p>
              <button className={s.modalClose} onClick={() => setAlertModal(false)}>✕</button>
            </div>
            <p className={s.modalDesc}>현재 평균가 {fmtWon(priceSum.avg_price)} — 이 가격 이하로 떨어지면 알림</p>
            <div className={s.alertInputRow}>
              <input
                className={s.alertInput}
                type="number"
                placeholder="목표가 입력 (원)"
                value={alertPrice}
                onChange={e => setAlertPrice(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && saveAlert()}
              />
              <button className={s.alertSaveBtn} onClick={saveAlert} disabled={alertSaving}>
                {alertSaving ? '저장 중...' : '설정'}
              </button>
            </div>
            {alerts.length > 0 && (
              <div className={s.alertList}>
                <p className={s.alertListTitle}>설정된 알림</p>
                {alerts.map(a => (
                  <div key={a.alert_id} className={s.alertItem}>
                    <span className={s.alertItemCat}>{a.category}</span>
                    <span className={s.alertItemPrice}>{fmtWon(a.target_price)} 이하</span>
                    <button className={s.alertDeleteBtn} onClick={() => deleteAlert(a.alert_id)}>삭제</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
