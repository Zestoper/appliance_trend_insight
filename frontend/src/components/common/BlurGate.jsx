import { useNavigate } from 'react-router-dom'
import { hasTier, TIER_LABEL } from '../../config'
import s from '../../styles/BlurGate.module.css'

export default function BlurGate({ tier, required, label, children }) {
  const navigate = useNavigate()
  if (hasTier(tier, required)) return children

  return (
    <div className={s.wrap}>
      <div className={s.blurred} aria-hidden="true">{children}</div>
      <div className={`${s.overlay} no-print`}>
        <div className={s.lockIcon}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <p className={s.overlayTitle}>{label || `${TIER_LABEL[required]} 등급부터 열람 가능`}</p>
        <button className={s.overlayBtn} onClick={() => navigate('/b2b/pricing')}>
          {TIER_LABEL[required]} 구독하기
        </button>
      </div>
    </div>
  )
}
