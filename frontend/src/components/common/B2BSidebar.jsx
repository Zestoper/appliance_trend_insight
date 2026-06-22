import s from '../../styles/B2BSidebar.module.css'

const CATEGORIES = ['에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기', 'TV']

export default function B2BSidebar({
  category, setCategory,
  periods, period, setPeriod,
  dataSources,
  onRefresh, loading, fetchedAt,
  onDownload,
}) {
  return (
    <aside className={s.sidebar}>

      {/* ── 액션 버튼 ── */}
      {(onRefresh || onDownload) && (
        <div className={s.actions}>
          {fetchedAt && (
            <span className={s.updateTime}>
              {fetchedAt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })} 업데이트
            </span>
          )}
          <div className={s.actionBtns}>
            {onRefresh && (
              <button className={s.actionBtn} title="새로고침" onClick={onRefresh}
                disabled={loading} style={{ opacity: loading ? 0.4 : 1 }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/>
                  <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                </svg>
              </button>
            )}
            {onDownload && (
              <button className={`${s.actionBtn} no-print`} title="PDF 저장" onClick={onDownload}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 16V4M12 16l-4-4M12 16l4-4"/><path d="M4 20h16"/>
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      <div className={s.group}>
        <p className={s.groupLabel}>카테고리</p>
        {CATEGORIES.map(c => (
          <button
            key={c}
            className={`${s.item} ${c === category ? s.itemActive : ''}`}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {periods && setPeriod && (
        <div className={s.group}>
          <p className={s.groupLabel}>기간</p>
          {periods.map(p => (
            <button
              key={p.value}
              className={`${s.item} ${p.value === period ? s.itemActive : ''}`}
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}

      {dataSources && dataSources.length > 0 && (
        <div className={s.group}>
          <p className={s.groupLabel}>데이터 소스</p>
          <ul className={s.sourceList}>
            {dataSources.map(src => (
              <li key={src} className={s.sourceItem}>
                <span className={s.sourceDot} />
                {src}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  )
}
