import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import FilterBar from '../components/common/FilterBar'
import TrendBlock from '../components/common/TrendBlock'
import styles from '../styles/ProductList.module.css'
import { API_BASE } from '../config'

const PAGE_SIZE = 15

const BRAND_NORMALIZE = {
  'LG전자': 'LG', '삼성전자': '삼성', '대우전자': '대우',
  '위니아딤채': '위니아', '위니아만도': '위니아',
  'Dyson': '다이슨', 'DYSON': '다이슨',
  'Philips': '필립스', 'PHILIPS': '필립스',
  'Sony': '소니', 'SONY': '소니',
  'Bosch': '보쉬', 'BOSCH': '보쉬',
  'Tefal': '테팔', 'TEFAL': '테팔',
  'Panasonic': '파나소닉', 'PANASONIC': '파나소닉',
  'Xiaomi': '샤오미',
  'Roborock': '로보락', 'ROBOROCK': '로보락',
  'Ecovacs': '에코백스', 'ECOVACS': '에코백스',
  'Coway': '코웨이', 'COWAY': '코웨이',
  'Winix': '위닉스', 'WINIX': '위닉스',
}
function normalizeBrand(raw) { return BRAND_NORMALIZE[raw] ?? raw }

const VALID_APPLIANCE_TERMS = [
  '에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기',
  'TV', '텔레비전', '에어프라이어', '전기밥솥', '밥솥', '전자레인지', '커피머신',
  '믹서기', '전기포트', '사운드바', '스피커', '프로젝터', '가습기', '제습기',
  '선풍기', '히터', '전기히터', '헤어드라이어', '청소기', '냉난방기', '세탁건조기',
  '인덕션', '전기레인지', '오븐', '스타일러', '의류관리기', '정수기', '제빙기',
]

export default function ProductList() {
  const { category } = useParams()
  const navigate = useNavigate()

  const [products, setProducts] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterState, setFilterState] = useState({ selectedBrands: [], priceRange: null })
  const [sort, setSort] = useState({ label: '관련도순', api: 'sim', client: null })
  const pageRef = useRef(null)

  useEffect(() => {
    setPage(1)
  }, [category, searchTerm, sort.label])

  // sort.client는 클라이언트 정렬이라 API 재요청 필요없음
  useEffect(() => {
    setLoading(true)
    const controller = new AbortController()
    const query = searchTerm ? `${category} ${searchTerm}` : category
    fetch(
      `${API_BASE}/api/naver/products?query=${encodeURIComponent(query)}&page=${page}&display=${PAGE_SIZE}&sort=${sort.api}&category=${encodeURIComponent(category)}`,
      { signal: controller.signal }
    )
      .then(r => r.json())
      .then(data => {
        setProducts(data.items ?? [])
        setTotal(data.total ?? 0)
        setLoading(false)
      })
      .catch(e => { if (e.name !== 'AbortError') setLoading(false) })
    return () => controller.abort()
  }, [category, page, searchTerm, sort.label])

  const filteredProducts = products
    .filter(p => {
      const { selectedBrands } = filterState
      return selectedBrands.length === 0 || selectedBrands.includes(normalizeBrand(p.brand))
    })
    .filter(p => {
      const pr = filterState.priceRange
      if (!pr || (pr.min === 0 && pr.max === Infinity)) return true
      return p.price >= pr.min && p.price <= pr.max
    })
    .sort((a, b) => {
      if (sort.client === 'review') return b.reviewCount - a.reviewCount
      if (sort.client === 'score')  return b.reviewScore - a.reviewScore
      return 0
    })

  // 전체 페이지 수 계산 (네이버 API start 파라미터 최대 1000 → 최대 66페이지)
  const totalPages = Math.min(Math.ceil(total / PAGE_SIZE), 66)

  // 페이지 번호를 5개씩 묶어서 표시 (1~5, 6~10, 11~15 ...)
  const pageGroup = Math.floor((page - 1) / 5)
  const pageStart = pageGroup * 5 + 1
  const pageEnd = Math.min(pageStart + 4, totalPages)

  function handlePage(p) {
    setPage(p)
    // body에 overflow:hidden이 걸려있어서 window.scrollTo가 안 됨
    // → .page div(pageRef)를 직접 스크롤 위로 올림
    pageRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const isValidCategory = VALID_APPLIANCE_TERMS.some(t => category.includes(t) || t.includes(category))

  if (!isValidCategory) {
    return (
      <div className={styles.page}>
        <Navbar />
        <div className={styles.container}>
          <div className={styles.invalidCategory}>
            <span style={{ fontSize: 40 }}>🏠</span>
            <p className={styles.invalidTitle}>가전제품 카테고리만 조회할 수 있습니다</p>
            <p className={styles.invalidDesc}>에어컨, 냉장고, 세탁기 등 가전제품 키워드로 검색해주세요</p>
            <button className={styles.invalidBtn} onClick={() => navigate('/')}>홈으로 돌아가기</button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page} ref={pageRef} data-scroll-container>
      <Navbar />
      <div className={styles.container}>

          <div className={styles.breadcrumb}>
          <span onClick={() => navigate('/')} className={styles.breadcrumbLink}>홈</span>
          <span className={styles.breadcrumbSep}>›</span>
          <span>{category}</span>
        </div>

        <div className={styles.header}>
          <h1 className={styles.title}>{category}</h1>
          <p className={styles.sub}>
            {total > 0 ? `${total.toLocaleString()}개 제품` : '검색 중...'} · 실시간 트렌드 분석
          </p>
        </div>

        <TrendBlock category={category} />

        <FilterBar
          products={products}
          category={category}
          onSearchChange={setSearchTerm}
          onFilterChange={setFilterState}
          onSortChange={setSort}
        />

        {loading ? (
          <div className={styles.grid}>
            {Array.from({ length: PAGE_SIZE }).map((_, i) => (
              <div key={i} className={styles.cardSkeleton} />
            ))}
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className={styles.empty}>검색 결과가 없습니다.</div>
        ) : (
          <div className={styles.grid}>
            {filteredProducts.map(product => (
              <div
                key={product.id || product.title}
                className={styles.card}
                onClick={() => navigate(`/report/${product.id}`, { state: { product, category } })}
              >
                <div className={styles.imgWrap}>
                  {product.image
                    ? <img src={product.image} alt={product.title} className={styles.productImg} />
                    : <div className={styles.imgFallback}>📦</div>
                  }
                </div>

                <div className={styles.cardBody}>
                  {product.brand && <p className={styles.brand}>{product.brand}</p>}
                  <p className={styles.name}>{product.title}</p>
                  {product.mallName && <p className={styles.mallName}>{product.mallName}</p>}
                </div>

                <div className={styles.cardFooter}>
                  <span className={styles.price}>
                    {product.price > 0 ? `${product.price.toLocaleString()}원` : '가격 미정'}
                  </span>
                  <span className={styles.analyzeBtn}>분석 보기 →</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && !loading && (
          <div className={styles.pagination}>
            <button
              className={styles.pageBtn}
              onClick={() => handlePage(page - 1)}
              disabled={page === 1}
            >
              ←
            </button>

            {pageStart > 1 && (
              <button className={styles.pageBtn} onClick={() => handlePage(pageStart - 1)}>···</button>
            )}

            {Array.from({ length: pageEnd - pageStart + 1 }, (_, i) => pageStart + i).map(p => (
              <button
                key={p}
                className={`${styles.pageBtn} ${p === page ? styles.pageBtnActive : ''}`}
                onClick={() => handlePage(p)}
              >
                {p}
              </button>
            ))}

            {pageEnd < totalPages && (
              <button className={styles.pageBtn} onClick={() => handlePage(pageEnd + 1)}>···</button>
            )}

            <button
              className={styles.pageBtn}
              onClick={() => handlePage(page + 1)}
              disabled={page === totalPages}
            >
              →
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
