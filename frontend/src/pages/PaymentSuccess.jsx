import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import { useAuth } from '../context/AuthContext'
import { API_BASE, TIER_LABEL } from '../config'
import s from '../styles/PaymentResult.module.css'

export default function PaymentSuccess() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { token, updateUser } = useAuth()
  const [status, setStatus] = useState('confirming')
  const [error, setError] = useState(null)
  const [tier, setTier] = useState(null)

  useEffect(() => {
    const paymentKey = params.get('paymentKey')
    const orderId = params.get('orderId')
    const amount = Number(params.get('amount'))

    if (!paymentKey || !orderId || !amount) {
      setStatus('error')
      setError('결제 정보를 확인할 수 없습니다')
      return
    }

    fetch(`${API_BASE}/api/payments/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ paymentKey, orderId, amount }),
    })
      .then(async r => {
        const data = await r.json()
        if (!r.ok) throw new Error(data.detail || '결제 승인에 실패했습니다')
        return data
      })
      .then(data => {
        updateUser({ tier: data.tier, tier_expires_at: data.tier_expires_at })
        setTier(data.tier)
        setStatus('done')
      })
      .catch(e => {
        setStatus('error')
        setError(e.message)
      })
  }, [params, token, updateUser])

  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.box}>
        {status === 'confirming' && (
          <>
            <div className={s.spinner} />
            <p className={s.title}>결제를 확인하고 있습니다...</p>
          </>
        )}
        {status === 'done' && (
          <>
            <div className={s.iconOk}>✓</div>
            <p className={s.title}>{TIER_LABEL[tier]} 등급 구독이 완료됐습니다</p>
            <p className={s.sub}>이제 해당 등급의 모든 기능을 이용할 수 있어요</p>
            <button className={s.btn} onClick={() => navigate('/b2b')}>B2B 홈으로 이동</button>
          </>
        )}
        {status === 'error' && (
          <>
            <div className={s.iconFail}>✕</div>
            <p className={s.title}>결제 승인에 실패했습니다</p>
            <p className={s.sub}>{error}</p>
            <button className={s.btn} onClick={() => navigate('/b2b/pricing')}>요금제로 돌아가기</button>
          </>
        )}
      </div>
    </div>
  )
}
