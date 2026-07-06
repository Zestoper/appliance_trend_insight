import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import { API_BASE, TOSS_CLIENT_KEY, TIER_LABEL, SKIP_PAYMENT_VERIFICATION } from '../config'
import s from '../styles/B2BPricing.module.css'

const FREE_PLAN = {
  tier: 'free',
  name: '무료',
  price: 0,
  tagline: '가입만 하면 바로 이용',
  features: [
    '시장 트렌드 대시보드 열람 (일부 블러 처리)',
    '카테고리·기간별 검색 관심도 조회',
    '브랜드 점유율 · 연령대 데이터 기본 열람',
  ],
}

const PLANS = [
  {
    tier: 'silver',
    name: '실버',
    price: 2900,
    tagline: '대시보드 전체 열람',
    features: [
      '시장 트렌드 대시보드 무제한 열람',
      'AI 종합 분석 · 불만 키워드 근거 블러 해제',
      '브랜드 점유율 · 소비층 데이터 전체 공개',
    ],
  },
  {
    tier: 'gold',
    name: '골드',
    price: 5900,
    tagline: '실버 + AI 기능 전체',
    highlight: true,
    features: [
      '실버 등급의 모든 기능',
      'AI 전략 리포트 생성 (매입·재고 의사결정)',
      'Prophet + XGBoost 수요 예측',
      '가격 인텔리전스 · AI 가격 인사이트',
    ],
  },
  {
    tier: 'platinum',
    name: '플래티넘',
    price: 9900,
    tagline: '골드 + 인쇄/내보내기',
    features: [
      '골드 등급의 모든 기능',
      '종합 리포트 인쇄용 PDF 출력',
      '리포트 엑셀(.xlsx) 다운로드',
    ],
  },
]

export default function B2BPricing() {
  const navigate = useNavigate()
  const { user, token, updateUser } = useAuth()
  const [loadingTier, setLoadingTier] = useState(null)
  const [error, setError] = useState(null)

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'
  const currentTier = user?.tier ?? 'free'

  if (!isB2BActive) {
    return (
      <div className={s.page}>
        <Navbar />
        <div className={s.denied}>
          <p className={s.deniedTitle}>
            {!user ? '로그인이 필요합니다' : user.user_type !== 'b2b' ? 'B2B 계정 전용입니다' : '승인 대기 중입니다'}
          </p>
          <button className={s.deniedBtn} onClick={() => navigate(!user ? '/login' : '/b2b')}>
            {!user ? '로그인' : 'B2B 홈으로'}
          </button>
        </div>
      </div>
    )
  }

  async function handleSubscribe(tier, price, name) {
    if (!SKIP_PAYMENT_VERIFICATION && !window.TossPayments) {
      setError('결제 모듈을 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.')
      return
    }
    setError(null)
    setLoadingTier(tier)
    try {
      const res = await fetch(`${API_BASE}/api/payments/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ tier }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '주문 생성에 실패했습니다')

      // 개발용 우회: 결제창 없이 바로 승인 처리 (백엔드 SKIP_PAYMENT_VERIFICATION=true일 때만 통과)
      if (SKIP_PAYMENT_VERIFICATION) {
        const confirmRes = await fetch(`${API_BASE}/api/payments/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ paymentKey: 'dev_bypass', orderId: data.orderId, amount: data.amount }),
        })
        const confirmData = await confirmRes.json()
        if (!confirmRes.ok) throw new Error(confirmData.detail || '결제 승인에 실패했습니다')
        updateUser({ tier: confirmData.tier, tier_expires_at: confirmData.tier_expires_at })
        setLoadingTier(null)
        navigate('/b2b/dashboard')
        return
      }

      const tossPayments = window.TossPayments(TOSS_CLIENT_KEY)
      await tossPayments.requestPayment('카드', {
        amount: data.amount,
        orderId: data.orderId,
        orderName: data.orderName,
        customerName: user?.company_name || user?.email || '가전무쌍 회원',
        customerEmail: user?.email,
        successUrl: `${window.location.origin}/b2b/payments/success`,
        failUrl: `${window.location.origin}/b2b/payments/fail`,
      })
    } catch (e) {
      setError(e.message || '결제를 시작할 수 없습니다')
      setLoadingTier(null)
    }
  }

  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.container}>
        <div className={s.header}>
          <p className={s.eyebrow}>B2B 요금제</p>
          <h1 className={s.title}>등급을 선택하세요</h1>
          <p className={s.sub}>
            현재 등급: <strong>{TIER_LABEL[currentTier]}</strong>
            {user?.tier_expires_at && currentTier !== 'free' && (
              <> · {new Date(user.tier_expires_at).toLocaleDateString('ko-KR')}까지</>
            )}
          </p>
        </div>

        {error && <div className={s.errorBox}>{error}</div>}

        <div className={s.grid}>
          <div className={s.card}>
            <p className={s.planName}>{FREE_PLAN.name}</p>
            <p className={s.planTagline}>{FREE_PLAN.tagline}</p>
            <p className={s.planPrice}>
              {FREE_PLAN.price.toLocaleString()}<span className={s.planPriceUnit}>원 / 월</span>
            </p>
            <ul className={s.featureList}>
              {FREE_PLAN.features.map(f => (
                <li key={f} className={s.featureItem}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
            <button className={`${s.subscribeBtn} ${s.subscribeBtnCurrent}`} disabled>
              {currentTier === 'free' ? '이용 중' : '기본 제공'}
            </button>
          </div>
          {PLANS.map(plan => {
            const isCurrent = currentTier === plan.tier
            return (
              <div key={plan.tier} className={`${s.card} ${plan.highlight ? s.cardHighlight : ''}`}>
                {plan.highlight && <span className={s.badge}>가장 많이 선택</span>}
                <p className={s.planName}>{plan.name}</p>
                <p className={s.planTagline}>{plan.tagline}</p>
                <p className={s.planPrice}>
                  {plan.price.toLocaleString()}<span className={s.planPriceUnit}>원 / 월</span>
                </p>
                <ul className={s.featureList}>
                  {plan.features.map(f => (
                    <li key={f} className={s.featureItem}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  className={`${s.subscribeBtn} ${isCurrent ? s.subscribeBtnCurrent : ''}`}
                  disabled={isCurrent || loadingTier === plan.tier}
                  onClick={() => handleSubscribe(plan.tier, plan.price, plan.name)}
                >
                  {isCurrent ? '이용 중' : loadingTier === plan.tier ? '결제창 여는 중...' : '구독하기'}
                </button>
              </div>
            )
          })}
        </div>

        <p className={s.footnote}>
          결제는 토스페이먼츠 결제창을 통해 진행되며, 매월 직접 재결제하는 단건 결제 방식입니다.
        </p>
      </div>
    </div>
  )
}
