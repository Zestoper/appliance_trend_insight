import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import s from '../styles/B2BHome.module.css'
import anim from '../styles/animations.module.css'
import { useInView } from '../hooks/useInView'

const TYPING_PHRASES = [
  'AI가 에어컨 매입 전략 수립 중',
  '냉장고 수요 예측 모델 실행 중',
  '로봇청소기 재고 최적 시점 분석 중',
  '가전 카테고리 의사결정 인사이트 도출 중',
]

function useTypingEffect(phrases) {
  const [displayed, setDisplayed] = useState('')
  const [phraseIdx, setPhraseIdx] = useState(0)
  const [charIdx, setCharIdx] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const current = phrases[phraseIdx]
    const speed = deleting ? 38 : 75

    const timeout = setTimeout(() => {
      if (!deleting && charIdx === current.length) {
        setTimeout(() => setDeleting(true), 1800)
        return
      }
      if (deleting && charIdx === 0) {
        setDeleting(false)
        setPhraseIdx(i => (i + 1) % phrases.length)
        return
      }
      setDisplayed(current.slice(0, charIdx + (deleting ? -1 : 1)))
      setCharIdx(i => i + (deleting ? -1 : 1))
    }, speed)

    return () => clearTimeout(timeout)
  }, [charIdx, deleting, phraseIdx, phrases])

  return displayed
}

const FEATURES = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
      </svg>
    ),
    title: 'AI 전략 리포트',
    desc: 'RAG 강화 AI가 "매입 확대·재고 전략·판매 시점"을 직접 지시하는 의사결정 리포트',
    path: '/b2b/report',
    cta: '리포트 열기',
    color: '#6366f1',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
        <polyline points="17 6 23 6 23 12" />
      </svg>
    ),
    title: '미래 예측',
    desc: 'Prophet + XGBoost 앙상블 모델로 향후 수요 피크를 예측하고 재고 전략을 제시',
    path: '/b2b/forecast',
    cta: '예측 보기',
    color: '#10b981',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    title: '시장 트렌드 분석',
    desc: '카테고리별 검색량·브랜드 점유율·연령대 관심도를 한 화면에서 파악',
    path: '/b2b/dashboard',
    cta: '대시보드 열기',
    color: '#a855f7',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
    title: '가격 인텔리전스',
    desc: '카테고리·브랜드별 실시간 가격 분포와 이력을 추적해 최적 매입가를 파악',
    path: '/b2b/price',
    cta: '가격 분석',
    color: '#f59e0b',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
    ),
    title: '제품 심층 분석',
    desc: '뉴스·리뷰·DataLab·유튜브를 통합해 개별 제품의 시장 포지션과 경쟁사를 진단',
    path: '/products/냉장고',
    cta: '리포트 보기',
    color: '#ec4899',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    title: '구매 타이밍 분석',
    desc: '90일 검색 관심도 추이로 시장 수요가 고점/저점인 시점을 사전에 포착',
    path: '/timing',
    cta: '타이밍 확인',
    color: '#06b6d4',
  },
]

const STATS = [
  { value: '4개', label: '통합 데이터 소스' },
  { value: '10개', label: '가전 카테고리' },
  { value: '실시간', label: '데이터 업데이트' },
  { value: 'AI', label: 'Groq 분석 엔진' },
]

function AccessGate({ user, navigate }) {
  if (!user) {
    return (
      <div className={s.gate}>
        <div className={s.gateIcon}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <p className={s.gateTitle}>B2B 전용 서비스입니다</p>
        <p className={s.gateDesc}>B2B 계정으로 로그인하면 모든 기능을 이용할 수 있어요</p>
        <div className={s.gateBtns}>
          <button className={s.gateBtnPrimary} onClick={() => navigate('/login')}>로그인</button>
          <button className={s.gateBtnSecondary} onClick={() => navigate('/signup')}>B2B 가입 신청</button>
        </div>
      </div>
    )
  }
  if (user.user_type !== 'b2b' && user.role !== 'admin') {
    return (
      <div className={s.gate}>
        <div className={s.gateIcon}>🏢</div>
        <p className={s.gateTitle}>B2B 계정이 필요합니다</p>
        <p className={s.gateDesc}>현재 계정은 B2C 계정입니다. B2B 서비스를 이용하려면 별도 가입이 필요해요</p>
        <button className={s.gateBtnPrimary} onClick={() => navigate('/signup')}>B2B 가입 신청</button>
      </div>
    )
  }
  if (user.status === 'pending') {
    return (
      <div className={s.gate}>
        <div className={s.gateIcon}>⏳</div>
        <p className={s.gateTitle}>승인 대기 중</p>
        <p className={s.gateDesc}>관리자 승인 후 모든 B2B 기능을 이용할 수 있어요. 보통 1~2 영업일이 소요됩니다</p>
      </div>
    )
  }
  return null
}

const STEPS = [
  {
    num: '01',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </svg>
    ),
    title: '데이터 수집',
    desc: '네이버 쇼핑·뉴스·DataLab 등 4가지 소스에서 가전 시장 데이터를 실시간으로 수집합니다',
    color: '#6366f1',
  },
  {
    num: '02',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
    title: 'AI 분석',
    desc: 'Groq LLM이 수집된 데이터를 분석해 소비자 트렌드와 시장 기회를 자동으로 파악합니다',
    color: '#a855f7',
  },
  {
    num: '03',
    icon: (
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
        <line x1="2" y1="20" x2="22" y2="20" />
      </svg>
    ),
    title: '의사결정 지원',
    desc: '"매입 확대·재고 전략·판매 타이밍" — AI가 직접 결론을 내려 유통 의사결정을 돕습니다',
    color: '#06b6d4',
  },
]

const DELAYS = [anim.delay0, anim.delay100, anim.delay200, anim.delay300, anim.delay300, anim.delay300]

export default function B2BHome() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const typingText = useTypingEffect(TYPING_PHRASES)

  const statsRef    = useInView({ threshold: 0.1 })
  const gateRef     = useInView({ threshold: 0.1 })
  const gridRef     = useInView({ threshold: 0.05 })
  const workflowRef = useInView({ threshold: 0.1 })

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'

  return (
    <div className={s.page}>
      <Navbar />

      <div className={s.scrollBody} data-scroll-container>

        {/* ── 히어로 ── */}
        <div className={s.hero}>
          <div className={s.blobWrap}>
            <div className={`${s.blob} ${s.blobIndigo}`} />
            <div className={`${s.blob} ${s.blobViolet}`} />
            <div className={`${s.blob} ${s.blobCyan}`} />
          </div>

          <div className={s.heroContent}>
            <span className={s.badge}>✦ B2B 가전 시장 인사이트 플랫폼</span>
            <h1 className={s.headline}>
              가전 시장 데이터로
              <span className={s.gradientText}>비즈니스 인사이트를 얻으세요</span>
            </h1>
            <p className={s.subtitle}>
              지금 이 순간,&nbsp;
              <span className={s.typingText}>{typingText}</span>
            </p>
            {isB2BActive && (
              <div className={s.heroBtns}>
                <button className={s.btnPrimary} onClick={() => navigate('/b2b/report')}>
                  AI 전략 리포트 →
                </button>
                <button className={s.btnSecondary} onClick={() => navigate('/b2b/forecast')}>
                  미래 예측 보기
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── 워크플로우 ── */}
        <div className={s.workflow}>
          <div className={s.workflowHeader}>
            <span className={s.workflowBadge}>✦ 어떻게 작동하나요</span>
            <h2 className={s.workflowTitle}>3단계로 시장 인사이트를 얻으세요</h2>
            <p className={s.workflowSub}>복잡한 데이터 수집과 분석을 AI가 자동으로 처리합니다</p>
          </div>
          <div className={s.workflowSteps} ref={workflowRef.ref}>
            {STEPS.map((step, i) => (
              <div key={step.num} className={s.stepWrap}>
                <div
                  className={`${s.workflowStep} ${anim.hidden} ${workflowRef.inView ? anim.visible : ''} ${DELAYS[i]}`}
                  style={{ '--step-color': step.color }}
                >
                  <div className={s.stepNumBadge}>{step.num}</div>
                  <div className={s.stepIconWrap}>{step.icon}</div>
                  <h3 className={s.stepTitle}>{step.title}</h3>
                  <p className={s.stepDesc}>{step.desc}</p>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={s.stepArrow}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── 기능 카드 ── */}
        <div className={s.featSection}>
          <div className={s.container}>

            <div
              ref={statsRef.ref}
              className={`${s.statsRow} ${anim.hidden} ${statsRef.inView ? anim.visible : ''}`}
            >
              {STATS.map(st => (
                <div key={st.label} className={s.statItem}>
                  <span className={s.statValue}>{st.value}</span>
                  <span className={s.statLabel}>{st.label}</span>
                </div>
              ))}
            </div>

            {!isB2BActive && (
              <div
                ref={gateRef.ref}
                className={`${anim.hidden} ${gateRef.inView ? anim.visible : ''}`}
              >
                <AccessGate user={user} navigate={navigate} />
              </div>
            )}

            <div ref={gridRef.ref} className={s.featureGrid}>
              {FEATURES.map((f, i) => (
                <div
                  key={f.title}
                  className={`${s.featureCard} ${!isB2BActive ? s.featureCardLocked : ''} ${anim.hidden} ${gridRef.inView ? anim.visible : ''} ${DELAYS[i]}`}
                  style={{ '--card-color': f.color }}
                  onClick={() => isB2BActive && navigate(f.path)}
                >
                  <div className={s.featureAccent} />
                  <div className={s.featureIcon}>{f.icon}</div>
                  <h3 className={s.featureTitle}>{f.title}</h3>
                  <p className={s.featureDesc}>{f.desc}</p>
                  {isB2BActive && (
                    <span className={s.featureCta}>{f.cta} →</span>
                  )}
                  {!isB2BActive && <span className={s.featureLock}>🔒</span>}
                </div>
              ))}
            </div>

          </div>
        </div>

      </div>
    </div>
  )
}
