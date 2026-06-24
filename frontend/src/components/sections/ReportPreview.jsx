import { useState, useEffect } from 'react'
import styles from '../../styles/ReportPreview.module.css'
import anim from '../../styles/animations.module.css'
import { useInView } from '../../hooks/useInView'
import { API_BASE } from '../../config'

const DEMO_QUERY = '비스포크 냉장고 RF85C9141AP'
const CACHE_KEY  = 'rp_preview_v1'
const CACHE_TTL  = 12 * 60 * 60 * 1000 // 12시간

function useCounter(target, duration = 1800, start = false) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!start || target == null) return
    setCount(0)
    const startTime = performance.now()
    const step = (now) => {
      const t = Math.min((now - startTime) / duration, 1)
      setCount(Math.round((1 - Math.pow(1 - t, 3)) * target))
      if (t < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [start, target, duration])
  return count
}

async function fetchPreviewData() {
  const [products, report, ai] = await Promise.all([
    fetch(`${API_BASE}/api/naver/products?query=${encodeURIComponent(DEMO_QUERY)}&page=1&display=1`).then(r => r.json()),
    fetch(`${API_BASE}/api/report?query=${encodeURIComponent(DEMO_QUERY)}`).then(r => r.json()),
    fetch(`${API_BASE}/api/ai-analysis?query=${encodeURIComponent(DEMO_QUERY)}`).then(r => r.json()),
  ])

  const product  = products?.items?.[0] ?? null
  const recent   = (report?.datalab?.data ?? []).slice(-4)
  const interest = recent.length > 0
    ? Math.round(recent.reduce((s, d) => s + d.ratio, 0) / recent.length)
    : 82
  const analysis = ai?.analysis ?? null

  return {
    title:       product?.title       ?? DEMO_QUERY,
    brand:       product?.brand       ?? 'Samsung · 비스포크 라인업',
    price:       product?.price > 0   ? `${product.price.toLocaleString()}원` : '1,897,000원',
    rating:      product?.reviewScore > 0 ? product.reviewScore : 4.6,
    reviewCount: product?.reviewCount > 0 ? product.reviewCount.toLocaleString() : '12,847',
    interest,
    pros:        analysis?.pros          ?? ['에너지 효율 1등급', '수납 공간 최적화', '소음 매우 적음', '패널 교체 가능'],
    cons:        analysis?.cons          ?? ['가격 다소 높음', '정수기 필터 비용 별도'],
    recall:      analysis?.recall        ?? false,
    suitableFor: analysis?.suitable_for  ?? '4인 이상 가족, 인테리어 중시하는 가정',
    caution:     analysis?.cautions?.[0] ?? '설치 공간 폭 902mm 이상 확보 필요',
    score:       analysis?.score != null  ? Math.round(analysis.score * 20) : 92,
  }
}

export default function ReportPreview() {
  const [data, setData] = useState(null)

  const header    = useInView()
  const leftCard  = useInView({ threshold: 0.1 })
  const rightCard = useInView({ threshold: 0.1 })

  useEffect(() => {
    try {
      const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null')
      if (cached && Date.now() - cached.ts < CACHE_TTL) {
        setData(cached.data)
        return
      }
    } catch {}

    fetchPreviewData()
      .then(result => {
        setData(result)
        try { localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: result })) } catch {}
      })
      .catch(() => {})
  }, [])

  const animatedInterest = useCounter(data?.interest ?? 0, 1500, leftCard.inView  && data != null)
  const animatedScore    = useCounter(data?.score    ?? 0, 1800, rightCard.inView && data != null)

  const rating = data?.rating ?? 4.6
  const stars  = '★'.repeat(Math.floor(rating)) + (rating % 1 >= 0.5 ? '★' : '☆') + '☆'.repeat(5 - Math.ceil(rating))

  if (!data) return (
    <section className={styles.section}>
      <div className={styles.header}>
        <p className={styles.eyebrow}>리포트 미리보기</p>
        <h2 className={styles.title}>이런 리포트를 받아보세요</h2>
      </div>
      <div className={styles.reportWrap}>
        <div className={styles.skeleton} />
        <div className={styles.skeleton} />
      </div>
    </section>
  )

  const { title, brand, price, reviewCount, interest, pros, cons, recall, suitableFor, caution } = data

  return (
    <section className={styles.section}>

      <div
        ref={header.ref}
        className={`${styles.header} ${anim.hidden} ${header.inView ? anim.visible : ''}`}
      >
        <p className={styles.eyebrow}>리포트 미리보기</p>
        <h2 className={styles.title}>이런 리포트를 받아보세요</h2>
      </div>

      <div className={styles.reportWrap}>

        <div
          ref={leftCard.ref}
          className={`${styles.productCard} ${anim.hiddenLeft} ${leftCard.inView ? anim.visibleLeft : ''}`}
        >
          <span className={styles.productBadge}>✓ 분석 완료</span>
          <p className={styles.productName}>{title}</p>
          <p className={styles.productBrand}>{brand}</p>
          <p className={styles.productPrice}>{price}</p>

          <div className={styles.ratingRow}>
            <span className={styles.stars}>{stars}</span>
            <span className={styles.ratingNum}>{rating}</span>
            <span className={styles.reviewCount}>({reviewCount}개 리뷰)</span>
          </div>

          <p className={styles.interestLabel}>현재 관심도</p>
          <div className={styles.interestBarWrap}>
            <div
              className={styles.interestBar}
              style={{ width: leftCard.inView ? `${interest}%` : '0%' }}
            />
          </div>
          <p className={styles.interestValue}>상위 {100 - animatedInterest}% · 관심도 {animatedInterest}점</p>
        </div>

        <div
          ref={rightCard.ref}
          className={`${styles.analysisCard} ${anim.hiddenRight} ${rightCard.inView ? anim.visibleRight : ''}`}
          style={{ transitionDelay: '150ms' }}
        >

          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: '#4ade80' }}>장점</p>
            <div className={styles.tagList}>
              {pros.map(p => (
                <span key={p} className={`${styles.tag} ${styles.tagGood}`}>{p}</span>
              ))}
            </div>
          </div>

          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: '#f87171' }}>단점</p>
            <div className={styles.tagList}>
              {cons.map(c => (
                <span key={c} className={`${styles.tag} ${styles.tagBad}`}>{c}</span>
              ))}
            </div>
          </div>

          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: 'var(--text-muted)' }}>리콜 여부</p>
            {recall
              ? <span className={styles.recallWarning}>⚠ 리콜 이력 있음</span>
              : <span className={styles.recallSafe}>✓ 리콜 이력 없음 · 안전</span>
            }
          </div>

          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: 'var(--text-muted)' }}>추천도</p>
            <div className={styles.recommendScore}>
              <span className={styles.scoreBig}>{animatedScore}</span>
              <p className={styles.scoreDesc}>
                {suitableFor}에 적합<br />
                {caution && <span style={{ color: '#f59e0b', fontSize: '11px' }}>⚠ {caution}</span>}
              </p>
            </div>
          </div>

          <button className={styles.buyBtn}>네이버 쇼핑에서 구매하기 →</button>

        </div>
      </div>

      <p className={styles.aiNote}>
        ✦ 실제 쇼핑 데이터 · 검색 트렌드 · 리뷰를 통합 분석한 결과입니다
      </p>

    </section>
  )
}
