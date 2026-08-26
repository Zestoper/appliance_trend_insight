import Navbar from '../components/common/Navbar'
import Hero from '../components/sections/Hero'
import DataSources from '../components/sections/DataSources'
import ReportPreview from '../components/sections/ReportPreview'
import styles from '../styles/Home.module.css'
import { COUPANG_PARTNER_LINK } from '../config'

export default function Home() {
  return (
    <>
      <Navbar />
      <main className={styles.snapContainer} data-scroll-container>
        <div className={styles.snapSection}>
          <Hero />
        </div>
        <div className={styles.snapSection}>
          <DataSources />
        </div>
        <div className={styles.snapSection}>
          <ReportPreview />
        </div>
      </main>
      <div className={styles.ptBar}>
        <a
          className={styles.ptBannerLink}
          href={COUPANG_PARTNER_LINK}
          target="_blank"
          rel="noopener noreferrer sponsored"
        >
          🎁 쿠팡 특가 상품 보러가기 →
        </a>
        <p className={styles.ptDisclosure}>이 사이트는 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
      </div>
    </>
  )
}
