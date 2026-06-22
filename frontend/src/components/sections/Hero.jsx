import { useState, useEffect } from 'react'
import styles from '../../styles/Hero.module.css'

// 타이핑 애니메이션에서 순환할 문장 목록
const TYPING_PHRASES = [
  '냉장고 시장 분석 중',
  '에어컨 트렌드 예측 중',
  '로봇청소기 리뷰 분석 중',
  '스타일러 소비자 반응 확인 중',
]

// 타이핑 → 지우기 → 다음 문장 반복하는 커스텀 훅
function useTypingEffect(phrases) {
  const [displayed, setDisplayed] = useState('')   // 화면에 표시되는 텍스트
  const [phraseIdx, setPhraseIdx] = useState(0)    // 현재 문장 인덱스
  const [charIdx, setCharIdx] = useState(0)        // 현재 글자 위치
  const [deleting, setDeleting] = useState(false)  // 지우는 중 여부

  useEffect(() => {
    const current = phrases[phraseIdx]
    const speed = deleting ? 40 : 80  // 지울 때는 더 빠르게

    const timeout = setTimeout(() => {
      // 타이핑 완료 → 잠시 대기 후 지우기 시작
      if (!deleting && charIdx === current.length) {
        setTimeout(() => setDeleting(true), 1800)
        return
      }
      // 다 지웠으면 → 다음 문장으로 전환
      if (deleting && charIdx === 0) {
        setDeleting(false)
        setPhraseIdx(i => (i + 1) % phrases.length)
        return
      }
      setDisplayed(current.slice(0, charIdx + (deleting ? -1 : 1)))
      setCharIdx(i => i + (deleting ? -1 : 1))
    }, speed)

    return () => clearTimeout(timeout)
  }, [charIdx, deleting, phraseIdx, phrases])

  return displayed
}

export default function Hero() {
  const typingText = useTypingEffect(TYPING_PHRASES)

  return (
    <section className={styles.hero}>

      {/* 배경 Blob: 애니메이션으로 둥둥 떠다니는 빛 덩어리 */}
      <div className={styles.blobWrap}>
        <div className={`${styles.blob} ${styles.blobIndigo}`} />
        <div className={`${styles.blob} ${styles.blobPurple}`} />
        <div className={`${styles.blob} ${styles.blobPink}`} />
      </div>

      <div className={styles.content}>

        {/* 상단 뱃지 */}
        <span className={styles.badge}>✦ 실시간 가전 트렌드 분석</span>

        {/* 메인 헤드라인 - 두 번째 줄에 그라디언트 텍스트 */}
        <h1 className={styles.headline}>
          국내 가전 트렌드를
          <span className={styles.gradientText}>한눈에 파악하세요</span>
        </h1>

        {/* 타이핑 효과 서브타이틀 */}
        <p className={styles.subtitle}>
          지금 이 순간,&nbsp;
          <span className={styles.typingText}>{typingText}</span>
        </p>

      </div>

      {/* 스크롤 유도 화살표 */}
      <div className={styles.scrollHint}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
        스크롤
      </div>

    </section>
  )
}
