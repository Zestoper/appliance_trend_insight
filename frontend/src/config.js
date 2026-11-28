import { Eye, MoveRight, TrendingDown, TrendingUp } from 'lucide-react'
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

// B2B 최종 권고(action) 표시 스타일 — 시장분석/가격분석/미래예측/AI전략리포트 4개 페이지가
// 전부 이 값(ai-report의 report.action)을 그대로 가져다 써서 페이지마다 결론이 어긋나지 않게 한다.
export const ACTION_CONFIG = {
  '매입 확대': { color: 'var(--verdict-best)', bg: 'color-mix(in srgb, var(--verdict-best) 6%, transparent)', border: 'color-mix(in srgb, var(--verdict-best) 20%, transparent)', icon: TrendingUp },
  '매입 유지': { color: 'var(--brand)', bg: 'color-mix(in srgb, var(--brand) 6%, transparent)', border: 'color-mix(in srgb, var(--brand) 20%, transparent)', icon: MoveRight },
  '재고 축소': { color: 'var(--warn)', bg: 'color-mix(in srgb, var(--warn) 6%, transparent)',  border: 'color-mix(in srgb, var(--warn) 20%, transparent)',  icon: TrendingDown },
  '관망':      { color: 'var(--brand)', bg: 'color-mix(in srgb, var(--brand) 6%, transparent)',  border: 'color-mix(in srgb, var(--brand) 20%, transparent)',  icon: Eye },
}
