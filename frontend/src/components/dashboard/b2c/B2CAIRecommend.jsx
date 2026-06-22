import styles from '../../../styles/dashboard/b2c/B2CAIRecommend.module.css'

const recommendProducts = [
  {
    rank: 1,
    name: '로보락 S8 MaxV Ultra',
    category: '로봇청소기',
    price: '1,390,000원',
    fit: '맞벌이 3~4인 가구',
    score: 94,
    reason: '청소 자동화, 장애물 인식, 자동 먼지 비움 니즈에 가장 잘 맞습니다.',
    tags: ['자동화', 'AI 인식', '프리미엄'],
  },
  {
    rank: 2,
    name: 'LG 휘센 오브제 에어컨',
    category: '에어컨',
    price: '1,320,000원',
    fit: '24평 이상 거실',
    score: 89,
    reason: '냉방 성능과 에너지 효율을 동시에 고려할 때 안정적인 선택입니다.',
    tags: ['에너지 효율', '저소음', '거실용'],
  },
  {
    rank: 3,
    name: '삼성 비스포크 냉장고',
    category: '냉장고',
    price: '1,897,000원',
    fit: '4인 이상 가족',
    score: 86,
    reason: '수납공간, 디자인, 브랜드 신뢰도를 중요하게 보는 사용자에게 적합합니다.',
    tags: ['대용량', '디자인', '수납'],
  },
]

const conditions = [
  { label: '예산', value: '150만원 이하' },
  { label: '가구 형태', value: '3~4인 가족' },
  { label: '주거 공간', value: '24평 이상' },
  { label: '중요 기준', value: '가격 · 리뷰 · 편의성' },
]

export default function B2CAIRecommend() {
  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>AI RECOMMEND</p>
          <h1>AI 맞춤 가전 추천</h1>
          <p>예산, 가족 수, 사용 패턴, 리뷰 반응을 기반으로 나에게 맞는 제품을 추천합니다.</p>
        </div>

        <button className={styles.resetBtn}>조건 다시 설정</button>
      </header>

      <section className={styles.conditionPanel}>
        <div className={styles.panelHeader}>
          <div>
            <h3>추천 조건</h3>
            <p>현재 입력된 사용자 조건입니다.</p>
          </div>
          <span>Personalized</span>
        </div>

        <div className={styles.conditionGrid}>
          {conditions.map(item => (
            <div key={item.label}>
              <span>{item.label}</span>
              <b>{item.value}</b>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.recommendList}>
          {recommendProducts.map(product => (
            <div className={styles.productCard} key={product.name}>
              <div className={styles.rank}>TOP {product.rank}</div>

              <div className={styles.productInfo}>
                <p>{product.category}</p>
                <h2>{product.name}</h2>
                <strong>{product.price}</strong>

                <div className={styles.tagBox}>
                  {product.tags.map(tag => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>

                <p className={styles.reason}>{product.reason}</p>
              </div>

              <div className={styles.scoreBox}>
                <span>AI 적합도</span>
                <b>{product.score}</b>
                <p>{product.fit}</p>
              </div>
            </div>
          ))}
        </div>

        <aside className={styles.aiPanel}>
          <p>AI SUMMARY</p>
          <h3>현재 조건에서는 로봇청소기 우선 추천</h3>
          <span>
            예산 범위 내에서 사용 편의성, 리뷰 만족도, 자동화 기능을 함께 고려하면
            로보락 S8 MaxV Ultra가 가장 높은 적합도를 보입니다.
          </span>

          <div className={styles.reasonBox}>
            <b>추천 근거</b>
            <ul>
              <li>자동 청소 기능 관련 긍정 리뷰 비율 높음</li>
              <li>맞벌이 가구의 시간 절약 니즈와 일치</li>
              <li>최근 가격 안정세로 구매 부담 완화</li>
            </ul>
          </div>
        </aside>
      </section>

      <section className={styles.formPanel}>
        <div className={styles.panelHeader}>
          <div>
            <h3>추천 조건 입력</h3>
            <p>나중에 실제 서비스에서는 이 입력값을 AI 추천 API로 보냅니다.</p>
          </div>
        </div>

        <div className={styles.formGrid}>
          <select defaultValue="">
            <option value="" disabled>예산 선택</option>
            <option>50만원 이하</option>
            <option>100만원 이하</option>
            <option>150만원 이하</option>
            <option>200만원 이상</option>
          </select>

          <select defaultValue="">
            <option value="" disabled>가족 수 선택</option>
            <option>1인 가구</option>
            <option>2인 가구</option>
            <option>3~4인 가족</option>
            <option>5인 이상 가족</option>
          </select>

          <select defaultValue="">
            <option value="" disabled>관심 카테고리</option>
            <option>냉장고</option>
            <option>에어컨</option>
            <option>로봇청소기</option>
            <option>건조기</option>
          </select>

          <button>AI 추천 받기</button>
        </div>
      </section>
    </>
  )
}