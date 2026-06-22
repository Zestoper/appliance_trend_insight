import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/Trend.module.css'
import { API_BASE } from '../config'

const CATEGORIES = [
  "전체", "냉장고", "세탁기", "건조기", "에어컨",
  "공기청정기", "로봇청소기", "식기세척기", "에어프라이어", "TV",
]

const CAT_COLOR = {
  '냉장고': '#3b82f6', '세탁기': '#06b6d4', '건조기': '#8b5cf6',
  '에어컨': '#0ea5e9', '공기청정기': '#22c55e', '로봇청소기': '#a855f7',
  '식기세척기': '#14b8a6', '에어프라이어': '#f97316', 'TV': '#ec4899',
  '세탁건조기': '#6366f1',
}

const RANK_STYLE = {
  1: { color: '#fbbf24', glow: 'rgba(251,191,36,0.08)', border: 'rgba(251,191,36,0.18)' },
  2: { color: '#94a3b8', glow: 'rgba(148,163,184,0.06)', border: 'rgba(148,163,184,0.14)' },
  3: { color: '#fb923c', glow: 'rgba(251,146,60,0.06)', border: 'rgba(251,146,60,0.14)' },
}

function Stars({ score }) {
  if (!score) return null
  const full = Math.round(score)
  return (
    <span className={styles.stars}>
      <span className={styles.starsFilled}>{'★'.repeat(full)}</span>
      <span className={styles.starsEmpty}>{'☆'.repeat(5 - full)}</span>
      <span className={styles.starsNum}>{score.toFixed(1)}</span>
    </span>
  )
}

function TrendBadge({ diff }) {
  if (diff > 8)  return <span className={`${styles.trendBadge} ${styles.up}`}>↑↑ 급상승</span>
  if (diff > 2)  return <span className={`${styles.trendBadge} ${styles.up}`}>↑ 상승세</span>
  if (diff < -5) return <span className={`${styles.trendBadge} ${styles.down}`}>↓ 하락세</span>
  return              <span className={`${styles.trendBadge} ${styles.stable}`}>→ 안정적</span>
}

function HotKeywords({ items, onCatClick }) {
  const catMap = {}
  items.forEach(item => {
    if (!catMap[item.category]) catMap[item.category] = { total: 0, count: 0 }
    catMap[item.category].total += (item.trend_score || 0)
    catMap[item.category].count++
  })
  const catRanked = Object.entries(catMap)
    .map(([cat, { total, count }]) => ({ cat, avg: Math.round(total / count) }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 8)

  const tags = [...new Set(items.map(i => i.tag).filter(Boolean))].slice(0, 8)

  const now = new Date()
  const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')} 기준`

  const TOP_COLORS = ['#fbbf24', '#94a3b8', '#fb923c']

  return (
    <aside className={styles.hotBox}>
      <div className={styles.hotHead}>
        <span className={styles.hotBullet} />
        <span className={styles.hotTitle}>인기 검색어</span>
        <span className={styles.hotTime}>{timeStr}</span>
      </div>
      <ol className={styles.hotList}>
        {catRanked.map(({ cat, avg }, i) => {
          const col = CAT_COLOR[cat] ?? '#6366f1'
          const rank = i + 1
          return (
            <li key={cat} className={styles.hotItem} onClick={() => onCatClick(cat)}>
              <span className={styles.hotRank} style={rank <= 3 ? { color: TOP_COLORS[rank - 1] } : undefined}>
                {rank}
              </span>
              <span className={styles.hotKeyword}>{cat}</span>
              <span className={styles.hotScore} style={{ color: col }}>{avg}</span>
            </li>
          )
        })}
      </ol>
      {tags.length > 0 && (
        <div className={styles.hotTagSection}>
          <p className={styles.hotTagLabel}>트렌딩 태그</p>
          <div className={styles.hotTagList}>
            {tags.map(tag => (
              <span key={tag} className={styles.hotTag}>#{tag}</span>
            ))}
          </div>
        </div>
      )}
    </aside>
  )
}

function RankRow({ item, rank, onClick }) {
  const rs = RANK_STYLE[rank]
  const col = CAT_COLOR[item.category] ?? '#6366f1'
  return (
    <div
      className={styles.row}
      style={rs ? { background: rs.glow, borderColor: rs.border } : undefined}
      onClick={onClick}
    >
      <div className={styles.rankNum} style={rs ? { color: rs.color } : undefined}>
        {rank}
      </div>

      <div className={styles.thumb}>
        {item.image
          ? <img src={item.image} alt={item.title} />
          : <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="3" y="3" width="18" height="18" rx="3"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
        }
      </div>

      <div className={styles.info}>
        <div className={styles.infoTop}>
          <span className={styles.catChip} style={{ '--c': col }}>{item.category}</span>
          <TrendBadge diff={item.trend_diff ?? 0} />
        </div>
        <p className={styles.itemTitle}>{item.title}</p>
        <div className={styles.itemMeta}>
          <span className={styles.price}>
            {item.price > 0 ? `${item.price.toLocaleString()}원` : '가격 미정'}
          </span>
          {item.reviewScore > 0 && <Stars score={item.reviewScore} />}
          {item.reviewCount > 0 && (
            <span className={styles.reviewCnt}>{item.reviewCount.toLocaleString()}개</span>
          )}
        </div>
        {item.reason && (
          <p className={styles.reason}>
            <span className={styles.reasonDot}>✦</span>{item.reason}
          </p>
        )}
      </div>

      <div className={styles.scoreWrap}>
        {item.tag && <span className={styles.aiTag}>{item.tag}</span>}
        <span className={styles.scoreNum}>
          {item.trend_score > 0 ? Math.round(item.trend_score) : '—'}
        </span>
        <span className={styles.scoreLabel}>트렌드 지수</span>
      </div>
    </div>
  )
}

export default function Trend() {
  const navigate = useNavigate()
  const [cache, setCache] = useState({})
  const [active, setActive] = useState('전체')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function load(cat) {
    if (cache[cat]) { setActive(cat); return }
    setActive(cat)
    setLoading(true)
    setError(null)
    try {
      const url = cat === '전체'
        ? `${API_BASE}/api/trend`
        : `${API_BASE}/api/trend?category=${encodeURIComponent(cat)}`
      const data = await fetch(url).then(r => r.json())
      if (data.error) setError(data.error)
      setCache(prev => ({ ...prev, [cat]: data.items ?? [] }))
    } catch {
      setError('데이터를 불러오지 못했습니다')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load('전체') }, [])

  const items = cache[active] ?? []

  return (
    <div className={styles.page} data-scroll-container>
      <Navbar />
      <div className={styles.container}>

        <div className={styles.header}>
          <div>
            <span className={styles.liveBadge}>LIVE TREND</span>
            <h1 className={styles.title}>트렌드 TOP 10</h1>
            <p className={styles.subtitle}>DataLab 검색 관심도 + 리뷰 품질을 AI가 종합 분석</p>
          </div>
          <div className={styles.liveWrap}>
            <span className={styles.liveDot} />
            <span className={styles.liveText}>실시간</span>
          </div>
        </div>

        <div className={styles.filters}>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              className={`${styles.filterBtn} ${active === cat ? styles.filterActive : ''}`}
              onClick={() => load(cat)}
            >
              {cat}
              {cache[cat] && active !== cat && <span className={styles.cachedDot} />}
            </button>
          ))}
        </div>

        <div className={styles.body}>
          <div className={styles.mainCol}>
            {loading && (
              <div className={styles.loadingWrap}>
                <div className={styles.spinner} />
                <p>트렌드 분석 중...</p>
              </div>
            )}

            {error && <p className={styles.error}>{error}</p>}

            {!loading && items.length > 0 && (
              <div className={styles.list}>
                {items.map((item, i) => (
                  <RankRow
                    key={item.id ?? i}
                    item={item}
                    rank={i + 1}
                    onClick={() => navigate(`/report/${item.id}`, {
                      state: { product: item, category: item.category },
                    })}
                  />
                ))}
              </div>
            )}
          </div>

          <HotKeywords items={items} onCatClick={cat => load(cat)} />
        </div>

      </div>
    </div>
  )
}
