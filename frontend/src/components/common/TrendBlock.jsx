import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import styles from '../../styles/TrendBlock.module.css'
import { API_BASE } from '../../config'

export default function TrendBlock({ category }) {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!category) return
    setLoading(true)
    setItems([])
    const controller = new AbortController()
    // Groq 호출 포함이라 느릴 수 있음 — 12초 내 응답 없으면 조용히 숨김
    const timer = setTimeout(() => controller.abort(), 12000)
    fetch(`${API_BASE}/api/trend?category=${encodeURIComponent(category)}`, { signal: controller.signal })
      .then(r => r.json())
      .then(data => { setItems(data.items?.slice(0, 5) ?? []); setLoading(false) })
      .catch(() => setLoading(false))
      .finally(() => clearTimeout(timer))
  }, [category])

  if (!loading && items.length === 0) return null

  return (
    <div className={styles.wrap}>
      <div className={styles.label}>
        <span className={styles.fire}>🔥</span>
        <span className={styles.labelText}>{category} 인기 TOP 5</span>
        <span className={styles.liveBadge}>LIVE</span>
      </div>

      <div className={styles.track}>
        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={styles.skelCard} />
            ))
          : items.map((item, i) => {
              const full = Math.round(item.reviewScore ?? 0)
              return (
                <div
                  key={item.id ?? i}
                  className={styles.card}
                  onClick={() =>
                    navigate(`/report/${item.id}`, { state: { product: item, category } })
                  }
                >
                  <span className={styles.rank}>{i + 1}</span>

                  <div className={styles.thumb}>
                    {item.image
                      ? <img src={item.image} alt={item.title} />
                      : <span>📦</span>
                    }
                  </div>

                  <div className={styles.info}>
                    <p className={styles.title}>{item.title}</p>
                    <p className={styles.price}>
                      {item.price > 0 ? `${item.price.toLocaleString()}원` : '가격 미정'}
                    </p>
                    {item.reviewScore > 0 && (
                      <p className={styles.stars}>
                        {'★'.repeat(full)}{'☆'.repeat(5 - full)}
                        <span className={styles.starsNum}> {item.reviewScore.toFixed(1)}</span>
                      </p>
                    )}
                  </div>
                </div>
              )
            })
        }
      </div>
    </div>
  )
}
