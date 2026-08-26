export const API_BASE = import.meta.env.VITE_API_BASE ?? ''
// 쿠팡파트너스 최종 승인 심사(실제 게시된 링크 스크린샷)용 — 승인 후 API 키 발급되면
// 상품별 동적 딥링크 생성으로 교체 예정. 그 전까지는 승인용으로 발급받은 고정 링크를 사용한다.
export const COUPANG_PARTNER_LINK = 'https://link.coupang.com/a/gwCNvEqcNg'
export const TOSS_CLIENT_KEY = import.meta.env.VITE_TOSS_CLIENT_KEY ?? ''
// 개발용 우회: true면 토스 결제창을 열지 않고 바로 결제 승인 처리 (백엔드 SKIP_PAYMENT_VERIFICATION과 함께 사용)
export const SKIP_PAYMENT_VERIFICATION = (import.meta.env.VITE_SKIP_PAYMENT_VERIFICATION ?? '') === 'true'

export const TIER_RANK = { free: 0, silver: 1, gold: 2, platinum: 3 }
export const TIER_LABEL = { free: '무료', silver: '실버', gold: '골드', platinum: '플래티넘' }
export const TIER_PRICES = { silver: 2900, gold: 5900, platinum: 9900 }

export function hasTier(userTier, required) {
  return (TIER_RANK[userTier] ?? 0) >= (TIER_RANK[required] ?? 0)
}

// B2B 최종 권고(action) 표시 스타일 — 시장분석/가격분석/미래예측/AI전략리포트 4개 페이지가
// 전부 이 값(ai-report의 report.action)을 그대로 가져다 써서 페이지마다 결론이 어긋나지 않게 한다.
export const ACTION_CONFIG = {
  '매입 확대': { color: '#10b981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)', icon: '↑' },
  '매입 유지': { color: '#6366f1', bg: 'rgba(99,102,241,0.06)', border: 'rgba(99,102,241,0.2)', icon: '→' },
  '재고 축소': { color: '#f59e0b', bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.2)',  icon: '↓' },
  '관망':      { color: '#8b5cf6', bg: 'rgba(139,92,246,0.06)',  border: 'rgba(139,92,246,0.2)',  icon: '◎' },
}
