import styles from '../../../styles/dashboard/b2c/B2CPurchaseTiming.module.css'

const timingProducts = [
  {
    name: 'LG 휘센 에어컨',
    category: '에어컨',
    currentPrice: '1,320,000원',
    lowestPrice: '1,120,000원',
    change: '+17.8%',
    decision: '2주 대기 추천',
    status: 'wait',
    reason: '여름 성수기 직전 수요 증가로 가격이 상승했습니다. 프로모션 전환 가능성이 있어 단기 대기를 추천합니다.',
    confidence: 84,
  },
  {
    name: '로보락 로봇청소기',
    category: '로봇청소기',
    currentPrice: '849,000원',
    lowestPrice: '799,000원',
    change: '+6.2%',
    decision: '지금 구매 추천',
    status: 'buy',
    reason: '최근 할인율이 상승했고 리뷰 만족도도 높습니다. 최저가와의 차이가 크지 않아 현재 구매 적합도가 높습니다.',
    confidence: 91,
  },
  {
    name: '삼성 비스포크 냉장고',
    category: '냉장고',
    currentPrice: '1,897,000원',
    lowestPrice: '1,730,000원',
    change: '+9.6%',
    decision: '가격 알림 설정 추천',
    status: 'alert',
    reason: '가격은 다소 높지만 관심도와 긍정 리뷰가 안정적입니다. 목표가를 설정하고 하락 시 구매하는 전략이 적합합니다.',
    confidence: 78,
  },
]

const seasonData = [
  { month: '1월', label: '낮음', height: '32%' },
  { month: '2월', label: '낮음', height: '38%' },
  { month: '3월', label: '구매 적기', height: '48%' },
  { month: '4월', label: '상승', height: '61%' },
  { month: '5월', label: '주의', height: '76%' },
  { month: '6월', label: '고가', height: '92%' },
]

export default function B2CPurchaseTiming() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>PURCHASE TIMING</p>
          <h1>구매 타이밍 추천</h1>
          <p>가격 히스토리, 계절성, 검색량, 리뷰 반응을 종합해 지금 사도 되는지 판단합니다.</p>
        </div>

        <div className={styles.searchBox}>
          <input placeholder="구매 고민 중인 제품명 입력" />
          <button>분석하기</button>
        </div>
      </header>

      <section className={styles.topGrid}>
        <div className={styles.heroCard}>
          <p>AI 최종 판단</p>
          <h2>에어컨은 지금보다 2주 뒤 구매가 유리할 가능성이 높습니다.</h2>
          <span>
            현재 가격은 최근 30일 평균보다 높고, 성수기 프로모션 전환 가능성이 있어 단기 대기 전략을 추천합니다.
          </span>
        </div>

        <div className={styles.scoreCard}>
          <p>구매 적합도</p>
          <strong>84</strong>
          <span>100점 만점 기준</span>
        </div>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.panelLarge}>
          <div className={styles.panelHeader}>
            <div>
              <h3>계절별 가격 흐름</h3>
              <p>에어컨 카테고리 기준 · 월별 가격 상승 압력</p>
            </div>
            <span>Seasonality</span>
          </div>

          <div className={styles.seasonChart}>
            {seasonData.map(item => (
              <div className={styles.seasonItem} key={item.month}>
                <span>{item.label}</span>
                <div className={styles.barWrap}>
                  <div className={styles.bar} style={{ height: item.height }} />
                </div>
                <b>{item.month}</b>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>판단 기준</h3>
              <p>AI가 참고한 데이터</p>
            </div>
          </div>

          <div className={styles.factorList}>
            <div>
              <b>가격 히스토리</b>
              <p>최근 최저가 대비 현재 가격이 높은지 확인</p>
            </div>
            <div>
              <b>계절성</b>
              <p>에어컨·건조기처럼 시즌 영향을 받는 품목 분석</p>
            </div>
            <div>
              <b>신제품 출시 가능성</b>
              <p>신제품 출시 전후 가격 하락 가능성 반영</p>
            </div>
            <div>
              <b>검색량 증가율</b>
              <p>수요 급증으로 인한 가격 상승 위험 판단</p>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.productList}>
        <div className={styles.panelHeader}>
          <div>
            <h3>제품별 구매 타이밍</h3>
            <p>현재 가격과 최저가, 관심도 변화를 비교한 결과입니다.</p>
          </div>
        </div>

        <div className={styles.cards}>
          {timingProducts.map(product => (
            <div className={styles.productCard} key={product.name}>
              <div className={styles.cardTop}>
                <div>
                  <p>{product.category}</p>
                  <h4>{product.name}</h4>
                </div>
                <span className={`${styles.badge} ${styles[product.status]}`}>
                  {product.decision}
                </span>
              </div>

              <div className={styles.priceGrid}>
                <div>
                  <span>현재가</span>
                  <b>{product.currentPrice}</b>
                </div>
                <div>
                  <span>최근 최저가</span>
                  <b>{product.lowestPrice}</b>
                </div>
                <div>
                  <span>최저가 대비</span>
                  <b>{product.change}</b>
                </div>
              </div>

              <p className={styles.reason}>{product.reason}</p>

              <div className={styles.confidence}>
                <div>
                  <span>AI 확신도</span>
                  <b>{product.confidence}%</b>
                </div>
                <div className={styles.progress}>
                  <span style={{ width: `${product.confidence}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}