import styles from '../../../styles/dashboard/b2c/B2CProductCompare.module.css'

const compareProducts = [
  {
    name: '삼성 비스포크 냉장고',
    brand: 'Samsung',
    price: '1,897,000원',
    rating: 4.6,
    reviews: '12,847',
    delivery: '네이버 최저가',
    sentiment: 82,
    pros: ['디자인 우수', '수납공간 넓음', '저소음'],
    cons: ['가격 높음', '설치 공간 필요'],
    score: 92,
  },
  {
    name: 'LG 오브제 냉장고',
    brand: 'LG',
    price: '1,760,000원',
    rating: 4.5,
    reviews: '9,421',
    delivery: '로켓배송 가능',
    sentiment: 79,
    pros: ['에너지 효율', '내부 구성 좋음', '브랜드 신뢰도'],
    cons: ['색상 선택 제한', '배송 지연'],
    score: 89,
  },
  {
    name: '캐리어 클라윈드 냉장고',
    brand: 'Carrier',
    price: '849,000원',
    rating: 4.2,
    reviews: '3,118',
    delivery: '할인 진행중',
    sentiment: 68,
    pros: ['가성비 좋음', '기본 기능 충실'],
    cons: ['소음 언급 있음', '프리미엄 기능 부족'],
    score: 76,
  },
]

const specs = [
  { label: '가격', key: 'price' },
  { label: '평점', key: 'rating' },
  { label: '리뷰 수', key: 'reviews' },
  { label: '구매 조건', key: 'delivery' },
  { label: '긍정 반응', key: 'sentiment' },
  { label: 'AI 추천 점수', key: 'score' },
]

export default function B2CProductCompare() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>PRODUCT COMPARE</p>
          <h1>제품 비교</h1>
          <p>가격, 평점, 리뷰 반응, 장단점 데이터를 기준으로 제품을 나란히 비교합니다.</p>
        </div>

        <div className={styles.searchBox}>
          <input placeholder="비교할 제품명을 입력하세요" />
          <button>제품 추가</button>
        </div>
      </header>

      <section className={styles.summaryGrid}>
        {compareProducts.map(product => (
          <div className={styles.productCard} key={product.name}>
            <p className={styles.brand}>{product.brand}</p>
            <h2>{product.name}</h2>
            <strong>{product.price}</strong>

            <div className={styles.scoreBox}>
              <span>AI 추천 점수</span>
              <b>{product.score}</b>
            </div>

            <button>구매 링크 보기</button>
          </div>
        ))}
      </section>

      <section className={styles.comparePanel}>
        <div className={styles.panelHeader}>
          <div>
            <h3>주요 지표 비교</h3>
            <p>쇼핑 데이터와 리뷰 데이터를 통합한 비교표입니다.</p>
          </div>
          <span>3 Products</span>
        </div>

        <div className={styles.compareTable}>
          <div className={styles.tableRow}>
            <div className={styles.tableHead}>항목</div>
            {compareProducts.map(product => (
              <div className={styles.tableHead} key={product.name}>{product.name}</div>
            ))}
          </div>

          {specs.map(spec => (
            <div className={styles.tableRow} key={spec.label}>
              <div className={styles.labelCell}>{spec.label}</div>
              {compareProducts.map(product => (
                <div className={styles.valueCell} key={product.name + spec.label}>
                  {spec.key === 'sentiment'
                    ? `${product[spec.key]}%`
                    : product[spec.key]}
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.bottomGrid}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>장점 비교</h3>
              <p>리뷰에서 반복적으로 언급된 긍정 요소</p>
            </div>
          </div>

          <div className={styles.tagCompare}>
            {compareProducts.map(product => (
              <div key={product.name}>
                <b>{product.name}</b>
                <div>
                  {product.pros.map(item => (
                    <span className={styles.goodTag} key={item}>{item}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>단점 비교</h3>
              <p>구매 전 확인해야 할 불만 요소</p>
            </div>
          </div>

          <div className={styles.tagCompare}>
            {compareProducts.map(product => (
              <div key={product.name}>
                <b>{product.name}</b>
                <div>
                  {product.cons.map(item => (
                    <span className={styles.badTag} key={item}>{item}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.aiPanel}>
        <div>
          <p>AI COMPARISON SUMMARY</p>
          <h3>가격과 만족도를 함께 보면 LG 오브제가 가장 균형 잡힌 선택입니다.</h3>
          <span>
            삼성 비스포크는 디자인과 프리미엄 만족도가 높지만 가격 부담이 있습니다.
            캐리어는 예산 절감 목적에는 적합하지만, 소음 관련 리뷰를 확인하는 것이 좋습니다.
          </span>
        </div>
      </section>
    </>
  )
}