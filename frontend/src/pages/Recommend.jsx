import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/Recommend.module.css'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'

const CATEGORIES = [
  '냉장고', '세탁기', '건조기', '에어컨', '공기청정기',
  '로봇청소기', '식기세척기', '에어프라이어', 'TV', '선풍기',
]

const ENVIRONMENTS = [
  { label: '자취 · 1인', value: '1인 자취용' },
  { label: '신혼부부 · 2인', value: '신혼부부 2인' },
  { label: '4인 가족', value: '4인 가족 가정용' },
  { label: '사무실 · 업무용', value: '사무실 업무용' },
  { label: '어르신 · 부모님', value: '어르신 부모님용 사용하기 쉬운' },
]

const BUDGET_STEPS = [10, 20, 30, 50, 70, 100, 150, 200, 300, 500]

function fmtBudget(wan) {
  return wan >= 100 ? `${wan}만원 이하` : `${wan}만원 이하`
}

function ImgPlaceholder() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  )
}

export default function Recommend() {
  const navigate = useNavigate()
  const { isLoggedIn } = useAuth()

  const [budgetIdx, setBudgetIdx] = useState(5)
  const [category, setCategory] = useState(null)
  const [envIdx, setEnvIdx] = useState(null)
  const [advanced, setAdvanced] = useState('')

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const budgetWan = BUDGET_STEPS[budgetIdx]
  const canSubmit = !!category && envIdx !== null && !loading


  function buildQuery() {
    const env = ENVIRONMENTS[envIdx].value
    const budget = `${budgetWan}만원 이하`
    const extra = advanced.trim()
    return `${category} ${env} ${budget}${extra ? ' ' + extra : ''}`
  }

  async function handleSubmit() {
    if (!canSubmit) return
    const q = buildQuery()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res  = await fetch(`${API_BASE}/api/recommend?query=${encodeURIComponent(q)}`)
      const data = await res.json()
      if (data.error && !data.recommendations?.length) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch {
      setError('서버에 연결할 수 없습니다')
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setResult(null)
    setError(null)
  }

  return (
    <div className={styles.page}>
      <Navbar />
      <div className={styles.container}>

        {/* 헤더 */}
        <div className={styles.header}>
          <span className={styles.badge}>AI POWERED</span>
          <h1 className={styles.title}>딱 맞는 제품을 찾아드려요</h1>
          <p className={styles.subtitle}>조건을 선택하면 AI가 최적의 제품 3가지를 추천해드려요</p>
        </div>

        {/* ── 폼 (결과 없을 때만) ── */}
        {!result && (
          <div className={styles.form}>

            {/* Step 1: 예산 */}
            <div className={styles.step}>
              <p className={styles.stepLabel}>
                <span className={styles.stepNum}>1</span>예산
                <span className={styles.stepValue}>{fmtBudget(budgetWan)}</span>
              </p>
              <div className={styles.sliderWrap}>
                <span className={styles.sliderMin}>10만원</span>
                <input
                  type="range"
                  className={styles.slider}
                  min={0}
                  max={BUDGET_STEPS.length - 1}
                  value={budgetIdx}
                  style={{ '--pct': `${budgetIdx / (BUDGET_STEPS.length - 1) * 100}%` }}
                  onChange={e => { setBudgetIdx(Number(e.target.value)); setError(null) }}
                />
                <span className={styles.sliderMax}>500만원</span>
              </div>
              <div className={styles.sliderTicks}>
                {BUDGET_STEPS.map((w, i) => (
                  <span
                    key={w}
                    className={`${styles.tick} ${i === budgetIdx ? styles.tickActive : ''}`}
                    onClick={() => setBudgetIdx(i)}
                  >
                    {w}만
                  </span>
                ))}
              </div>
            </div>

            {/* Step 2: 카테고리 */}
            <div className={styles.step}>
              <p className={styles.stepLabel}>
                <span className={styles.stepNum}>2</span>카테고리
                {category && <span className={styles.stepValue}>{category}</span>}
              </p>
              <div className={styles.btnGrid}>
                {CATEGORIES.map(cat => (
                  <button
                    key={cat}
                    className={`${styles.optBtn} ${category === cat ? styles.optBtnActive : ''}`}
                    onClick={() => { setCategory(cat); setError(null) }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 3: 사용 환경 */}
            <div className={styles.step}>
              <p className={styles.stepLabel}>
                <span className={styles.stepNum}>3</span>사용 환경
                {envIdx !== null && <span className={styles.stepValue}>{ENVIRONMENTS[envIdx].label}</span>}
              </p>
              <div className={styles.btnGrid}>
                {ENVIRONMENTS.map((env, i) => (
                  <button
                    key={env.label}
                    className={`${styles.optBtn} ${envIdx === i ? styles.optBtnActive : ''}`}
                    onClick={() => { setEnvIdx(i); setError(null) }}
                  >
                    {env.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 추가 조건 (선택) */}
            <div className={styles.step}>
              <p className={styles.stepLabel}>
                <span className={styles.stepNum} style={{ opacity: 0.4 }}>+</span>
                추가 조건
                <span className={styles.stepOptional}>선택</span>
              </p>
              <input
                className={styles.advInput}
                placeholder="예: 조용한, 에너지효율 1등급, 인버터 방식..."
                value={advanced}
                onChange={e => setAdvanced(e.target.value)}
              />
            </div>

            {/* 에러 */}
            {error && (
              <div className={styles.errorWrap}>
                <p className={styles.errorText}>{error}</p>
                <div className={styles.errorBtns}>
                  {/* 에러 메시지에서 제안 예산 추출해 슬라이더 자동 이동 */}
                  {(() => {
                    const m = error.match(/(\d+)만원 이상/)
                    if (!m) return null
                    const suggestWan = parseInt(m[1], 10)
                    const suggestIdx = BUDGET_STEPS.findIndex(s => s >= suggestWan)
                    if (suggestIdx < 0) return null
                    return (
                      <button className={styles.suggestBtn} onClick={() => {
                        setBudgetIdx(suggestIdx)
                        setError(null)
                      }}>
                        예산 {suggestWan}만원으로 올리기
                      </button>
                    )
                  })()}
                  <button className={styles.retryBtn} onClick={() => setError(null)}>
                    조건 다시 선택
                  </button>
                </div>
              </div>
            )}

            {/* 추천받기 버튼 */}
            {isLoggedIn ? (
              <button
                className={styles.submitBtn}
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                {loading
                  ? <><span className={styles.btnSpinner} /> AI 분석 중...</>
                  : '추천받기 →'
                }
              </button>
            ) : (
              <div className={styles.loginGate}>
                <span className={styles.loginGateIcon}>🔒</span>
                <p className={styles.loginGateText}>로그인 후 AI 추천을 받을 수 있어요</p>
                <button className={styles.loginGateBtn} onClick={() => navigate('/login')}>
                  로그인하기 →
                </button>
              </div>
            )}

            {isLoggedIn && !canSubmit && !loading && (
              <p className={styles.hint}>
                {!category ? '카테고리를 선택해주세요' : '사용 환경을 선택해주세요'}
              </p>
            )}

          </div>
        )}

        {/* 로딩 */}
        {loading && (
          <div className={styles.loadingWrap}>
            <div className={styles.spinner} />
            <p className={styles.loadingText}>AI가 제품을 분석하고 있어요...</p>
            <p className={styles.loadingSubText}>네이버 쇼핑 데이터를 기반으로 최적 제품을 선별 중입니다</p>
          </div>
        )}

        {/* ── 결과 ── */}
        {result && (
          <div className={styles.results}>
            <div className={styles.resultsHeader}>
              <p className={styles.resultsLabel}>
                <span className={styles.queryChip}>"{result.search_term}"</span> 기준 {result.ai_limited ? '인기순 TOP 3' : 'AI 추천 TOP 3'}
              </p>
              <button className={styles.resetBtn} onClick={handleReset}>← 다시 선택</button>
            </div>
            {result.ai_limited && (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                AI 분석이 일시적으로 제한되어 인기·평점 기준으로 정렬했습니다.
              </p>
            )}

            <div className={styles.cards}>
              {result.recommendations.map((item, i) => (
                <div
                  key={i}
                  className={`${styles.card} ${i === 0 ? styles.cardFirst : ''}`}
                >
                  <div className={styles.rank}>{i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}</div>

                  <div className={styles.cardImg}>
                    {item.image
                      ? <img src={item.image} alt={item.title} />
                      : <div className={styles.imgPlaceholder}><ImgPlaceholder /></div>
                    }
                    {item.highlight && (
                      <span className={styles.highlightBadge}>{item.highlight}</span>
                    )}
                  </div>

                  <div className={styles.cardBody}>
                    <p className={styles.cardTitle}>{item.title}</p>
                    <p className={styles.cardPrice}>
                      {item.price > 0 ? `${item.price.toLocaleString()}원` : '가격 미정'}
                    </p>
                    {item.reviewScore > 0 && (
                      <p className={styles.cardReview}>
                        ★ {item.reviewScore.toFixed(1)}
                        <span className={styles.reviewCount}> ({item.reviewCount.toLocaleString()}개)</span>
                      </p>
                    )}
                    <p className={styles.cardReason}>{item.reason}</p>

                    <div className={styles.cardBtns}>
                      <button
                        className={styles.analyzeBtn}
                        onClick={() => navigate(`/report/${item.id}`, {
                          state: { product: item, category }
                        })}
                      >
                        분석 보기
                      </button>
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.buyBtn}
                      >
                        네이버 구매 →
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
