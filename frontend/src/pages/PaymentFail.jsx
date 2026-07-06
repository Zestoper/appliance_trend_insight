import { useNavigate, useSearchParams } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import s from '../styles/PaymentResult.module.css'

export default function PaymentFail() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const message = params.get('message') || '결제가 취소되었거나 실패했습니다'

  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.box}>
        <div className={s.iconFail}>✕</div>
        <p className={s.title}>결제에 실패했습니다</p>
        <p className={s.sub}>{message}</p>
        <button className={s.btn} onClick={() => navigate('/b2b/pricing')}>요금제로 돌아가기</button>
      </div>
    </div>
  )
}
