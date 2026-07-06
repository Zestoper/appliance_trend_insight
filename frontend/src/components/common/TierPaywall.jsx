import { useNavigate } from 'react-router-dom'
import Navbar from './Navbar'
import { TIER_LABEL, TIER_PRICES } from '../../config'
import s from '../../styles/TierPaywall.module.css'

export default function TierPaywall({ required, title, desc }) {
  const navigate = useNavigate()
  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.box}>
        <div className={s.icon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <p className={s.badge}>{TIER_LABEL[required]} 등급 전용</p>
        <h1 className={s.title}>{title || `${TIER_LABEL[required]} 등급부터 열람 가능합니다`}</h1>
        <p className={s.desc}>{desc || '이 기능은 구독 등급을 업그레이드하면 바로 이용할 수 있어요.'}</p>
        <button className={s.btn} onClick={() => navigate('/b2b/pricing')}>
          {TIER_LABEL[required]} 구독하기 · 월 {TIER_PRICES[required]?.toLocaleString()}원
        </button>
      </div>
    </div>
  )
}
