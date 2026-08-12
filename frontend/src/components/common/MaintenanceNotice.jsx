import styles from '../../styles/MaintenanceNotice.module.css'
import { DEFAULT_MAINTENANCE_MESSAGE } from '../../utils/naverMaintenance'

export default function MaintenanceNotice({ message }) {
  return (
    <div className={styles.wrap}>
      <span className={styles.icon}>🛠️</span>
      <p className={styles.title}>일시 점검중입니다</p>
      <p className={styles.desc}>{message || DEFAULT_MAINTENANCE_MESSAGE}</p>
    </div>
  )
}
