import { useState, useEffect, useRef } from 'react'
import styles from '../../styles/FilterBar.module.css'

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

export default function FilterBar({ products, onSearchChange, onFilterChange, onSortChange }) {
  const [search, setSearch] = useState('')
  // css-skill #1: 평소엔 아이콘만(40px 원), 클릭하면 너비 확장
  const [searchExpanded, setSearchExpanded] = useState(false)
  const [openPanel, setOpenPanel] = useState(null)
  const [selectedBrands, setSelectedBrands] = useState([])
  const [selectedPrice, setSelectedPrice] = useState(PRICE_OPTIONS[0])
  const [selectedSort, setSelectedSort] = useState(SORT_OPTIONS[0])
  const barRef = useRef(null)
  const searchInputRef = useRef(null)

  const brands = [...new Set(products.map(p => p.brand).filter(Boolean))].sort()

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
