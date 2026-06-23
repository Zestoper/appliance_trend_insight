import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import s from '../../styles/B2BPrintModal.module.css';

export const PAGE_SECTIONS = {
  dashboard: [
    { num: '01', title: '시장 현황 · 관심도 추이' },
    { num: '02', title: '브랜드 점유율 · 핵심 소비층' },
    { num: '03', title: '트렌드 분석 · 관심 키워드' },
    { num: '04', title: '트렌드 분석 · 소비자 불만 요인' },
    { num: '05', title: '시장 구조 · 설치 환경 · 구매 목적' },
    { num: '06', title: 'AI 종합 분석' },
  ],
  price: [
    { num: '01', title: '핵심 가격 지표' },
    { num: '02', title: '브랜드별 가격 경쟁력 분석' },
    { num: '03', title: '가격 수준별 브랜드 비중' },
    { num: '04', title: '가격 이력 · 추이 분석' },
    { num: '05', title: 'AI 가격 인사이트' },
  ],
  report: [
    { num: '01', title: 'AI 최종 권고 및 판단 근거' },
    { num: '02', title: '소비자 니즈 및 상품 기획 제안' },
    { num: '03', title: '시장 경쟁 현황' },
    { num: '04', title: '매입 · 가격 전략' },
    { num: '05', title: '기회 · 위험 요인 분석' },
    { num: '06', title: 'AI 종합 판단' },
    { num: '07', title: '실행 전략' },
    { num: '08', title: '예상 효과' },
  ],
  forecast: [
    { num: '01', title: '관심도 추세 · 예측 차트' },
    { num: '02', title: '핵심 예측 지표' },
    { num: '03', title: '월별 수요 영향도 · 계절 분석' },
    { num: '04', title: '3개월 전망 시나리오 · 기회 및 전략' },
  ],
};

const PAGES = [
  {
    id: 'dashboard', label: '시장 분석',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    id: 'price', label: '가격 분석',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    id: 'report', label: 'AI 전략 리포트',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
  {
    id: 'forecast', label: '미래 예측',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="3 17 7 11 11 14 15 8 21 14" />
        <polyline points="17 8 21 8 21 12" />
      </svg>
    ),
  },
];

function initSections() {
  const out = {};
  PAGES.forEach(p => { out[p.id] = PAGE_SECTIONS[p.id].map(s => s.num); });
  return out;
}

export default function B2BPrintModal({ open, onClose, category, period }) {
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState('dashboard');
  const [selected, setSelected] = useState(initSections);

  if (!open) return null;

  const secs       = PAGE_SECTIONS[activePage] ?? [];
  const activeSels = selected[activePage] ?? [];
  const allChecked = activeSels.length === secs.length;

  const toggleSection = (pageId, num) =>
    setSelected(prev => {
      const cur = prev[pageId] ?? [];
      return { ...prev, [pageId]: cur.includes(num) ? cur.filter(n => n !== num) : [...cur, num] };
    });

  const toggleAllSections = () =>
    setSelected(prev => ({
      ...prev,
      [activePage]: allChecked ? [] : secs.map(s => s.num),
    }));

  const totalSecs = PAGES.reduce((acc, p) => acc + (selected[p.id]?.length ?? 0), 0);

  const handlePrint = () => {
    if (totalSecs === 0) return;
    const parts = PAGES
      .filter(p => (selected[p.id]?.length ?? 0) > 0)
      .map(p => `${p.id}:${selected[p.id].join(',')}`);
    const params = new URLSearchParams({
      sections: parts.join('|'),
      category: category ?? '에어컨',
      period:   period   ?? '3m',
    });
    navigate(`/b2b/print?${params}`);
    onClose();
  };

  return (
    <div className={s.backdrop} onClick={onClose}>
      <div className={s.modal} onClick={e => e.stopPropagation()}>

        {/* ── 헤더 ── */}
        <div className={s.header}>
          <div className={s.headerLeft}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 6 2 18 2 18 9" />
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="8" />
            </svg>
            <h3 className={s.title}>출력 섹션 선택</h3>
            <span className={s.catBadge}>{category ?? '에어컨'}</span>
          </div>
          <button className={s.close} onClick={onClose}>✕</button>
        </div>

        {/* ── 2패널 바디 ── */}
        <div className={s.body}>

          {/* 왼쪽 — 페이지 목록 */}
          <div className={s.pageList}>
            <p className={s.panelLabel}>페이지</p>
            {PAGES.map(p => {
              const cnt   = selected[p.id]?.length ?? 0;
              const total = PAGE_SECTIONS[p.id].length;
              const isActive = activePage === p.id;
              return (
                <button
                  key={p.id}
                  className={`${s.pageItem} ${isActive ? s.pageItemActive : ''} ${cnt === 0 ? s.pageItemEmpty : ''}`}
                  onClick={() => setActivePage(p.id)}
                >
                  <span className={s.pageItemIcon}>{p.icon}</span>
                  <span className={s.pageItemLabel}>{p.label}</span>
                  <span className={`${s.pageItemBadge} ${cnt === 0 ? s.pageItemBadgeOff : ''}`}>
                    {cnt}/{total}
                  </span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={s.chevron}>
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              );
            })}
          </div>

          {/* 오른쪽 — 섹션 목록 */}
          <div className={s.sectionPanel}>
            <div className={s.sectionPanelHead}>
              <p className={s.panelLabel}>
                {PAGES.find(p => p.id === activePage)?.label} 섹션
              </p>
              <button className={s.toggleAllBtn} onClick={toggleAllSections}>
                {allChecked ? '전체 해제' : '전체 선택'}
              </button>
            </div>
            <div className={s.sectionList}>
              {secs.map(sec => {
                const checked = activeSels.includes(sec.num);
                return (
                  <label key={sec.num} className={`${s.secRow} ${checked ? s.secRowOn : ''}`}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleSection(activePage, sec.num)}
                      className={s.hiddenCheck}
                    />
                    <div className={`${s.secCheck} ${checked ? s.secCheckOn : ''}`}>
                      {checked && (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </div>
                    <span className={s.secNum}>{sec.num}</span>
                    <span className={s.secTitle}>{sec.title}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── 푸터 ── */}
        <div className={s.footer}>
          <button className={s.cancelBtn} onClick={onClose}>취소</button>
          <button
            className={s.printBtn}
            onClick={handlePrint}
            disabled={totalSecs === 0}
          >
            {totalSecs > 0 ? `${totalSecs}개 섹션 출력` : '섹션을 선택하세요'}
          </button>
        </div>
      </div>
    </div>
  );
}
