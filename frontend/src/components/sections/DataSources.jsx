import styles from '../../styles/DataSources.module.css'
import anim from '../../styles/animations.module.css'
import { useInView } from '../../hooks/useInView'

const DELAYS = [anim.delay0, anim.delay100, anim.delay200, anim.delay300]


const SOURCES = [
  {
    color: '#22c55e',
    source: 'Naver Shopping',
    title: '제품 정보 수집',
    items: ['제품명 · 브랜드', '현재 가격', '평점 · 리뷰 수', '카테고리', '구매 URL'],
  },
  {
    color: '#6366f1',
    source: 'Naver DataLab',
    title: '현재 관심도 분석',
    items: ['검색량 추이', '최근 증가율', '연령별 · 성별 관심도', '연관 검색어', '현재 인기 지수'],
  },
  {
    color: '#f59e0b',
    source: 'Coupang Review',
    title: '실사용자 분석',
    items: ['감성 분석', '장점 · 단점 추출', '결함 분석', '광고성 리뷰 제거', '소비자 만족도'],
  },
  {
    color: '#ec4899',
    source: 'News',
    title: '현재 제품 이슈 분석',
    items: ['리콜 여부', '안전성 이슈', '신제품 정보', '기술 특징'],
  },
]

export default function DataSources() {
  const header = useInView()
  const grid = useInView({ threshold: 0.1 })

  return (
    <section className={styles.section}>

      <div
        ref={header.ref}
        className={`${styles.header} ${anim.hidden} ${header.inView ? anim.visible : ''}`}
      >
        <p className={styles.eyebrow}>Data Sources</p>
        <h2 className={styles.title}>4가지 소스로 입체 분석합니다</h2>
        <p className={styles.desc}>
          쇼핑 데이터, 검색 트렌드, 실구매 리뷰, 뉴스를 통합해
          단 하나의 분석 리포트로 만들어냅니다.
        </p>
      </div>

      <div ref={grid.ref} className={styles.grid}>
        {SOURCES.map((src, i) => (
            <div
              key={src.title}
              className={`${styles.card} ${anim.hidden} ${grid.inView ? anim.visible : ''} ${DELAYS[i]}`}
            >
              <div className={styles.cardHeader}>
                <div className={styles.cardMeta}>
                  <span className={styles.cardSource} style={{ color: src.color }}>
                    {src.source}
                  </span>
                  <span className={styles.cardTitle}>{src.title}</span>
                </div>
              </div>

              <ul className={styles.itemList}>
                {src.items.map(item => (
                  <li key={item} className={styles.item}>
                    <span className={styles.dot} style={{ background: src.color }} />
                    {item}
                  </li>
                ))}
              </ul>

            </div>
        ))}
      </div>

    </section>
  )
}
