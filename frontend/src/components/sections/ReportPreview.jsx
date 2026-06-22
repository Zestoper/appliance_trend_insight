import { useState, useEffect } from 'react'
import styles from '../../styles/ReportPreview.module.css'
import anim from '../../styles/animations.module.css'
import { useInView } from '../../hooks/useInView'

function useCounter(target, duration = 1800, start = false) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    if (!start) return
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

// AI 구매 리포트 샘플 데이터 (실제 API 연동 전 목업)
const SAMPLE_REPORT = {
  product: '비스포크 냉장고 RF85C9141AP',
  brand: 'Samsung · 비스포크 라인업',
  price: '1,897,000원',
  rating: 4.6,
  reviewCount: '12,847',
  interest: 82,
  pros: ['에너지 효율 1등급', '수납 공간 최적화', '소음 매우 적음', '패널 교체 가능'],
  cons: ['가격 다소 높음', '정수기 필터 비용 별도'],
  recall: false,
  suitableFor: '4인 이상 가족, 인테리어 중시하는 가정',
  caution: '설치 공간 폭 902mm 이상 확보 필요',
  score: 92,
}

export default function ReportPreview() {
  const { product, brand, price, rating, reviewCount, interest, pros, cons, recall, suitableFor, caution, score } = SAMPLE_REPORT

  const header = useInView()
  const leftCard = useInView({ threshold: 0.1 })
  const rightCard = useInView({ threshold: 0.1 })

  const animatedInterest = useCounter(interest, 1500, leftCard.inView)
  const animatedScore = useCounter(score, 1800, rightCard.inView)

  // 별점 문자열 생성 (ex. 4.6 → "★★★★☆")
  const stars = '★'.repeat(Math.floor(rating)) + (rating % 1 >= 0.5 ? '★' : '☆') + '☆'.repeat(5 - Math.ceil(rating))

  return (
    <section className={styles.section}>

      {/* 헤더: fadeUp */}
      <div
        ref={header.ref}
        className={`${styles.header} ${anim.hidden} ${header.inView ? anim.visible : ''}`}
      >
        <p className={styles.eyebrow}>리포트 미리보기</p>
        <h2 className={styles.title}>이런 리포트를 받아보세요</h2>
      </div>

      <div className={styles.reportWrap}>

        {/* 왼쪽 카드: 왼쪽에서 슬라이드 인 */}
        <div
          ref={leftCard.ref}
          className={`${styles.productCard} ${anim.hiddenLeft} ${leftCard.inView ? anim.visibleLeft : ''}`}
        >
          <span className={styles.productBadge}>✓ 분석 완료</span>
          <p className={styles.productName}>{product}</p>
          <p className={styles.productBrand}>{brand}</p>
          <p className={styles.productPrice}>{price}</p>

          <div className={styles.ratingRow}>
            <span className={styles.stars}>{stars}</span>
            <span className={styles.ratingNum}>{rating}</span>
            <span className={styles.reviewCount}>({reviewCount}개 리뷰)</span>
          </div>

          {/* 현재 관심도 게이지 바 */}
          <p className={styles.interestLabel}>현재 관심도</p>
          <div className={styles.interestBarWrap}>
            <div className={styles.interestBar} />
          </div>
          <p className={styles.interestValue}>상위 {100 - animatedInterest}% · 관심도 {animatedInterest}점</p>
        </div>

        {/* 오른쪽 카드: 오른쪽에서 슬라이드 인 (딜레이 150ms로 순서감) */}
        <div
          ref={rightCard.ref}
          className={`${styles.analysisCard} ${anim.hiddenRight} ${rightCard.inView ? anim.visibleRight : ''}`}
          style={{ transitionDelay: '150ms' }}
        >

          {/* 장점 */}
          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: '#4ade80' }}>장점</p>
            <div className={styles.tagList}>
              {pros.map(p => (
                <span key={p} className={`${styles.tag} ${styles.tagGood}`}>{p}</span>
              ))}
            </div>
          </div>

          {/* 단점 */}
          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: '#f87171' }}>단점</p>
            <div className={styles.tagList}>
              {cons.map(c => (
                <span key={c} className={`${styles.tag} ${styles.tagBad}`}>{c}</span>
              ))}
            </div>
          </div>

          {/* 리콜 여부 */}
          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: 'var(--text-muted)' }}>리콜 여부</p>
            <span className={styles.recallSafe}>✓ 리콜 이력 없음 · 안전</span>
          </div>

          {/* 추천도 점수 */}
          <div className={styles.analysisRow}>
            <p className={styles.analysisTitle} style={{ color: 'var(--text-muted)' }}>추천도</p>
            <div className={styles.recommendScore}>
              <span className={styles.scoreBig}>{animatedScore}</span>
              <p className={styles.scoreDesc}>
                {suitableFor}에 적합<br />
                <span style={{ color: '#f59e0b', fontSize: '11px' }}>⚠ {caution}</span>
              </p>
            </div>
          </div>

          {/* 구매 링크 버튼 */}
          <button className={styles.buyBtn}>네이버 쇼핑에서 구매하기 →</button>

        </div>
      </div>

      <p className={styles.aiNote}>
        ✦ 실제 쇼핑 데이터 · 검색 트렌드 · 리뷰를 통합 분석한 결과입니다
      </p>

    </section>
  )
}
