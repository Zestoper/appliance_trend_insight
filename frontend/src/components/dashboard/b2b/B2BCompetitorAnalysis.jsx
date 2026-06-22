import styles from '../../../styles/dashboard/b2b/B2BCompetitorAnalysis.module.css'

export default function B2BCompetitorAnalysis() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>B2B COMPETITOR INSIGHT</span>
        <h1>경쟁사 분석</h1>
        <p>브랜드별 시장 관심도, 리뷰 평점, 뉴스 언급량을 비교합니다.</p>
      </div>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <h4>1위 브랜드</h4>
          <h2>삼성전자</h2>
          <p>AI 기능 언급 최다</p>
        </div>

        <div className={styles.card}>
          <h4>리뷰 만족도</h4>
          <h2>4.8점</h2>
          <p>LG전자 평균 평점</p>
        </div>

        <div className={styles.card}>
          <h4>뉴스 언급량</h4>
          <h2>1,450건</h2>
          <p>최근 30일 기준</p>
        </div>

        <div className={styles.card}>
          <h4>경쟁 강도</h4>
          <h2>높음</h2>
          <p>프리미엄 가전 중심</p>
        </div>
      </div>

      <section className={styles.tableBox}>
        <div className={styles.sectionHeader}>
          <h3>주요 브랜드 경쟁 지표</h3>
          <span>Brand Comparison</span>
        </div>

        <table className={styles.table}>
          <thead>
            <tr>
              <th>브랜드</th>
              <th>시장 관심도</th>
              <th>리뷰 평점</th>
              <th>뉴스 언급량</th>
              <th>강점 키워드</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>삼성전자</td>
              <td>91점</td>
              <td>4.7</td>
              <td>1,450건</td>
              <td>AI 기능 · 스마트싱스</td>
            </tr>
            <tr>
              <td>LG전자</td>
              <td>88점</td>
              <td>4.8</td>
              <td>1,320건</td>
              <td>프리미엄 · 디자인</td>
            </tr>
            <tr>
              <td>Roborock</td>
              <td>82점</td>
              <td>4.9</td>
              <td>1,100건</td>
              <td>가성비 · 청소 성능</td>
            </tr>
            <tr>
              <td>다이슨</td>
              <td>76점</td>
              <td>4.6</td>
              <td>870건</td>
              <td>흡입력 · 브랜드 이미지</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className={styles.aiBox}>
        <h2>AI 경쟁 분석</h2>

        <div className={styles.analysis}>
          <h3>삼성전자는 AI 기능 중심의 시장 선점 효과가 강하게 나타납니다.</h3>
          <p>
            삼성전자는 AI 기능과 스마트홈 연동 키워드에서 높은 언급량을 보이며,
            LG전자는 프리미엄 디자인과 사용자 만족도에서 강점을 보입니다.
            Roborock은 가격 대비 성능을 중심으로 소비자 반응이 긍정적입니다.
          </p>

          <div className={styles.strategy}>
            추천 전략 : AI 기능 차별화 · 프리미엄 이미지 강화 · 가격 경쟁력 확보
          </div>
        </div>
      </section>
    </div>
  )
}