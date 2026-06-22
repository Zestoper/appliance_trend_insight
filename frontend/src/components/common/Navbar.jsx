import { useState, useRef, useEffect } from 'react'
import styles from '../../styles/Navbar.module.css'
import { useTheme } from '../../context/ThemeContext'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const SERVICE_ITEMS = [
  {
    label: '제품 비교',
    desc: '두 제품을 나란히 비교 분석',
    path: '/compare',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="8" height="18" rx="2" />
        <rect x="14" y="3" width="8" height="18" rx="2" />
        <line x1="10" y1="8" x2="14" y2="8" />
        <line x1="10" y1="12" x2="14" y2="12" />
        <line x1="10" y1="16" x2="14" y2="16" />
      </svg>
    ),
  },
  {
    label: '구매 타이밍',
    desc: '가격 추이로 최적 구매 시점 분석',
    path: '/timing',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 17 7 11 11 14 15 8 21 14" />
        <line x1="3" y1="21" x2="21" y2="21" />
        <circle cx="21" cy="7" r="3" />
      </svg>
    ),
  },
  {
    label: 'AI 추천',
    desc: '내 조건에 딱 맞는 제품을 AI 추천',
    path: '/recommend',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
      </svg>
    ),
  },
  {
    label: 'AI 트렌드 분석',
    desc: 'RAG 기반 가전 트렌드 리포트 생성',
    path: '/chat',
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
]


const B2B_ITEMS = [
  {
    label: '시장 분석',
    desc: '카테고리별 검색 관심도·트렌드',
    path: '/b2b/dashboard',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    label: '가격 분석',
    desc: '브랜드·구간별 가격 현황 분석',
    path: '/b2b/price',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    label: '미래 예측',
    desc: '선형 회귀 기반 수요 트렌드 예측',
    path: '/b2b/forecast',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 17 7 11 11 14 15 8 21 14" />
        <polyline points="17 8 21 8 21 12" />
      </svg>
    ),
  },
  {
    label: 'AI 전략 리포트',
    desc: 'AI가 생성하는 시장 분석 리포트',
    path: '/b2b/report',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
]

const _ALL_APPLIANCE_TERMS = [
  '에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기',
  'TV', '텔레비전', '에어프라이어', '전기밥솥', '밥솥', '전자레인지', '커피머신',
  '믹서기', '전기포트', '사운드바', '스피커', '프로젝터', '가습기', '제습기',
  '선풍기', '히터', '전기히터', '헤어드라이어', '청소기', '냉난방기', '세탁건조기',
  '인덕션', '전기레인지', '오븐', '스타일러', '의류관리기', '정수기', '제빙기',
]

const PRODUCT_CATEGORIES = [
  {
    name: '생활가전',
    items: ['냉장고', '세탁기', '건조기', '에어컨', '공기청정기', '로봇청소기', '식기세척기'],
  },
  {
    name: '주방가전',
    items: ['에어프라이어', '전기밥솥', '전자레인지', '커피머신', '믹서기', '전기포트'],
  },
  {
    name: '영상/음향',
    items: ['TV', '사운드바', '블루투스 스피커', '프로젝터'],
  },
  {
    name: '계절가전',
    items: ['가습기', '제습기', '선풍기', '전기히터'],
  },
  {
    name: '개인가전',
    items: ['헤어드라이어', '헤어스타일러', '전동칫솔', '전기면도기'],
  },
]

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState(() => localStorage.getItem('navMode') ?? 'b2c')
  const B2B_ONLY_PATHS = ['/b2b', '/b2b/dashboard', '/b2b/price', '/b2b/report', '/b2b/forecast']
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [scrollProgress, setScrollProgress] = useState(0)
  const [isHidden, setIsHidden] = useState(false)
  const [openDropdown, setOpenDropdown] = useState(null)
  const [searchError, setSearchError] = useState('')
  const lastScrollY = useRef(0)
  const searchInputRef = useRef(null)
  const navRef = useRef(null)
  const { isDark, toggle } = useTheme()
  const { isLoggedIn, user, logout } = useAuth()

  useEffect(() => {
    if (!user) {
      // 로그아웃 시 플래그 초기화
      sessionStorage.removeItem('navModeSet')
      return
    }
    // 이미 이번 세션에서 자동 감지했으면 재실행 안 함
    // (B2B 유저가 수동으로 B2C 전환 후 페이지 이동해도 유지됨)
    if (sessionStorage.getItem('navModeSet')) return

    if (user.user_type === 'b2b') {
      setMode('b2b')
      localStorage.setItem('navMode', 'b2b')
    } else if (user.user_type !== 'b2b' && user.role !== 'admin') {
      setMode('b2c')
      localStorage.setItem('navMode', 'b2c')
    }
    sessionStorage.setItem('navModeSet', '1')
  }, [user])

  // 라우트 이동 시 항상 네비바 표시 (이전 페이지 스크롤 상태 초기화)
  useEffect(() => {
    setIsHidden(false)
  }, [location.pathname])

  useEffect(() => {
    const container = document.querySelector('[data-scroll-container]')
    const onScroll = () => {
      const scrollTop = container ? container.scrollTop : window.scrollY
      const scrollHeight = container ? container.scrollHeight : document.body.scrollHeight
      const clientHeight = container ? container.clientHeight : window.innerHeight
      setScrollProgress(Math.round((scrollTop / Math.max(scrollHeight - clientHeight, 1)) * 100))
      setIsHidden(scrollTop > 0)
      lastScrollY.current = scrollTop
    }
    if (container) {
      container.addEventListener('scroll', onScroll)
      return () => container.removeEventListener('scroll', onScroll)
    }
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [location.pathname])

  // 드롭다운 열릴 때 스크롤 잠금
  useEffect(() => {
    const container = document.querySelector('[data-scroll-container]')
    const target = container ?? document.body
    if (openDropdown !== null) {
      target.style.overflow = 'hidden'
    } else {
      target.style.overflow = ''
    }
    return () => { target.style.overflow = '' }
  }, [openDropdown])

  useEffect(() => {
    function handleClickOutside(e) {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpenDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function openSearch() {
    setIsSearchOpen(true)
    setTimeout(() => searchInputRef.current?.focus(), 60)
  }

  function closeSearch() {
    setIsSearchOpen(false)
    if (searchInputRef.current) searchInputRef.current.value = ''
  }

  function handleNavSearch(e) {
    if (e.nativeEvent.isComposing) return
    if (e.key === 'Enter') {
      const q = searchInputRef.current?.value.trim()
      if (!q) return
      const isAppliance = _ALL_APPLIANCE_TERMS.some(t => q.includes(t) || t.includes(q))
      if (!isAppliance) {
        setSearchError('가전제품 키워드를 입력해주세요 (예: 에어컨, 냉장고)')
        return
      }
      setSearchError('')
      setOpenDropdown(null)
      closeSearch()
      navigate(`/products/${encodeURIComponent(q)}`)
    }
    setSearchError('')
  }

  function toggleDropdown(key) {
    setOpenDropdown(prev => (prev === key ? null : key))
  }

  return (
    <>
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${scrollProgress}%` }} />
      </div>

      <div
        ref={navRef}
        className={`${styles.navOuter} ${isHidden ? styles.navHidden : ''}`}
      >
        <nav className={styles.navbar}>

          <div className={styles.logo}
            onClick={() => navigate(mode === 'b2b' ? '/b2b' : '/')}
            style={{ cursor: 'pointer' }}>
            <svg className={styles.logoIcon} viewBox="0 0 48 52" fill="none" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="lgGrad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#9333ea"/>
                  <stop offset="100%" stopColor="#ec4899"/>
                </linearGradient>
              </defs>
              {/* 플러그 프롱 (왼쪽) */}
              <rect x="13" y="2" width="8" height="13" rx="3.5" fill="url(#lgGrad)"/>
              {/* 플러그 프롱 (오른쪽) */}
              <rect x="27" y="2" width="8" height="13" rx="3.5" fill="url(#lgGrad)"/>
              {/* 바디 */}
              <rect x="3" y="11" width="42" height="37" rx="10" fill="url(#lgGrad)"/>
              {/* 막대 차트 — 왼쪽 */}
              <rect x="10" y="31" width="8" height="10" rx="2.5" fill="white" fillOpacity="0.9"/>
              {/* 막대 차트 — 가운데 */}
              <rect x="20" y="23" width="8" height="18" rx="2.5" fill="white" fillOpacity="0.9"/>
              {/* 막대 차트 — 오른쪽 */}
              <rect x="30" y="27" width="8" height="14" rx="2.5" fill="white" fillOpacity="0.9"/>
            </svg>
            <span className={styles.logoText}>가전무쌍</span>
            {mode === 'b2b' && <span className={styles.b2bBadge}>B2B</span>}
          </div>

          <ul className={styles.navItems}>
            <li
              className={`${styles.navItem} ${openDropdown === 'product' ? styles.navItemActive : ''}`}
              onClick={() => toggleDropdown('product')}
            >
              제품
              <span className={`${styles.navCaret} ${openDropdown === 'product' ? styles.navCaretOpen : ''}`}>▾</span>
            </li>
            <li
              className={`${styles.navItem} ${openDropdown === 'service' ? styles.navItemActive : ''}`}
              onClick={() => toggleDropdown('service')}
            >
              서비스
              <span className={`${styles.navCaret} ${openDropdown === 'service' ? styles.navCaretOpen : ''}`}>▾</span>
            </li>
            <li
              className={styles.navItem}
              onClick={() => { setOpenDropdown(null); navigate('/trend') }}
            >
              트렌드
            </li>
            {mode === 'b2b' && (
              <li
                className={`${styles.navItem} ${openDropdown === 'b2b' ? styles.navItemActive : ''}`}
                onClick={() => toggleDropdown('b2b')}
              >
                B2B 분석
                <span className={`${styles.navCaret} ${openDropdown === 'b2b' ? styles.navCaretOpen : ''}`}>▾</span>
              </li>
            )}
          </ul>

          <div className={styles.navRight}>
            <div className={`${styles.searchToggle} ${isSearchOpen ? styles.searchOpen : ''}`}>
              <button className={styles.searchIconBtn} onClick={openSearch} aria-label="검색">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <line x1="16.5" y1="16.5" x2="22" y2="22" />
                </svg>
              </button>
              <input
                ref={searchInputRef}
                className={styles.searchInput}
                placeholder="제품 검색..."
                onBlur={closeSearch}
                onKeyDown={handleNavSearch}
              />
              <button
                className={styles.searchCloseBtn}
                onMouseDown={e => e.preventDefault()}
                onClick={closeSearch}
                aria-label="닫기"
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            {searchError && (
              <div className={styles.searchError}>{searchError}</div>
            )}

            <div className={styles.toggle}>
              <div className={`${styles.toggleSlider} ${mode === 'b2b' ? styles.toggleSliderRight : ''}`} />
              <button
                onClick={() => {
                  setMode('b2c')
                  localStorage.setItem('navMode', 'b2c')
                  navigate('/', { replace: true })
                }}
                className={`${styles.toggleBtn} ${mode === 'b2c' ? styles.toggleBtnActive : ''}`}
              >
                개인
              </button>
              <button
                onClick={() => {
                  setMode('b2b')
                  localStorage.setItem('navMode', 'b2b')
                  navigate('/b2b', { replace: true })
                }}
                className={`${styles.toggleBtn} ${mode === 'b2b' ? styles.toggleBtnActive : ''}`}
              >
                기업
              </button>
            </div>

            <button
              className={`${styles.themeToggle} ${isDark ? '' : styles.themeLightMode}`}
              onClick={toggle}
              aria-label="테마 전환"
            >
              <span className={`${styles.themeThumb} ${isDark ? '' : styles.themeThumbRight}`}>
                {isDark ? '🌙' : '☀️'}
              </span>
            </button>

            {isLoggedIn ? (
              <div className={styles.userWrap}>
                {user?.role === 'admin' && (
                  <button className={styles.adminBtn} onClick={() => navigate('/admin')}>
                    🛡️ 관리자
                  </button>
                )}
                <span className={styles.userName} onClick={() => navigate('/mypage')} style={{ cursor: 'pointer' }}>
                  {user?.nickname || user?.company_name || user?.email}
                </span>
                <button className={styles.logoutBtn} onClick={logout}>로그아웃</button>
              </div>
            ) : (
              <button className={styles.ctaBtn} onClick={() => navigate('/login')}>
                시작하기 →
              </button>
            )}
          </div>

        </nav>

        <div className={`${styles.dropdown} ${openDropdown === 'product' ? styles.dropdownOpen : ''}`}>
          <div className={styles.dropdownGrid}>
            {PRODUCT_CATEGORIES.map(cat => (
              <div key={cat.name} className={styles.dropdownCol}>
                <p className={styles.dropdownCatName}>{cat.name}</p>
                <ul className={styles.dropdownItems}>
                  {cat.items.map(item => (
                    <li
                      key={item}
                      className={styles.dropdownItem}
                      onClick={() => { setOpenDropdown(null); navigate(`/products/${item}`) }}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.dropdown} ${openDropdown === 'service' ? styles.dropdownOpen : ''}`}>
          <div className={styles.dropdownServiceGrid}>
            {SERVICE_ITEMS.map(item => (
              <div
                key={item.path}
                className={styles.serviceCard}
                onClick={() => { setOpenDropdown(null); navigate(item.path, B2B_ONLY_PATHS.includes(location.pathname) ? { replace: true } : {}) }}
              >
                <div className={styles.serviceCardIcon}>{item.icon}</div>
                <div>
                  <p className={styles.serviceCardLabel}>{item.label}</p>
                  <p className={styles.serviceCardDesc}>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={`${styles.dropdown} ${openDropdown === 'b2b' ? styles.dropdownOpen : ''}`}>
          <div className={styles.dropdownB2bGrid}>
            {B2B_ITEMS.map(item => (
              <div
                key={item.path}
                className={styles.b2bCard}
                onClick={() => { setOpenDropdown(null); navigate(item.path) }}
              >
                <div className={styles.b2bCardIcon}>{item.icon}</div>
                <div>
                  <p className={styles.b2bCardLabel}>{item.label}</p>
                  <p className={styles.b2bCardDesc}>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </>
  )
}
