import styles from '../../../styles/dashboard/b2c/B2CSentimentAnalysis.module.css'

const sentimentSummary = [
  { label: '긍정', value: 72, text: '디자인 · 성능 · 편의성 만족' },
  { label: '중립', value: 18, text: '가격 비교 · 구매 고민' },
  { label: '부정', value: 10, text: '설치비 · 배송 · 소음 불만' },
]

const reviewKeywords = [
  { keyword: '저소음', count: 184, type: 'good' },
  { keyword: '에너지 효율', count: 162, type: 'good' },
  { keyword: '디자인', count: 148, type: 'good' },
  { keyword: '설치비', count: 91, type: 'bad' },
  { keyword: '배송 지연', count: 74, type: 'bad' },
  { keyword: '가격 부담', count: 68, type: 'bad' },
]

const productReviews = [
  {
    product: 'LG 휘센 에어컨',
    positive: 78,
    negative: 12,
    summary: '냉방 성능과 저소음 만족도가 높지만 설치비 관련 불만이 일부 있습니다.',
  },
  {
    product: '로보락 로봇청소기',
    positive: 84,
    negative: 8,
    summary: '자동 청소 편의성과 장애물 인식 기능에 대한 긍정 반응이 많습니다.',
  },
  {
    product: '삼성 비스포크 냉장고',
    positive: 76,
    negative: 14,
    summary: '디자인과 수납공간은 긍정적이나 가격 부담 언급이 있습니다.',
  },
]

export default function B2CSentimentAnalysis() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>SENTIMENT ANALYSIS</p>
          <h1>감성 분석</h1>
          <p>리뷰와 커뮤니티 반응을 분석해 소비자가 실제로 만족하거나 불만을 느끼는 지점을 보여줍니다.</p>
        </div>

        <div className={styles.searchBox}>
          <input placeholder="제품명 또는 카테고리 입력" />
          <button>분석</button>
        </div>
      </header>

      <section className={styles.topGrid}>
        <div className={styles.scoreCard}>
          <p>전체 긍정 비율</p>
          <div className={styles.circle}>72%</div>
          <span>최근 리뷰·커뮤니티 12,847건 기준</span>
        </div>

        <div className={styles.summaryGrid}>
          {sentimentSummary.map(item => (
            <div className={styles.summaryCard} key={item.label}>
              <p>{item.label}</p>
              <h2>{item.value}%</h2>
              <span>{item.text}</span>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.panelLarge}>
          <div className={styles.panelHeader}>
            <div>
              <h3>자주 언급된 키워드</h3>
              <p>리뷰에서 반복적으로 등장한 표현입니다.</p>
            </div>
            <span>Keyword Count</span>
          </div>

          <div className={styles.keywordList}>
            {reviewKeywords.map(item => (
              <div className={styles.keywordRow} key={item.keyword}>
                <div>
                  <b>{item.keyword}</b>
                  <span className={item.type === 'good' ? styles.good : styles.bad}>
                    {item.type === 'good' ? '긍정' : '부정'}
                  </span>
                </div>
                <div className={styles.barWrap}>
                  <span style={{ width: `${Math.min(item.count / 2, 100)}%` }} />
                </div>
                <strong>{item.count}회</strong>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>AI 감성 요약</h3>
              <p>리뷰 문장 기반 자동 요약</p>
            </div>
          </div>

          <div className={styles.aiBox}>
            <b>소비자는 성능보다 “사용 편의성”에 더 민감하게 반응하고 있습니다.</b>
            <p>
              최근 긍정 리뷰에서는 저소음, 자동화, 에너지 효율이 반복적으로 언급됩니다.
              반면 부정 리뷰는 설치비와 배송 지연처럼 구매 후 경험에 집중되어 있습니다.
            </p>
            <span>개선 포인트: 설치비 안내 강화 · 배송 일정 명확화 · 유지비 정보 제공</span>
          </div>
        </div>
      </section>

      <section className={styles.productPanel}>
        <div className={styles.panelHeader}>
          <div>
            <h3>제품별 감성 비교</h3>
            <p>제품별 긍정·부정 비율과 주요 반응 요약입니다.</p>
          </div>
        </div>

        <div className={styles.reviewCards}>
          {productReviews.map(item => (
            <div className={styles.reviewCard} key={item.product}>
              <h4>{item.product}</h4>

              <div className={styles.ratioBox}>
                <div>
                  <span>긍정</span>
                  <b>{item.positive}%</b>
                </div>
                <div>
                  <span>부정</span>
                  <b>{item.negative}%</b>
                </div>
              </div>

              <div className={styles.progressBox}>
                <span style={{ width: `${item.positive}%` }} />
              </div>

              <p>{item.summary}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}