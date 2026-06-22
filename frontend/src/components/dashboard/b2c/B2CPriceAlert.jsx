import styles from '../../../styles/dashboard/b2c/B2CPriceAlert.module.css'

const alertItems = [
  {
    product: '삼성 비스포크 냉장고',
    currentPrice: '1,897,000원',
    targetPrice: '1,750,000원',
    gap: '147,000원 남음',
    status: '대기중',
    progress: 74,
  },
  {
    product: '로보락 로봇청소기',
    currentPrice: '849,000원',
    targetPrice: '850,000원',
    gap: '목표가 도달',
    status: '알림 가능',
    progress: 100,
  },
  {
    product: 'LG 휘센 에어컨',
    currentPrice: '1,320,000원',
    targetPrice: '1,200,000원',
    gap: '120,000원 남음',
    status: '대기중',
    progress: 62,
  },
]

const priceHistory = [
  { month: '1주', height: '88%' },
  { month: '2주', height: '76%' },
  { month: '3주', height: '81%' },
  { month: '4주', height: '69%' },
  { month: '현재', height: '64%' },
]

export default function B2CPriceAlert() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>PRICE ALERT</p>
          <h1>가격 알림</h1>
          <p>원하는 목표 가격을 설정하면 가격 변동을 추적하고 도달 여부를 확인할 수 있습니다.</p>
        </div>

        <button className={styles.addBtn}>새 알림 추가</button>
      </header>

      <section className={styles.topGrid}>
        <div className={styles.formPanel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>가격 알림 설정</h3>
              <p>제품명과 목표 가격을 입력하세요.</p>
            </div>
          </div>

          <div className={styles.formGrid}>
            <input placeholder="제품명 예: 삼성 비스포크 냉장고" />
            <input placeholder="목표 가격 예: 1750000" />
            <button>알림 설정</button>
          </div>

          <p className={styles.notice}>
            실제 서비스에서는 목표가 도달 시 이메일 또는 푸시 알림으로 안내됩니다.
          </p>
        </div>

        <div className={styles.aiPanel}>
          <p>AI PRICE INSIGHT</p>
          <h2>로보락 로봇청소기는 현재 목표가에 도달했습니다.</h2>
          <span>
            최근 할인율이 상승했고 현재 가격이 설정한 목표가 이하로 내려왔습니다.
            재고와 배송 조건을 확인한 뒤 구매를 검토하는 것이 좋습니다.
          </span>
        </div>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.panelLarge}>
          <div className={styles.panelHeader}>
            <div>
              <h3>최근 가격 변화</h3>
              <p>관심 제품의 최근 가격 흐름입니다.</p>
            </div>
            <span>Last 30 Days</span>
          </div>

          <div className={styles.priceChart}>
            {priceHistory.map(item => (
              <div className={styles.chartItem} key={item.month}>
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
              <h3>알림 상태 요약</h3>
              <p>현재 등록된 가격 알림 기준</p>
            </div>
          </div>

          <div className={styles.statusList}>
            <div>
              <b>등록 알림</b>
              <strong>3개</strong>
            </div>
            <div>
              <b>목표가 도달</b>
              <strong>1개</strong>
            </div>
            <div>
              <b>평균 목표가 차이</b>
              <strong>89,000원</strong>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.alertPanel}>
        <div className={styles.panelHeader}>
          <div>
            <h3>내 가격 알림 목록</h3>
            <p>설정한 목표 가격과 현재 가격을 비교합니다.</p>
          </div>
        </div>

        <div className={styles.alertList}>
          {alertItems.map(item => (
            <div className={styles.alertCard} key={item.product}>
              <div className={styles.alertTop}>
                <div>
                  <h4>{item.product}</h4>
                  <p>{item.gap}</p>
                </div>
                <span className={item.status === '알림 가능' ? styles.activeBadge : styles.waitBadge}>
                  {item.status}
                </span>
              </div>

              <div className={styles.priceRow}>
                <div>
                  <span>현재가</span>
                  <b>{item.currentPrice}</b>
                </div>
                <div>
                  <span>목표가</span>
                  <b>{item.targetPrice}</b>
                </div>
              </div>

              <div className={styles.progress}>
                <span style={{ width: `${item.progress}%` }} />
              </div>

              <button>
                {item.status === '알림 가능' ? '구매 링크 보기' : '알림 유지하기'}
              </button>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}