import { useState, useEffect, useRef } from 'react'
import styles from '../../styles/FilterBar.module.css'

// "LG전자" → "LG" 등 표기 통일
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

// 드롭다운에 표시할 대표 브랜드 허용 목록
const MAJOR_BRANDS = new Set([
  '삼성', 'LG', '위닉스', '캐리어', '다이슨', '코웨이',
  '쿠쿠', '쿠첸', '위니아', '린나이', '로보락', '에코백스',
  '필립스', '소니', '보쉬', '테팔', '파나소닉', '샤오미', '대우',
])

function normalizeBrand(raw) {
  return BRAND_NORMALIZE[raw] ?? raw
}

// 카테고리별 고정 대표 브랜드 목록 (제품 결과와 무관하게 항상 표시)
const CATEGORY_BRANDS = {
  '에어컨':       ['삼성', 'LG', '캐리어', '위니아'],
  '냉장고':       ['삼성', 'LG', '위니아'],
  '세탁기':       ['삼성', 'LG'],
  '건조기':       ['삼성', 'LG', '린나이'],
  'TV':           ['삼성', 'LG', '소니'],
  '선풍기':       ['삼성', 'LG', '다이슨'],
  '공기청정기':   ['삼성', 'LG', '위닉스', '코웨이', '다이슨'],
  '제습기':       ['삼성', 'LG', '위닉스'],
  '가습기':       ['삼성', 'LG', '위닉스', '다이슨', '필립스'],
  '로봇청소기':   ['삼성', 'LG', '로보락', '에코백스', '샤오미'],
  '식기세척기':   ['삼성', 'LG', '보쉬'],
  '에어프라이어': ['필립스', '테팔', '쿠쿠', '삼성', 'LG'],
  '전자레인지':   ['삼성', 'LG'],
  '전기밥솥':     ['쿠쿠', '쿠첸', '삼성', 'LG'],
  '헤어드라이어': ['다이슨', '필립스', '파나소닉', '샤오미', 'LG', '삼성'],
  '청소기':       ['다이슨', '삼성', 'LG', '로보락', '필립스'],
  '정수기':       ['코웨이', '청호나이스', '쿠쿠', '삼성', 'LG'],
}

const PRICE_OPTIONS = [
  { label: '전체',          min: 0,       max: Infinity },
  { label: '10만원 이하',   min: 0,       max: 100000 },
  { label: '10~50만원',     min: 100000,  max: 500000 },
  { label: '50~100만원',    min: 500000,  max: 1000000 },
  { label: '100만원 이상',  min: 1000000, max: Infinity },
]

const SORT_OPTIONS = [
  { label: '관련도순',    api: 'sim',  client: null },
  { label: '최신순',      api: 'date', client: null },
  { label: '낮은가격순', api: 'asc',  client: null },
  { label: '높은가격순', api: 'dsc',  client: null },
  { label: '리뷰 많은순', api: 'sim',  client: 'review' },
  { label: '별점순',      api: 'sim',  client: 'score' },
]

export default function FilterBar({ products, category, onSearchChange, onFilterChange, onSortChange }) {
  const [search, setSearch] = useState('')
  // css-skill #1: 평소엔 아이콘만(40px 원), 클릭하면 너비 확장
  const [searchExpanded, setSearchExpanded] = useState(false)
  const [openPanel, setOpenPanel] = useState(null)
  const [selectedBrands, setSelectedBrands] = useState([])
  const [selectedPrice, setSelectedPrice] = useState(PRICE_OPTIONS[0])
  const [selectedSort, setSelectedSort] = useState(SORT_OPTIONS[0])
  const barRef = useRef(null)
  const searchInputRef = useRef(null)

  // 카테고리별 고정 목록 우선, 없으면 제품 결과에서 대표 브랜드만 추출
  const brands = CATEGORY_BRANDS[category]
    ?? [...new Set(
      products.map(p => normalizeBrand(p.brand)).filter(b => b && MAJOR_BRANDS.has(b))
    )].sort()

  // 검색어 debounce: 타이핑 멈춘 뒤 400ms 후 부모에 전달
  useEffect(() => {
    const timer = setTimeout(() => onSearchChange(search), 400)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    onFilterChange({ selectedBrands, priceRange: selectedPrice })
  }, [selectedBrands, selectedPrice])

  useEffect(() => {
    onSortChange?.(selectedSort)
  }, [selectedSort])

  // 필터바 바깥 클릭 시 드롭다운 + 검색창 닫기
  useEffect(() => {
    function handleClickOutside(e) {
      if (barRef.current && !barRef.current.contains(e.target)) {
        setOpenPanel(null)
        // 검색어가 없으면 검색창도 닫기
        if (!search) setSearchExpanded(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [search])

  function handleSearchExpand() {
    setSearchExpanded(true)
    // 너비 확장 애니메이션 후 input에 포커스 (css-skill #1 동일 패턴)
    setTimeout(() => searchInputRef.current?.focus(), 300)
  }

  function handleSearchCollapse() {
    setSearch('')
    setSearchExpanded(false)
    onSearchChange('')
  }

  function toggleBrand(brand) {
    setSelectedBrands(prev =>
      prev.includes(brand) ? prev.filter(b => b !== brand) : [...prev, brand]
    )
  }

  function resetAll() {
    setSearch('')
    setSelectedBrands([])
    setSelectedPrice(PRICE_OPTIONS[0])
    setSelectedSort(SORT_OPTIONS[0])
    setSearchExpanded(false)
    onSearchChange('')
  }

  const hasFilter = search || selectedBrands.length > 0 || selectedPrice.min > 0 || selectedPrice.max < Infinity || selectedSort.label !== '관련도순'

  return (
    <div ref={barRef} className={styles.bar}>

      {/* ── 왼쪽: 확장/축소 검색 (css-skill #1) ── */}
      <div
        className={`${styles.searchWrap} ${searchExpanded ? styles.searchExpanded : ''}`}
        onClick={!searchExpanded ? handleSearchExpand : undefined}
      >
        <div className={styles.searchIconWrap}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="22" y2="22" />
          </svg>
        </div>
        <input
          ref={searchInputRef}
          className={styles.searchInput}
          placeholder="제품 이름 검색..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ pointerEvents: searchExpanded ? 'auto' : 'none' }}
        />
        {searchExpanded && (
          <button className={styles.clearBtn} onMouseDown={e => e.preventDefault()} onClick={handleSearchCollapse}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      {/* ── 오른쪽: 드롭다운 필터들 ── */}
      <div className={styles.leftGroup}>

        {/* 정렬 드롭다운 */}
        <div className={styles.dropdownWrap}>
          <button
            className={`${styles.filterBtn} ${selectedSort.label !== '관련도순' ? styles.filterBtnActive : ''}`}
            onClick={() => setOpenPanel(prev => prev === 'sort' ? null : 'sort')}
          >
            {selectedSort.label}
            <span className={`${styles.caret} ${openPanel === 'sort' ? styles.caretOpen : ''}`}>▾</span>
          </button>
          {openPanel === 'sort' && (
            <div className={styles.panel}>
              {SORT_OPTIONS.map(opt => (
                <label key={opt.label} className={styles.radioRow}>
                  <input type="radio" className={styles.radio}
                    checked={selectedSort.label === opt.label}
                    onChange={() => { setSelectedSort(opt); setOpenPanel(null) }} />
                  <span className={styles.checkLabel}>{opt.label}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* 제조사 드롭다운 */}
        <div className={styles.dropdownWrap}>
          <button
            className={`${styles.filterBtn} ${selectedBrands.length > 0 ? styles.filterBtnActive : ''}`}
            onClick={() => setOpenPanel(prev => prev === 'brand' ? null : 'brand')}
          >
            제조사
            {selectedBrands.length > 0 && <span className={styles.badge}>{selectedBrands.length}</span>}
            <span className={`${styles.caret} ${openPanel === 'brand' ? styles.caretOpen : ''}`}>▾</span>
          </button>
          {openPanel === 'brand' && (
            <div className={styles.panel}>
              {brands.length === 0 ? (
                <p className={styles.panelEmpty}>브랜드 정보 없음</p>
              ) : brands.map(brand => (
                <label key={brand} className={styles.checkRow}>
                  <input type="checkbox" className={styles.checkbox}
                    checked={selectedBrands.includes(brand)}
                    onChange={() => toggleBrand(brand)} />
                  <span className={styles.checkLabel}>{brand}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* 가격 드롭다운 */}
        <div className={styles.dropdownWrap}>
          <button
            className={`${styles.filterBtn} ${selectedPrice.min > 0 || selectedPrice.max < Infinity ? styles.filterBtnActive : ''}`}
            onClick={() => setOpenPanel(prev => prev === 'price' ? null : 'price')}
          >
            {selectedPrice.label === '전체' ? '가격' : selectedPrice.label}
            <span className={`${styles.caret} ${openPanel === 'price' ? styles.caretOpen : ''}`}>▾</span>
          </button>
          {openPanel === 'price' && (
            <div className={styles.panel}>
              {PRICE_OPTIONS.map(opt => (
                <label key={opt.label} className={styles.radioRow}>
                  <input type="radio" className={styles.radio}
                    checked={selectedPrice.label === opt.label}
                    onChange={() => { setSelectedPrice(opt); setOpenPanel(null) }} />
                  <span className={styles.checkLabel}>{opt.label}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* 초기화 버튼 */}
        {hasFilter && (
          <button className={styles.resetBtn} onClick={resetAll}>✕ 초기화</button>
        )}

      </div>

    </div>
  )
}
