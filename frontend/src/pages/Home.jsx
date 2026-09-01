import Navbar from '../components/common/Navbar'
import Hero from '../components/sections/Hero'
import DataSources from '../components/sections/DataSources'
import ReportPreview from '../components/sections/ReportPreview'
import styles from '../styles/Home.module.css'

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
    </>
  )
}
