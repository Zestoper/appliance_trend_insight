import styles from '../../../styles/dashboard/b2c/B2CDashboardMain.module.css'

const products = [
  { rank: 1, name: '삼성 비스포크 냉장고', price: '1,897,000원', score: 92, status: '지금 구매 추천' },
  { rank: 2, name: 'LG 휘센 에어컨', price: '1,320,000원', score: 88, status: '2주 대기 추천' },
  { rank: 3, name: '로보락 로봇청소기', price: '849,000원', score: 84, status: '가격 하락 중' },
]

export default function B2CDashboardMain() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>B2C DASHBOARD</p>
          <h1>내게 맞는 가전 구매 인사이트</h1>
        </div>

        <div className={styles.searchBox}>
          <input placeholder="제품명을 검색하세요" />
          <button>검색</button>
        </div>
      </header>

      <section className={styles.statsGrid}>
        <div className={styles.statCard}>
          <p>현재 인기 카테고리</p>
          <h2>에어컨</h2>
          <span>검색량 +38.5%</span>
        </div>
        <div className={styles.statCard}>
          <p>평균 가격 변동</p>
          <h2>-12.4%</h2>
          <span>최근 30일 기준</span>
        </div>
        <div className={styles.statCard}>
          <p>긍정 리뷰 비율</p>
          <h2>82%</h2>
          <span>커뮤니티·리뷰 분석</span>
        </div>
        <div className={styles.statCard}>
          <p>구매 추천 상품</p>
          <h2>24개</h2>
          <span>AI 기준 통과</span>
        </div>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.panelLarge}>
          <div className={styles.panelHeader}>
            <h3>가전 카테고리별 관심도</h3>
            <span>최근 6개월</span>
          </div>

          <div className={styles.chartBox}>
            <div style={{ height: '72%' }}><span>에어컨</span></div>
            <div style={{ height: '58%' }}><span>냉장고</span></div>
            <div style={{ height: '66%' }}><span>로봇청소기</span></div>
            <div style={{ height: '46%' }}><span>건조기</span></div>
            <div style={{ height: '39%' }}><span>식기세척기</span></div>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3>구매 타이밍</h3>
            <span>AI 판단</span>
          </div>

          <div className={styles.timingCard}>
            <strong>LG 휘센 에어컨</strong>
            <p>현재 가격이 계절 수요 증가 전보다 높습니다.</p>
            <b>2주 대기 추천</b>
          </div>

          <div className={styles.timingCard}>
            <strong>로보락 로봇청소기</strong>
            <p>최근 할인율이 상승하고 있습니다.</p>
            <b className={styles.buyNow}>지금 구매 추천</b>
          </div>
        </div>
      </section>

      <section className={styles.bottomGrid}>
        <div className={styles.tablePanel}>
          <div className={styles.panelHeader}>
            <h3>AI 추천 TOP 3</h3>
            <span>예산·리뷰·가격 기준</span>
          </div>

          <table>
            <thead>
              <tr>
                <th>순위</th>
                <th>제품명</th>
                <th>가격</th>
                <th>점수</th>
                <th>판단</th>
              </tr>
            </thead>
            <tbody>
              {products.map(item => (
                <tr key={item.rank}>
                  <td>{item.rank}</td>
                  <td>{item.name}</td>
                  <td>{item.price}</td>
                  <td>{item.score}</td>
                  <td>{item.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <h3>감성 분석</h3>
            <span>리뷰 요약</span>
          </div>

          <div className={styles.sentiment}>
            <div className={styles.circle}>82%</div>
            <div>
              <p><b>긍정</b> 에너지 효율, 디자인, 저소음</p>
              <p><b>부정</b> 설치비, 배송 지연, 가격 부담</p>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}