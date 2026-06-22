import styles from '../../../styles/dashboard/b2b/B2BMarketInsight.module.css'

export default function B2BMarketInsight() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>B2B MARKET INSIGHT</span>
        <h1>시장 인사이트</h1>
        <p>경쟁 브랜드와 소비자 반응을 함께 분석해 시장 경쟁력을 파악합니다.</p>
      </div>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <h4>1위 브랜드</h4>
          <h2>삼성전자</h2>
          <p>AI 기능 언급 최다</p>
        </div>

        <div className={styles.card}>
          <h4>최다 니즈</h4>
          <h2>AI 자동화</h2>
          <p>반복 사용 기능 선호</p>
        </div>

        <div className={styles.card}>
          <h4>긍정 반응</h4>
          <h2>74%</h2>
          <p>편의성 관련 리뷰</p>
        </div>

        <div className={styles.card}>
          <h4>핵심 타깃</h4>
          <h2>30~40대</h2>
          <p>맞벌이 가구 중심</p>
        </div>
      </div>

      <section className={styles.contentGrid}>
        <div className={styles.tableBox}>
          <div className={styles.sectionHeader}>
            <h3>브랜드 경쟁 지표</h3>
            <span>Brand Comparison</span>
          </div>

          <table className={styles.table}>
            <thead>
              <tr>
                <th>브랜드</th>
                <th>시장 관심도</th>
                <th>리뷰 평점</th>
                <th>강점 키워드</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>삼성전자</td>
                <td>91점</td>
                <td>4.7</td>
                <td>AI 기능 · 스마트싱스</td>
              </tr>
              <tr>
                <td>LG전자</td>
                <td>88점</td>
                <td>4.8</td>
                <td>프리미엄 · 디자인</td>
              </tr>
              <tr>
                <td>Roborock</td>
                <td>82점</td>
                <td>4.9</td>
                <td>가성비 · 청소 성능</td>
              </tr>
              <tr>
                <td>다이슨</td>
                <td>76점</td>
                <td>4.6</td>
                <td>흡입력 · 브랜드 이미지</td>
              </tr>
            </tbody>
          </table>
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

      <section className={styles.keywordBox}>
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
      </section>

      <section className={styles.aiBox}>
        <h2>AI 시장 인사이트</h2>

        <div className={styles.analysis}>
          <h3>AI 기능은 브랜드 경쟁과 소비자 니즈 양쪽에서 핵심 요소로 나타납니다.</h3>
          <p>
            삼성전자는 AI 기능과 스마트홈 연동 키워드에서 강점을 보이고,
            LG전자는 프리미엄 디자인과 리뷰 만족도에서 우위를 보입니다.
            동시에 소비자는 자동 먼지 비움, AI 경로 설정, 저소음 운전처럼
            사용자의 개입을 줄여주는 기능에 더 강하게 반응하고 있습니다.
          </p>

          <div className={styles.strategy}>
            추천 전략 : AI 자동화 기능 강조 · 맞벌이 가구 타깃 · 가격 부담 완화 메시지
          </div>
        </div>
      </section>
    </div>
  )
}