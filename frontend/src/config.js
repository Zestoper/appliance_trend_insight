export const API_BASE = import.meta.env.VITE_API_BASE ?? ''
export const TOSS_CLIENT_KEY = import.meta.env.VITE_TOSS_CLIENT_KEY ?? ''
// 개발용 우회: true면 토스 결제창을 열지 않고 바로 결제 승인 처리 (백엔드 SKIP_PAYMENT_VERIFICATION과 함께 사용)
export const SKIP_PAYMENT_VERIFICATION = (import.meta.env.VITE_SKIP_PAYMENT_VERIFICATION ?? '') === 'true'

export const TIER_RANK = { free: 0, silver: 1, gold: 2, platinum: 3 }
export const TIER_LABEL = { free: '무료', silver: '실버', gold: '골드', platinum: '플래티넘' }
export const TIER_PRICES = { silver: 2900, gold: 5900, platinum: 9900 }

export function hasTier(userTier, required) {
  return (TIER_RANK[userTier] ?? 0) >= (TIER_RANK[required] ?? 0)
}
