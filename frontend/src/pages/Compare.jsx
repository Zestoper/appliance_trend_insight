import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/Compare.module.css'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'

function MiniChart({ data, uid }) {
  if (!data || data.length < 2) return <p className={styles.noData}>데이터 없음</p>

  const W = 300, H = 80, padX = 8, padTop = 18, padBot = 6
  const max = Math.max(...data.map(d => d.ratio), 1)
  const n = data.length

  const pts = data.map((d, i) => ({
    x: padX + (i / (n - 1)) * (W - padX * 2),
    y: padTop + (H - padTop - padBot) * (1 - d.ratio / max),
    xPct: (padX + (i / (n - 1)) * (W - padX * 2)) / W * 100,
    yPct: (padTop + (H - padTop - padBot) * (1 - d.ratio / max)) / H * 100,
    ratio: d.ratio,
    period: d.period,
  }))

  const line = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = `${padX},${H - padBot} ${line} ${W - padX},${H - padBot}`
  const gradId = `cmpG-${uid}`

  const isPeak = i =>
    i > 0 && i < n - 1 &&
    data[i].ratio >= data[i - 1].ratio &&
    data[i].ratio >= data[i + 1].ratio

  const xLabelIdx = data.map((_, i) => i).filter(i => i % 3 === 0)

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ width: '100%', height: `${H}px`, display: 'block' }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <polygon points={area} fill={`url(#${gradId})`} />
        <polyline points={line} fill="none" stroke="#818cf8" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {pts.map((p, i) => (isPeak(i) || i === n - 1) && (
          <circle key={i} cx={p.x} cy={p.y} r={i === n - 1 ? 4 : 3}
            fill="#6366f1" vectorEffect="non-scaling-stroke" />
        ))}
      </svg>

      {pts.map((p, i) => (isPeak(i) || i === n - 1) && (
        <div key={i} className={styles.dotLabel} style={{
          left: `${p.xPct}%`,
          top: `${p.yPct}%`,
        }}>
          {Math.round(p.ratio)}
        </div>
      ))}

      <div className={styles.xAxis}>
        {xLabelIdx.map(i => (
          <span key={i}>{data[i].period?.slice(5, 10)}</span>
        ))}
      </div>
    </div>
  )
}

function SearchSlot({ slotNum, onAdd, alreadyIds, collapsible = false, isOpen = true, onOpen }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const timerRef = useRef(null)

  const favs = (() => {
    try { return JSON.parse(localStorage.getItem('applens_favs') || '[]') }
    catch { return [] }
  })()
  const availableFavs = favs.filter(f => !alreadyIds.includes(f.id))

  useEffect(() => {
    if (!query.trim()) { setResults([]); return }
    clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setSearching(true)
      fetch(`${API_BASE}/api/naver/products?query=${encodeURIComponent(query)}&page=1&display=6`)
        .then(r => r.json())
        .then(data => { setResults(data.items ?? []); setSearching(false) })
        .catch(() => setSearching(false))
    }, 400)
    return () => clearTimeout(timerRef.current)
  }, [query])

  function pick(p) { onAdd(p); setQuery(''); setResults([]) }

  if (collapsible && !isOpen) {
    return (
      <div className={styles.slotCollapsed} onClick={onOpen}>
        <span className={styles.slotCollapsedPlus}>+</span>
        <span className={styles.slotCollapsedLabel}>제품 추가</span>
      </div>
    )
  }

  return (
    <div className={styles.slot}>
      <div className={styles.slotTop}>
        <span className={styles.slotBadge}>{slotNum}</span>
        <span className={styles.slotLabel}>제품 추가</span>
      </div>
      <div className={styles.searchWrap}>
        <svg className={styles.searchIcon} width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <circle cx="11" cy="11" r="7" /><line x1="16.5" y1="16.5" x2="22" y2="22" />
        </svg>
        <input
          className={styles.searchInput}
          placeholder="제품명 검색..."
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        {searching && <span className={styles.spinner} />}
      </div>
      <div className={styles.slotBody}>
        {results.length > 0 && (
          <ul className={styles.list}>
            {results.map(p => (
              <li key={p.id} className={styles.listItem} onClick={() => pick(p)}>
                {p.image && <img src={p.image} alt={p.title} className={styles.listImg} />}
                <div className={styles.listInfo}>
                  <p className={styles.listName}>{p.title}</p>
                  <p className={styles.listPrice}>{p.price > 0 ? `${p.price.toLocaleString()}원` : '가격 미정'}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
        {query.trim() && !searching && results.length === 0 && (
          <p className={styles.noResult}>검색 결과 없음</p>
        )}
        {!query.trim() && availableFavs.length > 0 && (
          <div className={styles.favSection}>
            <p className={styles.favTitle}>♥ 즐겨찾기</p>
            <ul className={styles.list}>
              {availableFavs.map(f => (
                <li key={f.id} className={styles.listItem} onClick={() => pick(f)}>
                  {f.image && <img src={f.image} alt={f.title} className={styles.listImg} />}
                  <div className={styles.listInfo}>
                    <p className={styles.listName}>{f.title}</p>
                    <p className={styles.listPrice}>{f.price > 0 ? `${f.price.toLocaleString()}원` : '가격 미정'}</p>
                  </div>
                  <span className={styles.addBadge}>추가</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!query.trim() && availableFavs.length === 0 && (
          <div className={styles.emptyHint}>
            <span className={styles.emptyPlus}>+</span>
            <p>검색하거나<br />♥ 즐겨찾기에서 추가</p>
          </div>
        )}
      </div>
    </div>
  )
}

function ProductCard({ product, report, loading, onRemove, isWinner }) {
  const [openSection, setOpenSection] = useState(null)

  const trendData = report?.datalab?.data ?? []
  const recentData = trendData.slice(-4)
  const trendScore = recentData.length > 0
    ? Math.round(recentData.reduce((s, d) => s + d.ratio, 0) / recentData.length)
    : null
  const datalabQuery = report?.datalab_query ?? null
  const newsItems = report?.news?.items ?? []
  const ytItems = report?.youtube?.items ?? []

  function toggle(key) {
    setOpenSection(prev => prev === key ? null : key)
  }

  return (
    <div className={styles.card}>
      <button className={styles.removeBtn} onClick={onRemove} title="제거">✕</button>

      <div className={styles.cardImgWrap}>
        {product.image
          ? <img src={product.image} alt={product.title} className={styles.cardImg} />
          : <div className={styles.cardImgFallback}>
              <svg width="52" height="52" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
            </div>
        }
      </div>

      <div className={styles.cardBody}>
        <p className={styles.cardName}>{product.title}</p>
        <p className={styles.cardPrice}>
          {product.price > 0 ? `${product.price.toLocaleString()}원` : '가격 미정'}
        </p>
      </div>

      {/* 검색 관심도 차트 */}
      <div className={styles.chartArea}>
        <div className={styles.chartHeader}>
          <span className={styles.chartLabel}>
            검색 관심도 <span className={styles.chartSub}>최근 4주 평균</span>
          </span>
          {trendScore !== null && !loading && (
            <span className={`${styles.trendScore} ${isWinner ? styles.trendScoreWinner : ''}`}>
              {isWinner && <span className={styles.winnerCrown}>▲</span>}
              {trendScore}
            </span>
          )}
        </div>
        {datalabQuery && !loading && (
          <p className={styles.chartKeyword}>"{datalabQuery}" 기준</p>
        )}
        {loading
          ? <div className={styles.chartSkeleton} />
          : <MiniChart data={trendData} uid={product.id} />
        }
      </div>

      {/* 뉴스 / 유튜브 토글 버튼 */}
      {!loading && (
        <div className={styles.metaRow}>
          <button
            className={`${styles.metaBtn} ${openSection === 'news' ? styles.metaBtnActive : ''}`}
            onClick={() => toggle('news')}
          >
            📰 뉴스 {newsItems.length}건
            <span className={styles.metaCaret}>{openSection === 'news' ? '▲' : '▼'}</span>
          </button>
          <button
            className={`${styles.metaBtn} ${openSection === 'yt' ? styles.metaBtnActive : ''}`}
            onClick={() => toggle('yt')}
          >
            ▶ YouTube {ytItems.length}개
            <span className={styles.metaCaret}>{openSection === 'yt' ? '▲' : '▼'}</span>
          </button>
        </div>
      )}

      {/* 뉴스 상세 */}
      {openSection === 'news' && newsItems.length > 0 && (
        <div className={styles.detailSection}>
          {newsItems.map((item, i) => (
            <a key={i} href={item.link} target="_blank" rel="noopener noreferrer"
              className={styles.newsItem}>
              <p className={styles.newsTitle}>{item.title}</p>
              <p className={styles.newsMeta}>
                {item.pubDate ? new Date(item.pubDate).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' }) : ''}
              </p>
            </a>
          ))}
        </div>
      )}

      {/* 유튜브 상세 */}
      {openSection === 'yt' && ytItems.length > 0 && (
        <div className={styles.detailSection}>
          {ytItems.map(item => (
            <a key={item.videoId}
              href={`https://www.youtube.com/watch?v=${item.videoId}`}
              target="_blank" rel="noopener noreferrer"
              className={styles.ytItem}>
              <img src={item.thumbnail} alt={item.title} className={styles.ytThumb} />
              <p className={styles.ytTitle}>{item.title}</p>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

// ── 메인 ─────────────────────────────────────────────────
const MAX_SLOTS = 3

const CATEGORIES = [
  { label: '에어컨',    emoji: '❄️' },
  { label: '냉장고',    emoji: '🧊' },
  { label: '세탁기',    emoji: '🫧' },
  { label: '건조기',    emoji: '🌀' },
  { label: '공기청정기', emoji: '💨' },
  { label: '로봇청소기', emoji: '🤖' },
  { label: '식기세척기', emoji: '🍽️' },
  { label: 'TV',        emoji: '📺' },
]

export default function Compare() {
  const navigate = useNavigate()

  const { isLoggedIn, token } = useAuth()

  const [list,            setList]            = useState([])
  const [reports,         setReports]         = useState([null, null, null])
  const [loading,         setLoading]         = useState([false, false, false])
  const [thirdSlotOpen,   setThirdSlotOpen]   = useState(false)
  const [aiCompare,       setAiCompare]       = useState(null)
  const [aiCmpLoading,    setAiCmpLoading]    = useState(false)
  const [activeCategory,  setActiveCategory]  = useState(null)
  const [catProducts,     setCatProducts]     = useState([])
  const [catLoading,      setCatLoading]      = useState(false)

  // 카테고리 선택 시 상품 목록 fetch
  useEffect(() => {
    if (!activeCategory) { setCatProducts([]); return }
    setCatLoading(true)
    setCatProducts([])
    fetch(`${API_BASE}/api/naver/products?query=${encodeURIComponent(activeCategory)}&page=1&display=10`)
      .then(r => r.json())
      .then(data => { setCatProducts(data.items ?? []); setCatLoading(false) })
      .catch(() => setCatLoading(false))
  }, [activeCategory])

  useEffect(() => {
    list.forEach((product, idx) => {
      if (!product) return
      setLoading(prev => { const n = [...prev]; n[idx] = true; return n })
      fetch(`${API_BASE}/api/report?query=${encodeURIComponent(product.title)}`)
        .then(r => r.json())
        .then(data => {
          setReports(prev => { const n = [...prev]; n[idx] = data; return n })
          setLoading(prev => { const n = [...prev]; n[idx] = false; return n })
        })
        .catch(() => setLoading(prev => { const n = [...prev]; n[idx] = false; return n }))
    })
  }, [list])

  // 로그인 상태이고 제품 2개 이상일 때 AI 비교 호출
  useEffect(() => {
    const filled = list.filter(Boolean)
    if (!isLoggedIn || filled.length < 2) { setAiCompare(null); return }
    setAiCmpLoading(true)
    setAiCompare(null)
    fetch(
      `${API_BASE}/api/ai-compare?q1=${encodeURIComponent(filled[0].title)}&q2=${encodeURIComponent(filled[1].title)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
      .then(r => r.json())
      .then(data => { setAiCompare(data); setAiCmpLoading(false) })
      .catch(() => setAiCmpLoading(false))
  }, [list, isLoggedIn, token])

  function add(product, idx) {
    const updated = [...list]
    updated[idx] = {
      id: product.id, title: product.title, image: product.image,
      price: product.price, brand: product.brand,
    }
    setList([...updated])
  }

  function remove(idx) {
    const pad = arr => { const a = [...arr]; while (a.length < MAX_SLOTS) a.push(null); return a }
    setList(prev   => prev.filter((_, i) => i !== idx))
    setReports(prev => pad(prev.filter((_, i) => i !== idx).map(v => v ?? null)))
    setLoading(prev => pad(prev.filter((_, i) => i !== idx).map(v => v ?? false)))
    setThirdSlotOpen(false)
  }

  const alreadyIds = list.filter(Boolean).map(p => p.id)
  const filled     = list.filter(Boolean)

  function getTrendScore(r) {
    const data = r?.datalab?.data ?? []
    const recent = data.slice(-4)
    return recent.length > 0
      ? Math.round(recent.reduce((s, d) => s + d.ratio, 0) / recent.length)
      : null
  }

  // 각 지표별 승자 인덱스 계산 (filled 기준)
  function winnerIdx(vals, mode = 'max') {
    const valid = vals.map((v, i) => ({ v, i })).filter(x => x.v !== null && x.v !== undefined)
    if (valid.length < 2) return null
    const best = mode === 'max'
      ? valid.reduce((a, b) => b.v > a.v ? b : a)
      : valid.reduce((a, b) => b.v < a.v ? b : a)
    const tied = valid.filter(x => x.v === best.v)
    return tied.length === 1 ? best.i : null
  }

  const prices    = list.map(p => p?.price > 0 ? p.price : null)
  const trends    = reports.slice(0, list.length).map(getTrendScore)
  const newsCnts  = reports.slice(0, list.length).map(r => r?.news?.items?.length ?? null)
  const ytCnts    = reports.slice(0, list.length).map(r => r?.youtube?.items?.length ?? null)

  const priceWin  = winnerIdx(prices,   'min')
  const trendWin  = winnerIdx(trends,   'max')
  const newsWin   = winnerIdx(newsCnts, 'max')
  const ytWin     = winnerIdx(ytCnts,   'max')

  const rows = [
    { label: '가격',       vals: prices,   win: priceWin,  fmt: v => `${v.toLocaleString()}원` },
    { label: '검색 관심도', vals: trends,   win: trendWin,  fmt: v => `${v} / 100` },
    { label: '최신 뉴스',  vals: newsCnts, win: newsWin,   fmt: v => `${v}건` },
    { label: 'YouTube',    vals: ytCnts,   win: ytWin,     fmt: v => `${v}개` },
  ]

  return (
    <div className={styles.page}>
      <Navbar />
      <div className={styles.container}>

        <div className={styles.header}>
          <span className={styles.breadcrumb} onClick={() => navigate('/')}>홈</span>
          <span className={styles.sep}>›</span>
          <span>제품 비교</span>
        </div>

        <div className={styles.titleRow}>
          <h1 className={styles.title}>제품 비교</h1>
          <p className={styles.subtitle}>최대 3개 제품을 나란히 비교해보세요</p>
        </div>

        {/* 카테고리 탭 */}
        <div className={styles.catSection}>
          <div className={styles.catTabs}>
            {CATEGORIES.map(c => (
              <button
                key={c.label}
                className={`${styles.catTab} ${activeCategory === c.label ? styles.catTabActive : ''}`}
                onClick={() => setActiveCategory(prev => prev === c.label ? null : c.label)}
              >
                <span>{c.emoji}</span> {c.label}
              </button>
            ))}
          </div>

          {activeCategory && (
            <div className={styles.catPickerWrap}>
              {catLoading ? (
                <div className={styles.catLoading}>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className={styles.catSkeleton} />
                  ))}
                </div>
              ) : (
                <div className={styles.catProducts}>
                  {catProducts.map(p => {
                    const alreadyAdded = list.some(l => l?.id === p.id)
                    const isFull = list.filter(Boolean).length >= MAX_SLOTS
                    return (
                      <button
                        key={p.id}
                        className={`${styles.catProductCard} ${alreadyAdded ? styles.catProductAdded : ''}`}
                        onClick={() => {
                          if (alreadyAdded || isFull) return
                          const nextIdx = list.length < MAX_SLOTS ? list.length : -1
                          if (nextIdx === -1) return
                          add(p, nextIdx)
                          if (nextIdx === 2) setThirdSlotOpen(false)
                        }}
                        disabled={alreadyAdded || isFull}
                        title={isFull && !alreadyAdded ? '최대 3개까지 비교 가능' : ''}
                      >
                        <div className={styles.catImgWrap}>
                          {p.image
                            ? <img src={p.image} alt={p.title} className={styles.catImg} />
                            : <span className={styles.catImgFallback}>📦</span>
                          }
                        </div>
                        <p className={styles.catProductName}>{p.title}</p>
                        <p className={styles.catProductPrice}>
                          {p.price > 0 ? `${p.price.toLocaleString()}원` : '가격 미정'}
                        </p>
                        {alreadyAdded
                          ? <span className={styles.catAddedBadge}>추가됨</span>
                          : <span className={styles.catAddBtn}>+ 비교 추가</span>
                        }
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 슬롯 그리드 */}
        <div className={`${styles.grid} ${list.length === 3 ? styles.grid3 : ''} ${list.filter(Boolean).length === 2 && !thirdSlotOpen ? styles.gridWithCollapsed : ''}`}>
          {Array.from({ length: Math.min(list.length + 1, MAX_SLOTS) }).map((_, idx) => {
            const product = list[idx]
            if (product) {
              return (
                <ProductCard
                  key={product.id}
                  product={product}
                  report={reports[idx]}
                  loading={loading[idx]}
                  onRemove={() => remove(idx)}
                  isWinner={trendWin === idx}
                />
              )
            }
            const isCollapsible = list.filter(Boolean).length >= 2
            return (
              <SearchSlot
                key={`slot-${idx}`}
                slotNum={idx + 1}
                onAdd={p => { add(p, idx); setThirdSlotOpen(false) }}
                alreadyIds={alreadyIds}
                collapsible={isCollapsible}
                isOpen={isCollapsible ? thirdSlotOpen : true}
                onOpen={() => setThirdSlotOpen(true)}
              />
            )
          })}
        </div>

        {/* 항목별 비교 테이블 (2개 이상 추가됐을 때) */}
        {filled.length >= 2 && (
          <div className={styles.summary}>
            <h2 className={styles.summaryTitle}>항목별 비교</h2>

            <div className={styles.cmpTable} style={{ '--cols': list.length }}>
              {/* 헤더 */}
              <div className={styles.cmpHead}>
                <span className={styles.cmpRowLabel} />
                {list.map((p, i) => (
                  <span key={i} className={styles.cmpHeadCell}>
                    {p?.brand || `제품 ${i + 1}`}
                  </span>
                ))}
              </div>

              {/* 데이터 행 */}
              {rows.map(row => (
                <div key={row.label} className={styles.cmpRow}>
                  <span className={styles.cmpRowLabel}>{row.label}</span>
                  {list.map((_, i) => {
                    const v = row.vals[i]
                    return (
                      <span
                        key={i}
                        className={`${styles.cmpCell} ${row.win === i ? styles.winner : ''}`}
                      >
                        {v !== null && v !== undefined ? row.fmt(v) : '—'}
                        {row.win === i && <span className={styles.winIcon}>★</span>}
                      </span>
                    )
                  })}
                </div>
              ))}
            </div>

            {/* 가격 요약 */}
            {priceWin !== null && (() => {
              const cheapest = list[priceWin]
              const others   = list.filter((_, i) => i !== priceWin && list[i]?.price > 0)
              const maxOther = Math.max(...others.map(p => p.price))
              const diff     = maxOther - cheapest.price
              return diff > 0 ? (
                <p className={styles.priceDiff}>
                  {cheapest.brand || `제품 ${priceWin + 1}`}이 가장 저렴해요 —
                  최대 {diff.toLocaleString()}원 차이
                </p>
              ) : null
            })()}
          </div>
        )}

        {/* AI 비교 분석 섹션 */}
        {filled.length >= 2 && (
          isLoggedIn ? (
            <div className={styles.aiSection}>
              <div className={styles.aiHeader}>
                <span className={styles.aiBadge}>AI</span>
                <h2 className={styles.aiTitle}>AI 비교 분석</h2>
                <span className={styles.aiPowered}>powered by Groq</span>
              </div>

              {aiCmpLoading && (
                <div className={styles.aiLoading}>
                  <div className={styles.aiSpinner} />
                  <span>AI가 두 제품을 분석 중이에요...</span>
                </div>
              )}

              {aiCompare && !aiCmpLoading && (
                <>
                  <div className={styles.winnerBanner}>
                    <span className={styles.winnerBannerLabel}>추천 제품</span>
                    <p className={styles.winnerBannerName}>
                      {filled[aiCompare.winner]?.title}
                    </p>
                    <p className={styles.winnerBannerReason}>{aiCompare.winner_reason}</p>
                  </div>

                  <div className={styles.aiGrid}>
                    {aiCompare.products.map((p, i) => (
                      <div
                        key={i}
                        className={`${styles.aiCard} ${aiCompare.winner === i ? styles.aiCardWinner : ''}`}
                      >
                        <div className={styles.aiCardTop}>
                          {aiCompare.winner === i && (
                            <span className={styles.crownBadge}>👑 추천</span>
                          )}
                          <p className={styles.aiProductName}>{filled[i]?.title}</p>
                          <div className={styles.aiScoreRow}>
                            <span className={styles.aiScoreNum}>{p.score}</span>
                            <span className={styles.aiScoreMax}> / 5</span>
                          </div>
                        </div>
                        <p className={styles.aiSummary}>{p.summary}</p>
                        <div className={styles.prosConsGrid}>
                          <div className={styles.prosList}>
                            <span className={styles.prosLabel}>장점</span>
                            <ul className={styles.pcUl}>
                              {p.pros.map((item, j) => <li key={j}>{item}</li>)}
                            </ul>
                          </div>
                          <div className={styles.consList}>
                            <span className={styles.consLabel}>단점</span>
                            <ul className={styles.pcUl}>
                              {p.cons.map((item, j) => <li key={j}>{item}</li>)}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className={styles.verdict}>
                    <span className={styles.verdictLabel}>AI 종합 의견</span>
                    <p className={styles.verdictText}>{aiCompare.verdict}</p>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className={styles.aiGate}>
              <span className={styles.aiGateIcon}>🔒</span>
              <p className={styles.aiGateTitle}>AI 비교는 회원 전용이에요</p>
              <p className={styles.aiGateSub}>로그인하면 두 제품을 AI로 비교해볼 수 있어요</p>
              <button className={styles.aiGateBtn} onClick={() => navigate('/login')}>
                로그인하기 →
              </button>
            </div>
          )
        )}

      </div>
    </div>
  )
}
