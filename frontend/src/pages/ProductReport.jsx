import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/ProductReport.module.css'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'

function fmtDate(str) {
  try {
    return new Date(str).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  } catch {
    return str
  }
}

// 뽐뿌 날짜 "26/06/11" → "6월 11일"
function fmtShortDate(str) {
  if (!str) return ''
  const parts = str.split('/')
  if (parts.length !== 3) return str
  const [, m, d] = parts
  return `${parseInt(m)}월 ${parseInt(d)}일`
}

function getTrendMessage(data) {
  if (!data || data.length < 4) return null
  const half = Math.floor(data.length / 2)
  const avg = arr => arr.reduce((s, d) => s + d.ratio, 0) / arr.length
  const diff = avg(data.slice(half)) - avg(data.slice(0, half))
  if (diff > 8) return { icon: '↑', label: '관심도 상승 중', desc: '최근 검색량이 늘고 있어요', type: 'up' }
  if (diff < -8) return { icon: '↓', label: '관심도 하락 중', desc: '지금 구매하면 가격 협상에 유리해요', type: 'down' }
  return { icon: '→', label: '관심도 안정적', desc: '꾸준한 인기 제품이에요', type: 'stable' }
}

function TrendChart({ data }) {
  if (!data || data.length < 2) {
    return <p className={styles.noData}>트렌드 데이터 없음</p>
  }

  const W = 400, H = 120
  const padX = 8, padY = 12
  const maxRatio = Math.max(...data.map(d => d.ratio), 1)

  const pts = data.map((d, i) => {
    const x = padX + (i / (data.length - 1)) * (W - padX * 2)
    const y = padY + (H - padY * 2) * (1 - d.ratio / maxRatio)
    return [x, y]
  })

  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${padX},${H - padY} ${line} ${W - padX},${H - padY}`
  const [dotX, dotY] = pts[pts.length - 1]

  const labelIdx = data.length <= 7
    ? data.map((_, i) => i)
    : [0, Math.floor(data.length / 2), data.length - 1]

  const midRatio = Math.round(maxRatio / 2)

  return (
    <div className={styles.chartWrap}>
      <div className={styles.chartInner}>
        <div className={styles.chartYAxis}>
          <span>{Math.round(maxRatio)}</span>
          <span>{midRatio}</span>
          <span>0</span>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            style={{ width: '100%', height: '120px', display: 'block' }}
          >
            <defs>
              <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity="0.28" />
                <stop offset="100%" stopColor="#6366f1" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            <line x1={padX} y1={padY} x2={W - padX} y2={padY} stroke="rgba(255,255,255,0.06)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <line x1={padX} y1={H / 2} x2={W - padX} y2={H / 2} stroke="rgba(255,255,255,0.06)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <line x1={padX} y1={H - padY} x2={W - padX} y2={H - padY} stroke="rgba(255,255,255,0.06)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <polygon points={area} fill="url(#trendFill)" />
            <polyline
              points={line}
              fill="none"
              stroke="#818cf8"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
            <circle cx={dotX} cy={dotY} r="8" fill="rgba(99,102,241,0.2)" vectorEffect="non-scaling-stroke" />
            <circle cx={dotX} cy={dotY} r="3.5" fill="#6366f1" vectorEffect="non-scaling-stroke" />
          </svg>
          <div className={styles.chartXAxis}>
            {labelIdx.map(i => (
              <span key={i}>{data[i].period.slice(5)}</span>
            ))}
          </div>
          <p className={styles.chartDesc}>최근 30일 · 네이버 검색 관심도 기준 (최고점 = 100)</p>
        </div>
      </div>
    </div>
  )
}

function NewsList({ items }) {
  if (!items.length) return <p className={styles.noData}>관련 뉴스 없음</p>
  return (
    <div className={styles.newsList}>
      {items.map((item, i) => (
        <a key={i} href={item.link} target="_blank" rel="noopener noreferrer" className={styles.newsItem}>
          <p className={styles.newsTitle}>{item.title}</p>
          <p className={styles.newsMeta}>{fmtDate(item.pubDate)}</p>
        </a>
      ))}
    </div>
  )
}

function YtList({ items }) {
  if (!items.length) return <p className={styles.noData}>유튜브 영상 없음</p>
  return (
    <div className={styles.ytList}>
      {items.map(item => (
        <a
          key={item.videoId}
          href={`https://www.youtube.com/watch?v=${item.videoId}`}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.ytCard}
        >
          <div className={styles.ytThumb}>
            <img src={item.thumbnail} alt={item.title} className={styles.ytThumbImg} />
            <span className={styles.ytPlay}>▶</span>
          </div>
          <div className={styles.ytInfo}>
            <p className={styles.ytTitle}>{item.title}</p>
            <p className={styles.ytMeta}>{item.channelTitle} · {item.publishedAt}</p>
            {item.transcript && (
              <p className={styles.ytTranscript}>"{item.transcript.slice(0, 70)}..."</p>
            )}
          </div>
        </a>
      ))}
    </div>
  )
}

// ── 뽐뿌 커뮤니티 목록 ───────────────────────────────────
function CommunityList({ items }) {
  if (!items.length) return <p className={styles.noData}>커뮤니티 데이터 없음</p>
  return (
    <div className={styles.postGrid}>
      {items.map((item, i) => (
        <a key={i} href={item.link} target="_blank" rel="noopener noreferrer" className={styles.postItem}>
          <p className={styles.postTitle}>{item.title}</p>
          <div className={styles.postMeta}>
            <span>{fmtShortDate(item.date)}</span>
            {parseInt(item.commentCount) > 0 && (
              <span className={styles.commentBadge}>댓글 {item.commentCount}</span>
            )}
          </div>
        </a>
      ))}
    </div>
  )
}

function ScoreDots({ score }) {
  const filled = Math.round(score)
  return (
    <span className={styles.scoreDots}>
      {[1,2,3,4,5].map(i => (
        <span key={i} className={i <= filled ? styles.dotFilled : styles.dotEmpty} />
      ))}
    </span>
  )
}

function AiAnalysis({ data, loading }) {
  if (loading) return (
    <div className={styles.aiLoadingWrap}>
      <div className={styles.aiSpinner} />
      <p>쿠팡 리뷰 수집 · AI 분석 중...</p>
    </div>
  )
  if (!data?.analysis) return null

  const { analysis, reviews } = data
  return (
    <>
      <div className={`${styles.section} ${styles.sectionAI}`}>
        <div className={styles.sectionHead}>
          <h2 className={styles.sectionTitle}>AI 구매 리포트</h2>
          <span className={styles.aiBadge}>AI POWERED</span>
        </div>

        <div className={styles.aiScoreRow}>
          <div className={styles.aiScoreLeft}>
            <span className={styles.aiScoreNum}>{analysis.score?.toFixed(1)}</span>
            <span className={styles.aiScoreMax}>/5</span>
          </div>
          <div className={styles.aiScoreRight}>
            <ScoreDots score={analysis.score ?? 0} />
            {analysis.summary && <p className={styles.aiSummary}>{analysis.summary}</p>}
          </div>
        </div>

        {analysis.recall && (
          <div className={styles.recallBanner}>
            ⚠️ 리콜 이력 있음 — 최신 뉴스를 확인해주세요
          </div>
        )}

        {analysis.defects?.length > 0 && (
          <div className={styles.defectBanner}>
            <span className={styles.defectIcon}>!</span>
            <div>
              <p className={styles.defectTitle}>반복 언급 결함</p>
              <ul className={styles.defectList}>
                {analysis.defects.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </div>
          </div>
        )}

        <div className={styles.prosCons}>
          {analysis.pros?.length > 0 && (
            <div className={styles.prosCol}>
              <p className={styles.colLabel}>장점</p>
              <ul className={styles.proList}>
                {analysis.pros.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </div>
          )}
          {analysis.cons?.length > 0 && (
            <div className={styles.consCol}>
              <p className={styles.colLabel}>단점</p>
              <ul className={styles.conList}>
                {analysis.cons.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
        </div>

        {/* 추천 대상 */}
        {analysis.suitable_for && (
          <div className={styles.suitableFor}>
            <span className={styles.suitableIcon}>👤</span>
            <div>
              <p className={styles.suitableLabel}>이런 분께 추천</p>
              <p className={styles.suitableText}>{analysis.suitable_for}</p>
            </div>
          </div>
        )}

        {/* 구매 주의사항 */}
        {analysis.cautions?.length > 0 && (
          <div className={styles.cautionWrap}>
            <p className={styles.cautionTitle}>구매 시 주의사항</p>
            <ul className={styles.cautionList}>
              {analysis.cautions.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* 실사용자 후기 */}
      {reviews?.length > 0 && (
        <div className={`${styles.section} ${styles.sectionCoupang}`}>
          <div className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>실사용자 후기</h2>
            <span className={styles.reviewCount2}>{reviews.length}개</span>
          </div>
          <div className={styles.reviewGrid}>
            {reviews.map((rv, i) => (
              <a
                key={i}
                href={rv.link}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.reviewCard}
                style={{ textDecoration: 'none', color: 'inherit', display: 'flex', flexDirection: 'column', gap: '6px' }}
              >
                <div className={styles.reviewTop}>
                  <span className={styles.reviewSource}>{rv.source}</span>
                  <span className={styles.reviewDate}>{rv.date?.slice(0,4)}.{rv.date?.slice(4,6)}.{rv.date?.slice(6,8)}</span>
                </div>
                <p className={styles.reviewTitle}>{rv.title}</p>
                <p className={styles.reviewBody}>{rv.review}</p>
              </a>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

// ── 제품별 가격 인텔리전스 ────────────────────────────────
function fmtP(p) {
  if (!p && p !== 0) return '-'
  if (p >= 10000) return `${Math.round(p / 10000).toLocaleString()}만원`
  return `${p.toLocaleString()}원`
}

function MiniPriceChart({ history }) {
  if (!history || history.length < 2) return null
  const W = 300, H = 48, padX = 4, padY = 4
  const vals = history.map(h => h.min_price)
  const minV = Math.min(...vals), maxV = Math.max(...vals, minV + 1)
  const pts = vals.map((v, i) => ({
    x: padX + (i / (vals.length - 1)) * (W - padX * 2),
    y: padY + (H - padY * 2) * (1 - (v - minV) / (maxV - minV)),
  }))
  const line = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = `${padX},${H - padY} ${line} ${W - padX},${H - padY}`
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: 48 }}>
      <defs>
        <linearGradient id="ppGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#22c55e" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#22c55e" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#ppGrad)" />
      <polyline points={line} fill="none" stroke="#22c55e" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function ProductPriceIntel({ title, token }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!title || !token) { setLoading(false); return }
    fetch(`${API_BASE}/api/b2b/product-price?title=${encodeURIComponent(title)}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [title, token])

  if (loading) return (
    <div className={`${styles.section} ${styles.sectionPt}`}>
      <div className={styles.ptLoadingRow}>
        <div className={styles.ptSpinner} />
        <span>멀티몰 가격 수집 중...</span>
      </div>
    </div>
  )

  if (!data?.available) return null

  const {
    model_number, min_price, avg_price, hist_avg_price, hist_min_price,
    cheapest_mall, cheapest_link, malls, price_history,
    signal, signal_type, reason, snapshot_date,
  } = data

  const signalCls =
    signal_type === 'buy'  ? styles.ptBuy  :
    signal_type === 'wait' ? styles.ptWait :
    styles.ptNeutral

  const icon =
    signal_type === 'buy'  ? '✅' :
    signal_type === 'wait' ? '⏸️' : 'ℹ️'

  return (
    <div className={`${styles.section} ${styles.sectionPt}`}>
      <div className={styles.ptHeader}>
        <div>
          <h2 className={styles.sectionTitle}>가격 인텔리전스</h2>
          {model_number && (
            <span className={styles.ptModel}>모델번호 자동감지: {model_number}</span>
          )}
        </div>
        <span className={`${styles.ptSignal} ${signalCls}`}>{signal}</span>
      </div>

      {/* 핵심 지표 3개 */}
      <div className={styles.ptStats}>
        <div className={styles.ptStat}>
          <span className={styles.ptStatLabel}>현재 최저가</span>
          <span className={`${styles.ptStatValue} ${styles.ptStatGreen}`}>{fmtP(min_price)}</span>
          <span className={styles.ptStatSub}>{cheapest_mall}</span>
        </div>
        <div className={styles.ptStatDiv} />
        <div className={styles.ptStat}>
          <span className={styles.ptStatLabel}>누적 평균가</span>
          <span className={styles.ptStatValue}>{fmtP(hist_avg_price)}</span>
          <span className={styles.ptStatSub}>전체 기간 평균</span>
        </div>
        <div className={styles.ptStatDiv} />
        <div className={styles.ptStat}>
          <span className={styles.ptStatLabel}>누적 최저가</span>
          <span className={styles.ptStatValue}>{fmtP(hist_min_price)}</span>
          <span className={styles.ptStatSub}>역대 최저</span>
        </div>
      </div>

      {/* 멀티몰 가격 비교 */}
      <div className={styles.ptMallSection}>
        <p className={styles.ptMallTitle}>쇼핑몰별 현재가</p>
        <div className={styles.ptMallList}>
          {malls.map((m, i) => {
            const isMin = m.price === min_price
            return (
              <div key={i} className={`${styles.ptMallRow} ${isMin ? styles.ptMallRowBest : ''}`}>
                <span className={styles.ptMallName}>{m.mall}</span>
                <span className={`${styles.ptMallPrice} ${isMin ? styles.ptStatGreen : ''}`}>
                  {fmtP(m.price)}
                </span>
                {isMin && <span className={styles.ptBestTag}>최저</span>}
              </div>
            )
          })}
        </div>
      </div>

      {/* 가격 추이 미니 차트 */}
      {price_history.length >= 2 && (
        <div className={styles.ptChartSection}>
          <p className={styles.ptMallTitle}>최저가 추이 ({price_history.length}일)</p>
          <MiniPriceChart history={price_history} />
          <div className={styles.ptChartLabels}>
            <span>{price_history[0]?.date?.slice(5)}</span>
            <span>{price_history[price_history.length - 1]?.date?.slice(5)}</span>
          </div>
        </div>
      )}

      {/* 구매 신호 */}
      <div className={styles.ptReason}>
        <span>{icon}</span>
        <p>{reason}</p>
      </div>

      {cheapest_link && (
        <a href={cheapest_link} target="_blank" rel="noopener noreferrer"
          className={styles.ptBuyLink}>
          {cheapest_mall}에서 {fmtP(min_price)}에 구매하기 →
        </a>
      )}

      <p className={styles.ptNote}>{snapshot_date} 기준 · 네이버 쇼핑 실시간 데이터</p>
    </div>
  )
}

// ── 로그인 게이트 ─────────────────────────────────────────
function AiLoginGate({ onLogin }) {
  return (
    <div className={styles.aiGate}>
      <div className={styles.aiGateBlur}>
        <div className={styles.aiGateFakeRow}><span /><span /><span /></div>
        <div className={styles.aiGateFakeRow}><span /><span /></div>
        <div className={styles.aiGateFakeRow}><span /><span /><span /><span /></div>
      </div>
      <div className={styles.aiGateOverlay}>
        <div className={styles.aiGateIcon}>🔒</div>
        <p className={styles.aiGateTitle}>로그인 후 AI 리포트를 볼 수 있어요</p>
        <p className={styles.aiGateSub}>장점 · 단점 · 추천도를 AI가 분석해드려요</p>
        <button className={styles.aiGateBtn} onClick={onLogin}>로그인하기 →</button>
      </div>
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────
export default function ProductReport() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { isLoggedIn, token, user } = useAuth()
  // ProductList에서 navigate(`/report/${id}`, { state: { product, category } })로 전달한 데이터
  const product  = state?.product
  const category = state?.category ?? '제품'

  const [reportData,    setReportData]    = useState(null)
  const [reportLoading, setReportLoading] = useState(true)
  const [aiData,        setAiData]        = useState(null)
  const [aiLoading,     setAiLoading]     = useState(true)
  const [isFav, setIsFav] = useState(() => {
    try {
      const favs = JSON.parse(localStorage.getItem('applens_favs') || '[]')
      return favs.some(f => f.id === product?.id)
    } catch { return false }
  })
  const [copied,       setCopied]       = useState(false)
  const [alertOpen,    setAlertOpen]    = useState(false)
  const [alertPrice,   setAlertPrice]   = useState('')
  const [alertLoading, setAlertLoading] = useState(false)
  const [alertDone,    setAlertDone]    = useState(false)

  useEffect(() => {
    if (!product) return
    // 두 API 병렬 호출
    fetch(`${API_BASE}/api/report?query=${encodeURIComponent(product.title)}`)
      .then(r => r.json())
      .then(data => { setReportData(data); setReportLoading(false) })
      .catch(() => setReportLoading(false))

    fetch(`${API_BASE}/api/ai-analysis?query=${encodeURIComponent(product.title)}`)
      .then(r => r.json())
      .then(data => { setAiData(data); setAiLoading(false) })
      .catch(() => setAiLoading(false))
  }, [])

  // product가 없으면 (직접 URL 접근 등) 안내 화면
  if (!product) {
    return (
      <div className={styles.page}>
        <Navbar />
        <div className={styles.notFound}>
          <p>제품 정보를 찾을 수 없습니다.</p>
          <button className={styles.backBtn} onClick={() => navigate(-1)}>← 돌아가기</button>
        </div>
      </div>
    )
  }

  const trendData      = reportData?.datalab?.data   ?? []
  const newsItems      = reportData?.news?.items     ?? []
  const ytItems        = reportData?.youtube?.items  ?? []
  const ppomppuItems   = reportData?.ppomppu?.items  ?? []
  const name           = product.title ?? product.name ?? '제품명 없음'
  const currentTrend   = trendData.length > 0
    ? Math.round(trendData[trendData.length - 1].ratio)
    : null
  const trendMsg = getTrendMessage(trendData)

  function toggleFav() {
    try {
      const favs = JSON.parse(localStorage.getItem('applens_favs') || '[]')
      const updated = isFav
        ? favs.filter(f => f.id !== product.id)
        : [...favs, { id: product.id, title: product.title, image: product.image, price: product.price, category }]
      localStorage.setItem('applens_favs', JSON.stringify(updated))
      setIsFav(!isFav)
    } catch {}
  }

  function handleShare() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function handleCreateAlert() {
    const price = Number(alertPrice.replace(/,/g, ''))
    if (!price || price <= 0) return
    setAlertLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/user/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          product_name:  product.title,
          target_price:  price,
          current_price: product.price ?? 0,
          product_url:   product.link ?? '',
          alert_type:    'below',
        }),
      })
      if (res.status === 409) { setAlertDone('dup'); return }
      if (!res.ok) throw new Error()
      setAlertDone('ok')
    } catch {
      setAlertDone('err')
    } finally {
      setAlertLoading(false)
    }
  }

  return (
    <div className={styles.page} data-scroll-container>
      <Navbar />
      <div className={styles.container}>

        {/* 브레드크럼: 홈 › 카테고리 › 제품명 */}
        <div className={styles.breadcrumb}>
          <span className={styles.breadcrumbLink} onClick={() => navigate('/')}>홈</span>
          <span className={styles.sep}>›</span>
          <span className={styles.breadcrumbLink} onClick={() => navigate(`/products/${category}`)}>{category}</span>
          <span className={styles.sep}>›</span>
          <span className={styles.breadcrumbTail}>{name}</span>
        </div>

        {/* ① 히어로 */}
        <div className={styles.hero}>
          {product.image && (
            <div className={styles.heroImgWrap}>
              <img src={product.image} alt={name} className={styles.heroImg} />
            </div>
          )}
          <div className={styles.heroInfo}>
            <div className={styles.heroTop}>
              {product.brand && <span className={styles.brandTag}>{product.brand}</span>}
              <div className={styles.actionRow}>
                <button
                  className={`${styles.actionBtn} ${isFav ? styles.actionBtnActive : ''}`}
                  onClick={toggleFav}
                  title={isFav ? '저장 취소' : '관심 제품 저장'}
                >
                  {isFav ? '♥' : '♡'}
                </button>
                <button className={styles.actionBtn} onClick={handleShare} title="링크 복사">
                  {copied ? '✓' : '⎙'}
                </button>
              </div>
            </div>
            <h1 className={styles.heroName}>{name}</h1>
            {product.mallName && <p className={styles.mallName}>{product.mallName}</p>}
            {product.reviewScore > 0 && (
              <div className={styles.reviewRow}>
                <span className={styles.stars}>
                  {'★'.repeat(Math.round(product.reviewScore))}{'☆'.repeat(5 - Math.round(product.reviewScore))}
                </span>
                <span className={styles.reviewScore}>{product.reviewScore.toFixed(1)}</span>
                {product.reviewCount > 0 && (
                  <span className={styles.reviewCount}>({product.reviewCount.toLocaleString()}개)</span>
                )}
              </div>
            )}
            <div className={styles.heroPriceArea}>
              <p className={styles.heroPriceLabel}>현재가</p>
              <div className={styles.heroPriceRow}>
                <p className={styles.heroPrice}>
                  {product.price > 0 ? `${product.price.toLocaleString()}원` : '가격 미정'}
                </p>
                {isLoggedIn && product.price > 0 && (
                  <button
                    className={styles.alertBtn}
                    onClick={() => { setAlertOpen(true); setAlertDone(false); setAlertPrice('') }}
                    title="가격 알림 설정"
                  >
                    🔔 가격 알림
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 제품별 가격 인텔리전스 — B2B 유저 전용 */}
        {user?.user_type === 'b2b' && user?.status === 'active' && (
          <ProductPriceIntel title={product.title} token={token} />
        )}

        {/* 수집 중 로딩 표시 — 완료되면 사라지고 데이터 섹션이 나타남 */}
        {reportLoading && (
          <div className={styles.loadingBlock}>
            <div className={styles.loadingSpinner} />
            <p>뉴스·트렌드·유튜브·뽐뿌 데이터 수집 중...</p>
          </div>
        )}

        {/* AI 구매 리포트 + 쿠팡 리뷰 */}
        {isLoggedIn
          ? <AiAnalysis data={aiData} loading={aiLoading} />
          : <AiLoginGate onLogin={() => navigate('/login')} />
        }

        {/* ② 데이터 랩 — 2개 이상 포인트가 있을 때만 표시 */}
        {!reportLoading && trendData.length >= 2 && (
          <div className={`${styles.section} ${styles.sectionTrend}`}>
            <div className={styles.sectionHead}>
              <h2 className={styles.sectionTitle}>검색 관심도 트렌드</h2>
              {currentTrend !== null && (
                <div className={styles.trendScore}>
                  <span className={styles.trendScoreLabel}>최근 관심도&nbsp;</span>
                  <span className={styles.trendScoreNum}>{currentTrend}</span>
                  <span className={styles.trendScoreLabel}>&nbsp;/ 100</span>
                </div>
              )}
            </div>
            <TrendChart data={trendData} />
            {trendMsg && (
              <div className={`${styles.trendMsg} ${styles[`trendMsg_${trendMsg.type}`]}`}>
                <span className={styles.trendMsgIcon}>{trendMsg.icon}</span>
                <div>
                  <p className={styles.trendMsgLabel}>{trendMsg.label}</p>
                  <p className={styles.trendMsgDesc}>{trendMsg.desc}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ③ 뉴스 + YouTube — 있는 것만, 둘 다 있으면 2열 */}
        {!reportLoading && (newsItems.length > 0 || ytItems.length > 0) && (
          <div className={newsItems.length > 0 && ytItems.length > 0 ? styles.twoCol : undefined}>
            {newsItems.length > 0 && (
              <div className={`${styles.section} ${styles.sectionNews}`}>
                <div className={styles.sectionHead}>
                  <h2 className={styles.sectionTitle}>최신 뉴스</h2>
                </div>
                <NewsList items={newsItems} />
              </div>
            )}
            {ytItems.length > 0 && (
              <div className={`${styles.section} ${styles.sectionYt}`}>
                <div className={styles.sectionHead}>
                  <h2 className={styles.sectionTitle}>리뷰 영상</h2>
                </div>
                <YtList items={ytItems} />
              </div>
            )}
          </div>
        )}

        {/* 로딩 완료 후 모든 섹션이 비어있을 때 */}
        {!reportLoading && trendData.length < 2 && newsItems.length === 0 && ytItems.length === 0 && ppomppuItems.length === 0 && (
          <div className={styles.emptyState}>
            <p className={styles.emptyIcon}>📭</p>
            <p className={styles.emptyTitle}>아직 분석 데이터가 없는 제품이에요</p>
            <p className={styles.emptyDesc}>검색량이 적거나 출시 초기 제품은 데이터가 수집되지 않을 수 있어요</p>
          </div>
        )}

        {/* ④ 뽐뿌 — 데이터 있을 때만 표시 */}
        {!reportLoading && ppomppuItems.length > 0 && (
          <div className={`${styles.section} ${styles.sectionComm}`}>
            <div className={styles.sectionHead}>
              <h2 className={styles.sectionTitle}>커뮤니티 반응</h2>
            </div>
            <CommunityList items={ppomppuItems} />
          </div>
        )}

        {/* ⑤ 구매 버튼 */}
        <div className={styles.section}>
          <div className={styles.buyRow}>
            <button
              className={`${styles.buyBtn} ${styles.buyNaver}`}
              onClick={() => product.link && window.open(product.link, '_blank')}
            >
              네이버 쇼핑에서 구매하기 →
            </button>
            <button
              className={`${styles.buyBtn} ${styles.buyCoupang}`}
              onClick={() => window.open(`https://www.coupang.com/np/search?q=${encodeURIComponent(name)}`, '_blank')}
            >
              쿠팡에서 구매하기 →
            </button>
          </div>
        </div>

      </div>

      {/* 가격 알림 모달 */}
      {alertOpen && (
        <div className={styles.modalOverlay} onClick={() => setAlertOpen(false)}>
          <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
            <button className={styles.modalClose} onClick={() => setAlertOpen(false)}>✕</button>
            <p className={styles.modalTitle}>🔔 가격 알림 설정</p>
            <p className={styles.modalSub}>현재가: <strong>{product.price.toLocaleString()}원</strong></p>

            {!alertDone ? (
              <>
                <p className={styles.modalLabel}>목표 가격 (이 가격 이하가 되면 알려드려요)</p>
                <input
                  className={styles.modalInput}
                  type="text"
                  placeholder="예: 900000"
                  value={alertPrice}
                  onChange={e => setAlertPrice(e.target.value.replace(/[^0-9]/g, ''))}
                  onKeyDown={e => e.key === 'Enter' && handleCreateAlert()}
                  autoFocus
                />
                {alertPrice && (
                  <p className={styles.modalHint}>
                    {Number(alertPrice).toLocaleString()}원 이하일 때 알림
                  </p>
                )}
                <button
                  className={styles.modalBtn}
                  disabled={!alertPrice || alertLoading}
                  onClick={handleCreateAlert}
                >
                  {alertLoading ? '등록 중...' : '알림 등록'}
                </button>
              </>
            ) : (
              <div className={styles.modalResult}>
                {alertDone === 'ok'  && <><p className={styles.modalResultIcon}>✅</p><p>알림이 등록됐습니다!<br/><span>마이페이지에서 확인할 수 있어요</span></p></>}
                {alertDone === 'dup' && <><p className={styles.modalResultIcon}>⚠️</p><p>이미 등록된 알림이에요</p></>}
                {alertDone === 'err' && <><p className={styles.modalResultIcon}>❌</p><p>오류가 발생했습니다. 다시 시도해주세요</p></>}
                <button className={styles.modalBtn} onClick={() => setAlertOpen(false)}>닫기</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
