import { useLocation, useNavigate } from 'react-router-dom'
import styles from '../styles/Login.module.css'
import s from '../styles/Signup.module.css'

export default function SignupPending() {
  const { state } = useLocation()
  const navigate  = useNavigate()

  return (
    <div className={styles.page}>
      <div className={styles.blobWrap}>
        <div className={`${styles.blob} ${styles.blobIndigo}`} />
        <div className={`${styles.blob} ${styles.blobPurple}`} />
      </div>

      <div className={`${styles.card} ${s.pendingCard}`}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>A</div>
          <span className={styles.logoText}>가전무쌍</span>
        </div>

        <div className={s.pendingIcon}>⏳</div>
        <h1 className={s.pendingTitle}>가입 신청 완료</h1>
        <p className={s.pendingDesc}>
          <strong style={{ color: 'var(--text)' }}>{state?.company_name || '사업자'}</strong> 계정 신청이 접수됐어요.<br />
          관리자 검토 후 <strong style={{ color: '#818cf8' }}>{state?.email}</strong>으로<br />
          1~2일 내 결과를 안내해드릴게요.
        </p>

        <div className={s.pendingSteps}>
          {[
            { icon: '✅', text: '가입 신청 완료' },
            { icon: '🔍', text: '관리자 검토 중' },
            { icon: '📧', text: '이메일로 결과 안내' },
          ].map((item, i) => (
            <div key={i} className={s.pendingStep}>
              <span className={s.pendingStepIcon}>{item.icon}</span>
              <span className={s.pendingStepText}
                style={{ color: i === 0 ? 'var(--text)' : 'var(--text-muted)', fontWeight: i === 0 ? 600 : 400 }}>
                {item.text}
              </span>
            </div>
          ))}
        </div>

        <button className={styles.ctaBtn} style={{ width: '100%', marginTop: 24 }}
          onClick={() => navigate('/')}>
          홈으로 돌아가기 →
        </button>
      </div>
    </div>
  )
}
