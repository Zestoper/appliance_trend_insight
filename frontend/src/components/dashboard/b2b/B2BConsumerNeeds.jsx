import styles from '../../../styles/dashboard/b2b/B2BConsumerNeeds.module.css'

export default function B2BConsumerNeeds() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>B2B CONSUMER INSIGHT</span>
        <h1>소비자 니즈</h1>
        <p>리뷰·검색 키워드·커뮤니티 반응을 기반으로 소비자가 원하는 기능을 분석합니다.</p>
      </div>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <h4>최다 언급 니즈</h4>
          <h2>AI 자동화</h2>
          <p>반복 사용 기능 선호</p>
        </div>

        <div className={styles.card}>
          <h4>긍정 반응</h4>
          <h2>74%</h2>
          <p>편의성 관련 리뷰</p>
        </div>

        <div className={styles.card}>
          <h4>불만 키워드</h4>
          <h2>가격</h2>
          <p>프리미엄 제품 부담</p>
        </div>

        <div className={styles.card}>
          <h4>핵심 타깃</h4>
          <h2>30~40대</h2>
          <p>맞벌이 가구 중심</p>
        </div>
      </div>

      <section className={styles.contentGrid}>
        <div className={styles.keywordBox}>
          <div className={styles.sectionHeader}>
            <h3>소비자 TOP 니즈 키워드</h3>
            <span>Keyword Ranking</span>
          </div>

          <div className={styles.keywordList}>
            <div>
              <strong>01</strong>
              <span>AI 자동청소</span>
              <p>92점</p>
            </div>
            <div>
              <strong>02</strong>
              <span>자동 먼지 비움</span>
              <p>88점</p>
            </div>
            <div>
              <strong>03</strong>
              <span>저소음</span>
              <p>84점</p>
            </div>
            <div>
              <strong>04</strong>
              <span>배터리 지속시간</span>
              <p>79점</p>
            </div>
            <div>
              <strong>05</strong>
              <span>반려동물 털 제거</span>
              <p>76점</p>
            </div>
          </div>
        </div>

        <div className={styles.sentimentBox}>
          <div className={styles.sectionHeader}>
            <h3>리뷰 감성 비율</h3>
            <span>Sentiment</span>
          </div>

          <div className={styles.circle}>
            <span>74%</span>
            <p>긍정</p>
          </div>

          <div className={styles.sentimentList}>
            <div>
              <span>긍정</span>
              <strong>74%</strong>
            </div>
            <div>
              <span>중립</span>
              <strong>18%</strong>
            </div>
            <div>
              <span>부정</span>
              <strong>8%</strong>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.aiBox}>
        <h2>AI 소비자 인사이트</h2>

        <div className={styles.analysis}>
          <h3>소비자는 단순 성능보다 “자동화된 편의성”에 더 강하게 반응합니다.</h3>
          <p>
            리뷰와 커뮤니티 반응을 분석한 결과, 소비자는 흡입력 자체보다 자동 먼지 비움,
            AI 경로 설정, 저소음 운전처럼 사용자의 개입을 줄여주는 기능에 높은 만족도를 보입니다.
          </p>

          <div className={styles.strategy}>
            추천 전략 : 자동화 기능 강조 · 맞벌이 가구 타깃 · 사용 편의성 중심 메시지
          </div>
        </div>
      </section>
    </div>
  )
}