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
      fetch(`${API_BASE}/api/naver/products?query=${encodeURIComponent(query)}&page=1&display=15`)
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

const FILTER_GROUPS = [
  {
    key: 'product',
    label: '제품',
    options: ['에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기', 'TV', '전자레인지', '에어프라이어', '선풍기', '가습기', '제습기'],
  },
  {
    key: 'brand',
    label: '브랜드',
    options: ['삼성', 'LG', '캐리어', '위닉스', '다이슨', '로보락', '에코백스', '코웨이', '쿠쿠', '위니아', '샤오미', '파나소닉'],
  },
  {
    key: 'price',
    label: '가격',
    options: ['~5만원', '5~20만원', '20~50만원', '50~80만원', '80만원~'],
    ranges: [[0, 50000], [50000, 200000], [200000, 500000], [500000, 800000], [800000, Infinity]],
  },
  {
    key: 'sort',
    label: '정렬',
    options: ['관련순', '가격 낮은순', '가격 높은순', '최신순'],
    sortMap: { '관련순': 'sim', '가격 낮은순': 'asc', '가격 높은순': 'dsc', '최신순': 'date' },
  },
]

const PRODUCT_SUBTYPES = {
  '에어컨':    ['벽걸이형', '스탠드형', '창문형', '2in1'],
  '냉장고':    ['일반형', '양문형', '4도어', '소형/미니'],
  '세탁기':    ['드럼', '통돌이', '미니세탁기'],
  '건조기':    ['히트펌프', '콘덴서', '가스'],
  '공기청정기':['스탠드형', '소형', '벽걸이형', '차량용'],
  '로봇청소기':['일반형', '물걸레겸용', '올인원', '스테이션형'],
  '식기세척기':['빌트인', '일반형', '미니/소형'],
  'TV':        ['OLED', 'QLED', '일반 LED', '미니LED', '포터블'],
  '전자레인지': ['단독형', '오븐겸용', '스팀겸용'],
  '에어프라이어':['소형(1~3L)', '중형(4~6L)', '대형(7L+)', '오븐형'],
  '선풍기':    ['일반형', '탑 팬', '스탠드형', '서큘레이터'],
  '가습기':    ['초음파식', '가열식', '기화식', '복합형'],
  '제습기':    ['소형', '중형', '대형'],
}

export default function Compare() {
  const navigate = useNavigate()

  const { isLoggedIn, token } = useAuth()

  const [list,            setList]            = useState([])
  const [reports,         setReports]         = useState([null, null, null])
  const [loading,         setLoading]         = useState([false, false, false])
  const [thirdSlotOpen,   setThirdSlotOpen]   = useState(false)
  const [aiCompare,       setAiCompare]       = useState(null)
  const [aiCmpLoading,    setAiCmpLoading]    = useState(false)
  const [filters,         setFilters]         = useState({ product: null, brand: null, price: null, sort: null, subtype: null })
  const [catProducts,     setCatProducts]     = useState([])
  const [catLoading,      setCatLoading]      = useState(false)
  const [catMismatch,     setCatMismatch]     = useState(null)  // { current, incoming }

  // 필터 조합으로 상품 목록 fetch
  useEffect(() => {
    const { product, brand, price, sort, subtype } = filters
    if (!product && !brand && !price) { setCatProducts([]); return }

    // 검색어: 브랜드 + 세부타입 + 제품 조합
    const query = [brand, subtype, product].filter(Boolean).join(' ') || '가전제품'
    const sortKey = FILTER_GROUPS.find(g => g.key === 'sort')?.sortMap?.[sort] ?? 'sim'

    setCatLoading(true)
    setCatProducts([])

    fetch(`${API_BASE}/api/naver/products?query=${encodeURIComponent(query)}&page=1&display=100&sort=${sortKey}`)
      .then(r => r.json())
      .then(data => {
        let items = data.items ?? []
        if (price) {
          const priceGroup = FILTER_GROUPS.find(g => g.key === 'price')
          const priceIdx = priceGroup.options.indexOf(price)
          if (priceIdx !== -1) {
            const [min, max] = priceGroup.ranges[priceIdx]
            items = items.filter(p => p.price > 0 && p.price >= min && p.price < max)
          }
        }
        // 정렬이 가격순이면 이미 API에서 정렬됨, 아니면 클라이언트 유지
        setCatProducts(items.slice(0, 30))
        setCatLoading(false)
      })
      .catch(() => setCatLoading(false))
  }, [filters])

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

  // 현재 비교 중인 카테고리 (카테고리 있는 첫 제품 기준)
  const compareCategory = list.filter(Boolean).map(p => p.category).find(Boolean) ?? null

  function add(product, idx, category = null) {
    // 카테고리 불일치 체크
    if (category && compareCategory && category !== compareCategory) {
      setCatMismatch({ current: compareCategory, incoming: category })
      return
    }
    const updated = [...list]
    updated[idx] = {
      id: product.id, title: product.title, image: product.image,
      price: product.price, brand: product.brand,
      category,
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

        {/* 필터 섹션 */}
        <div className={styles.catSection}>
          <div className={styles.filterRows}>
            {/* 순서: 제품 → 브랜드 → 타입(동적) → 가격 → 정렬 */}
            {['product', 'brand'].map(key => {
              const group = FILTER_GROUPS.find(g => g.key === key)
              return (
                <div key={key} className={styles.filterRow}>
                  <span className={styles.filterLabel}>{group.label}</span>
                  <div className={styles.filterChips}>
                    {group.options.map(opt => (
                      <button
                        key={opt}
                        className={`${styles.catTab} ${filters[key] === opt ? styles.catTabActive : ''}`}
                        onClick={() => setFilters(prev => {
                          const next = { ...prev, [key]: prev[key] === opt ? null : opt }
                          if (key === 'product') next.subtype = null
                          return next
                        })}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}

            {/* 타입 — 제품 선택 시만 표시 */}
            {filters.product && PRODUCT_SUBTYPES[filters.product] && (
              <div className={styles.filterRow}>
                <span className={styles.filterLabel}>타입</span>
                <div className={styles.filterChips}>
                  {PRODUCT_SUBTYPES[filters.product].map(opt => (
                    <button
                      key={opt}
                      className={`${styles.catTab} ${filters.subtype === opt ? styles.catTabActive : ''}`}
                      onClick={() => setFilters(prev => ({
                        ...prev,
                        subtype: prev.subtype === opt ? null : opt,
                      }))}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {['price', 'sort'].map(key => {
              const group = FILTER_GROUPS.find(g => g.key === key)
              return (
                <div key={key} className={styles.filterRow}>
                  <span className={styles.filterLabel}>{group.label}</span>
                  <div className={styles.filterChips}>
                    {group.options.map(opt => (
                      <button
                        key={opt}
                        className={`${styles.catTab} ${filters[key] === opt ? styles.catTabActive : ''}`}
                        onClick={() => setFilters(prev => ({
                          ...prev,
                          [key]: prev[key] === opt ? null : opt,
                        }))}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {(filters.product || filters.brand || filters.price || filters.sort) && (
            <div className={styles.catPickerWrap}>
              <div className={styles.catPickerHeader}>
                <span className={styles.catPickerQuery}>
                  {[filters.brand, filters.subtype, filters.product].filter(Boolean).join(' ')}
                  {filters.price && ` · ${filters.price}`}
                  {filters.sort && ` · ${filters.sort}`}
                </span>
                <button
                  className={styles.catClearBtn}
                  onClick={() => setFilters({ product: null, brand: null, price: null, sort: null, subtype: null })}
                >
                  필터 초기화
                </button>
              </div>
              {catLoading ? (
                <div className={styles.catLoading}>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className={styles.catSkeleton} />
                  ))}
                </div>
              ) : catProducts.length === 0 ? (
                <p className={styles.catEmpty}>검색 결과가 없어요. 다른 조건을 선택해보세요.</p>
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
                          add(p, nextIdx, filters.product ?? null)
                          if (nextIdx === 2) setThirdSlotOpen(false)
                        }}
                        disabled={alreadyAdded || isFull}
                        title={isFull && !alreadyAdded ? '최대 3개까지 비교 가능' : ''}
                      >
                        <div className={styles.catImgWrap}>
                          {p.image
                            ? <img src={p.image} alt={p.title} className={styles.catImg} />
                            : <span className={styles.catImgFallback}>—</span>
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

      {/* 카테고리 불일치 모달 */}
      {catMismatch && (
        <div className={styles.modalOverlay} onClick={() => setCatMismatch(null)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalIcon}>⚠️</div>
            <h3 className={styles.modalTitle}>카테고리가 맞지 않아요</h3>
            <p className={styles.modalDesc}>
              현재 <strong>{catMismatch.current}</strong> 제품이 비교 중이에요.<br />
              <strong>{catMismatch.incoming}</strong> 제품은 추가할 수 없어요.
            </p>
            <p className={styles.modalHint}>같은 카테고리 제품끼리만 비교할 수 있어요.</p>
            <div className={styles.modalBtns}>
              <button
                className={styles.modalBtnSecondary}
                onClick={() => {
                  setList([])
                  setReports([null, null, null])
                  setLoading([false, false, false])
                  setThirdSlotOpen(false)
                  setCatMismatch(null)
                }}
              >
                비교 목록 초기화
              </button>
              <button className={styles.modalBtnPrimary} onClick={() => setCatMismatch(null)}>
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
