import styles from '../../../styles/dashboard/b2b/B2BAIStrategyReport.module.css'

export default function B2BAIStrategyReport() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>B2B AI STRATEGY REPORT</span>
        <h1>AI 전략 리포트</h1>
        <p>시장 데이터, 경쟁사 동향, 소비자 니즈를 종합해 기업 전략 방향을 제안합니다.</p>
      </div>

      <div className={styles.summaryBox}>
        <div>
          <span>AI 종합 판단</span>
          <h2>프리미엄 AI 가전 시장 확대 가능성이 높습니다.</h2>
          <p>
            검색량 증가, 뉴스 언급량 상승, 긍정 리뷰 확대가 동시에 나타나며
            AI 기능 중심의 제품 전략이 유효할 것으로 분석됩니다.
          </p>
        </div>

        <div className={styles.scoreBox}>
          <h3>전략 점수</h3>
          <strong>91</strong>
          <p>Very High</p>
        </div>
      </div>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <h4>추천 타깃</h4>
          <h2>30~40대</h2>
          <p>맞벌이 · 프리미엄 가구</p>
        </div>

        <div className={styles.card}>
          <h4>핵심 제품군</h4>
          <h2>로봇청소기</h2>
          <p>AI 자동화 니즈 최다</p>
        </div>

        <div className={styles.card}>
          <h4>우선 전략</h4>
          <h2>AI 기능</h2>
          <p>자동화 · 스마트홈 연동</p>
        </div>

        <div className={styles.card}>
          <h4>시장 리스크</h4>
          <h2>가격 경쟁</h2>
          <p>중국 브랜드 확산</p>
        </div>
      </div>

      <section className={styles.strategyGrid}>
        <div className={styles.swotBox}>
          <div className={styles.sectionHeader}>
            <h3>SWOT 분석</h3>
            <span>Business Diagnosis</span>
          </div>

          <div className={styles.swotGrid}>
            <div className={styles.swotItem}>
              <strong>S</strong>
              <h4>Strength</h4>
              <p>AI 기능과 프리미엄 가전에 대한 소비자 관심 증가</p>
            </div>

            <div className={styles.swotItem}>
              <strong>W</strong>
              <h4>Weakness</h4>
              <p>높은 가격으로 인한 구매 전환 장벽 존재</p>
            </div>

            <div className={styles.swotItem}>
              <strong>O</strong>
              <h4>Opportunity</h4>
              <p>맞벌이 가구 증가와 자동화 가전 수요 확대</p>
            </div>

            <div className={styles.swotItem}>
              <strong>T</strong>
              <h4>Threat</h4>
              <p>중국 브랜드의 가격 경쟁과 빠른 제품 출시</p>
            </div>
          </div>
        </div>

        <div className={styles.priorityBox}>
          <div className={styles.sectionHeader}>
            <h3>전략 우선순위</h3>
            <span>Priority</span>
          </div>

          <div className={styles.priorityList}>
            <div>
              <span>01</span>
              <p>AI 자동화 기능 중심 마케팅</p>
              <strong>최우선</strong>
            </div>
            <div>
              <span>02</span>
              <p>30~40대 맞벌이 가구 타깃팅</p>
              <strong>높음</strong>
            </div>
            <div>
              <span>03</span>
              <p>프리미엄 제품 라인업 강화</p>
              <strong>높음</strong>
            </div>
            <div>
              <span>04</span>
              <p>가격 경쟁 대응 프로모션 설계</p>
              <strong>중간</strong>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.finalInsight}>
        <h3>최종 인사이트</h3>
        <p>
          현재 시장에서는 단순 성능 경쟁보다 <b>AI 기반 편의성</b>과
          <b> 프리미엄 사용 경험</b>이 구매 결정에 더 큰 영향을 미칩니다.
          기업은 제품 기능보다 “생활이 얼마나 편해지는가”를 중심으로
          전략 메시지를 설계하는 것이 효과적입니다.
        </p>
      </section>
    </div>
  )
}