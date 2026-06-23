import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import B2BSidebar from '../components/common/B2BSidebar';
import { useAuth } from '../context/AuthContext';
import s from '../styles/B2BReport.module.css';
import { API_BASE } from '../config';

const PERIODS = [
  { label: '1개월', value: '1m' },
  { label: '3개월', value: '3m' },
  { label: '6개월', value: '6m' },
  { label: '1년',   value: '1y' },
];
const PERIOD_LABEL = { '1m': '최근 1개월', '3m': '최근 3개월', '6m': '최근 6개월', '1y': '최근 1년' };

const ACTION_CONFIG = {
  '매입 확대': { color: '#10b981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)', icon: '↑' },
  '매입 유지': { color: '#6366f1', bg: 'rgba(99,102,241,0.06)', border: 'rgba(99,102,241,0.2)', icon: '→' },
  '재고 축소': { color: '#f59e0b', bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.2)',  icon: '↓' },
  '관망':      { color: '#8b5cf6', bg: 'rgba(139,92,246,0.06)',  border: 'rgba(139,92,246,0.2)',  icon: '◎' },
};
const RISK_COLOR  = { 낮음: '#10b981', 중간: '#f59e0b', 높음: '#ef4444' };
const BRAND_COLORS = ['#6366f1','#a855f7','#3b82f6','#06b6d4','#10b981','#f59e0b'];
const SIGNAL_CFG  = {
  '매입 적기': { color: '#10b981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.2)' },
  '관망 권장': { color: '#8b5cf6', bg: 'rgba(139,92,246,0.08)', border: 'rgba(139,92,246,0.2)' },
  '적정가':    { color: '#6366f1', bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.2)' },
};

function fmt만(won) { return won ? `${Math.round(won / 10000).toLocaleString()}만원` : '-'; }

/* ── 섹션 헤더 (번호 + 제목) ── */
function SectionHead({ num, title }) {
  return (
    <div className={s.sectionHead}>
      <span className={s.sectionNum}>{num}</span>
      <span className={s.sectionTitle}>{title}</span>
      <span className={s.sectionLine} />
    </div>
  );
}

/* ── 브랜드 점유율 테이블 ── */
function BrandTable({ brands }) {
  if (!brands?.length) return null;
  const maxPct = Math.max(...brands.map(b => b.pct));
  return (
    <table className={s.dataTable}>
      <thead>
        <tr>
          <th>브랜드</th>
          <th>점유율</th>
          <th className={s.barCol}>비중</th>
        </tr>
      </thead>
      <tbody>
        {brands.slice(0, 6).map((b, i) => (
          <tr key={i}>
            <td>
              <span className={s.brandDot2} style={{ background: BRAND_COLORS[i % BRAND_COLORS.length] }} />
              {b.brand}
            </td>
            <td className={s.numCell}><strong>{b.pct}%</strong></td>
            <td className={s.barCell}>
              <div className={s.barTrack}>
                <div className={s.barFill}
                  style={{ width: `${(b.pct / maxPct) * 100}%`, background: BRAND_COLORS[i % BRAND_COLORS.length] }} />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* ── 가격 인텔리전스 테이블 ── */
function PriceTable({ priceData, category }) {
  const ins    = priceData?.price_insight;
  const sum    = priceData?.summary;
  const brands = priceData?.by_brand ?? [];
  if (!ins) return null;

  const signal = ins.signal ?? '적정가';
  const cfg    = SIGNAL_CFG[signal] ?? SIGNAL_CFG['적정가'];

  const changePct = sum?.price_change_pct;
  const changeStr = changePct != null ? `${changePct >= 0 ? '+' : ''}${changePct}%` : '-';

  return (
    <>
      {/* 시그널 헤더 */}
      <div className={s.priceSignalRow} style={{ borderColor: cfg.border, background: cfg.bg }}>
        <span className={s.priceSignalBadge} style={{ color: cfg.color, borderColor: cfg.border }}>
          {signal}
        </span>
        <span className={s.priceSignalReason}>{ins.reason}</span>
        {ins.brand_pick && ins.brand_pick !== '-' && (
          <span className={s.priceBrandPick} style={{ color: cfg.color }}>
            추천 브랜드: <strong>{ins.brand_pick}</strong>
          </span>
        )}
      </div>

      {/* 시장 가격 현황 테이블 */}
      <table className={s.dataTable} style={{ marginTop: 14 }}>
        <thead>
          <tr>
            <th>구분</th>
            <th>평균가</th>
            <th>최저가</th>
            <th>최고가</th>
            <th>전일 대비</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>시장 전체</td>
            <td className={s.numCell}><strong>{fmt만(sum?.avg_price)}</strong></td>
            <td className={s.numCell}>{fmt만(sum?.min_price)}</td>
            <td className={s.numCell}>{fmt만(sum?.max_price)}</td>
            <td className={s.numCell} style={{ color: (changePct ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
              {changeStr}
            </td>
          </tr>
          {brands.slice(0, 4).map((b, i) => (
            <tr key={i}>
              <td>
                <span className={s.brandDot2} style={{ background: BRAND_COLORS[i % BRAND_COLORS.length] }} />
                {b.brand}
              </td>
              <td className={s.numCell}><strong>{fmt만(b.avg_price)}</strong></td>
              <td className={s.numCell}>{fmt만(b.min_price)}</td>
              <td className={s.numCell}>{fmt만(b.max_price)}</td>
              <td className={s.numCell}>—</td>
            </tr>
          ))}
        </tbody>
      </table>

      {ins.strategy && ins.strategy !== '-' && (
        <div className={s.strategyNote}>
          <span className={s.strategyNoteIcon} style={{ color: cfg.color }}>→</span>
          {ins.strategy}
        </div>
      )}
    </>
  );
}

function AccessDenied({ user, navigate }) {
  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.denied}>
        <p className={s.deniedTitle}>
          {!user ? '로그인이 필요합니다' : user.user_type !== 'b2b' ? 'B2B 계정 전용입니다' : '승인 대기 중입니다'}
        </p>
        <p className={s.deniedDesc}>
          {!user ? 'B2B 계정으로 로그인해주세요' : user.user_type !== 'b2b' ? 'B2B 가입 후 이용할 수 있어요' : '관리자 승인 후 사용 가능합니다'}
        </p>
        <button className={s.deniedBtn} onClick={() => navigate(!user ? '/login' : '/b2b')}>
          {!user ? '로그인' : 'B2B 홈으로'}
        </button>
      </div>
    </div>
  );
}

export default function B2BReport() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [category, setCategory] = useState('에어컨');
  const [period, setPeriod]     = useState('3m');
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [fetchedAt, setFetchedAt]     = useState(null);
  const [priceData, setPriceData]     = useState(null);

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin';
  const loadData = () => setRefreshTick(t => t + 1);

  const downloadExcel = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/b2b/export-report?category=${encodeURIComponent(category)}&period=${period}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(err.detail || '엑셀 다운로드에 실패했습니다. 먼저 AI 리포트를 생성해주세요.')
        return
      }
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `가전무쌍_B2B리포트_${category}_${new Date().toISOString().slice(0,10)}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('엑셀 다운로드 중 오류가 발생했습니다.')
    }
  }

  useEffect(() => {
    if (!isB2BActive) return;
    setLoading(true); setError(null); setData(null); setPriceData(null);
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API_BASE}/api/b2b/ai-report?category=${encodeURIComponent(category)}&period=${period}`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/b2b/price?category=${encodeURIComponent(category)}`, { headers }).then(r => r.json()),
    ])
      .then(([d, pd]) => { setData(d); setPriceData(pd); setFetchedAt(new Date()); setLoading(false); })
      .catch(() => { setError('서버에 연결할 수 없습니다'); setLoading(false); });
  }, [category, period, isB2BActive, refreshTick]);

  if (!isB2BActive) return <AccessDenied user={user} navigate={navigate} />;

  const report  = data?.report;
  const metrics = data?.metrics;
  const brands  = data?.brands ?? [];
  const action  = report?.action ?? '관망';
  const acfg    = ACTION_CONFIG[action] ?? ACTION_CONFIG['관망'];

  const growth    = metrics?.growth_rate;
  const growthStr = growth != null ? `${growth >= 0 ? '+' : ''}${growth}%` : '-';
  const riskColor = RISK_COLOR[metrics?.risk] ?? '#8e8e93';
  const today     = fetchedAt
    ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });

  const oppList   = Array.isArray(report?.opportunity)  ? report.opportunity  : (report?.opportunity  ? [report.opportunity]  : []);
  const riskList  = Array.isArray(report?.risk_summary) ? report.risk_summary : (report?.risk_summary ? [report.risk_summary] : []);
  const basisList = report?.action_basis ?? [];
  const kwList    = report?.key_keywords ?? [];

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>
        <div className={s.layout}>
          <div className={s.main}>

            {loading && (
              <div className={s.loadingWrap}>
                <div className={s.spinner} />
                <p>"{category}" 시장 AI 분석 중...</p>
              </div>
            )}
            {error && <div className={s.error}>{error}</div>}
            {!loading && data?.error && <div className={s.error}>{data.error}</div>}

            {!loading && data && report && (
              <>
                {/* ── 리포트 헤더 ── */}
                <div className={s.reportHeader}>
                  <div className={s.reportHeaderTop}>
                    <div>
                      <p className={s.reportLabel}>B2B 시장 전략 리포트</p>
                      <h1 className={s.reportTitle}>{category} 시장 분석</h1>
                      <p className={s.reportMeta}>{today} 기준 &nbsp;·&nbsp; {PERIOD_LABEL[period]} &nbsp;·&nbsp; 데이터 출처: 네이버 DataLab · Groq LLM</p>
                    </div>
                    <div className={s.reportActionBadge} style={{ background: acfg.bg, borderColor: acfg.border }}>
                      <span className={s.reportActionIcon} style={{ color: acfg.color }}>{acfg.icon}</span>
                      <span className={s.reportActionText} style={{ color: acfg.color }}>{action}</span>
                    </div>
                  </div>
                  <div className={s.reportKpiRow}>
                    {[
                      { label: '검색 관심도', val: metrics?.trend_score != null ? metrics.trend_score : '-', sub: '현재 지수' },
                      { label: '시장 성장률', val: growthStr, sub: '전기 대비', color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' },
                      { label: '시장 위험도', val: metrics?.risk ?? '-', sub: '종합 평가', color: riskColor },
                      { label: '추천 시기',   val: report.timing !== '-' ? report.timing : '-', sub: '매입 타이밍' },
                      { label: '재고 조정',   val: report.inventory_advice !== '-' ? report.inventory_advice : '-', sub: '권장 수준' },
                    ].map(({ label, val, sub, color }) => (
                      <div key={label} className={s.reportKpi}>
                        <p className={s.reportKpiLabel}>{label}</p>
                        <p className={s.reportKpiVal} style={color ? { color } : {}}>{val}</p>
                        <p className={s.reportKpiSub}>{sub}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── 01 AI 최종 권고 ── */}
                <div className={s.section}>
                  <SectionHead num="01" title="AI 최종 권고 및 판단 근거" />

                  <div className={s.heroBanner} style={{ background: acfg.bg, borderColor: acfg.border }}>
                    <div className={s.heroLeft}>
                      <p className={s.heroAction} style={{ color: acfg.color }}>
                        {acfg.icon} {action}
                      </p>
                      <p className={s.heroReason}>{report.action_reason}</p>
                      {report.recommended_products !== '-' && (
                        <div className={s.heroRecoRow}>
                          <span className={s.heroRecoLabel}>추천 제품군</span>
                          <span className={s.heroRecoVal} style={{ color: acfg.color }}>
                            {report.recommended_products}
                          </span>
                        </div>
                      )}
                      {kwList.length > 0 && (
                        <div className={s.heroKwRow}>
                          {kwList.map((kw, i) => (
                            <span key={i} className={s.heroKwChip} style={{ borderColor: acfg.border, color: acfg.color }}>
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className={s.heroRight}>
                      <div className={s.heroMetricGrid}>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>예상 성장률</span>
                          <span className={s.heroMetricVal}
                            style={{ color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
                            {growthStr}
                          </span>
                        </div>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>추천 시기</span>
                          <span className={s.heroMetricVal} style={{ color: acfg.color, fontSize: '14px' }}>
                            {report.timing !== '-' ? report.timing : '-'}
                          </span>
                        </div>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>권장 재고</span>
                          <span className={s.heroMetricVal} style={{ color: acfg.color, fontSize: '14px' }}>
                            {report.inventory_advice !== '-' ? report.inventory_advice : '-'}
                          </span>
                        </div>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>위험도</span>
                          <span className={s.heroMetricVal} style={{ color: riskColor }}>
                            {metrics?.risk ?? '-'}
                          </span>
                        </div>
                        {report.target_segment !== '-' && (
                          <div className={s.heroMetric}>
                            <span className={s.heroMetricLabel}>추천 타깃</span>
                            <span className={s.heroMetricVal} style={{ color: acfg.color, fontSize: '13px' }}>
                              {report.target_segment}
                            </span>
                          </div>
                        )}
                        {report.price_range !== '-' && (
                          <div className={s.heroMetric}>
                            <span className={s.heroMetricLabel}>추천 가격대</span>
                            <span className={s.heroMetricVal} style={{ color: acfg.color, fontSize: '13px' }}>
                              {report.price_range}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {basisList.length > 0 && (
                    <div className={s.basisCard}>
                      <p className={s.basisTitle}>AI 판단 근거</p>
                      <div className={s.basisList}>
                        {basisList.map((item, i) => (
                          <div key={i} className={s.basisItem}>
                            <span className={s.basisNum} style={{ color: acfg.color }}>
                              {['①','②','③','④','⑤'][i]}
                            </span>
                            <span className={s.basisText}>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* ── 02 소비자 니즈 및 상품 기획 ── */}
                {(report.consumer_needs?.length > 0 || report.consumer_complaints?.length > 0) && (
                  <div className={s.section}>
                    <SectionHead num="02" title="소비자 니즈 및 상품 기획 제안" />

                    {/* 제품 기획 브리프 — 핵심 한 줄 결론 */}
                    {report.product_brief && report.product_brief !== '-' && (
                      <div className={s.productBriefBanner}>
                        <span className={s.productBriefIcon} style={{ color: acfg.color }}>◎</span>
                        <p className={s.productBriefText}>{report.product_brief}</p>
                      </div>
                    )}

                    <div className={s.planningGrid}>
                      {/* 소비자가 원하는 것 — 키워드 기반 */}
                      <div className={s.planningCard}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: '#10b981' }}>
                          <span className={s.planningCardTag} style={{ background: '#10b98118', color: '#10b981' }}>소비자 니즈</span>
                          <p className={s.planningCardSub}>쇼핑 키워드에서 도출</p>
                        </div>
                        <ul className={s.planningList}>
                          {(report.consumer_needs ?? []).filter(item => item && item !== '없음' && item !== '-').map((item, i) => (
                            <li key={i} className={s.planningItem}>
                              <span className={s.planningBullet} style={{ color: '#10b981' }}>→</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* 현재 시장 공백 — 불만 키워드 기반 */}
                      <div className={s.planningCard}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: '#f59e0b' }}>
                          <span className={s.planningCardTag} style={{ background: '#f59e0b18', color: '#f59e0b' }}>시장 공백</span>
                          <p className={s.planningCardSub}>불만 키워드에서 도출</p>
                        </div>
                        <ul className={s.planningList}>
                          {(report.consumer_complaints ?? []).filter(item => item && item !== '없음' && item !== '-').map((item, i) => (
                            <li key={i} className={s.planningItem}>
                              <span className={s.planningBullet} style={{ color: '#f59e0b' }}>!</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* 탑재해야 할 기능 — 핵심 */}
                      <div className={s.planningCard} style={{ gridColumn: '1 / -1' }}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: acfg.color }}>
                          <span className={s.planningCardTag} style={{ background: `${acfg.color}18`, color: acfg.color }}>탑재 기능 제안</span>
                          <p className={s.planningCardSub}>니즈 충족 + 불만 해소 기능</p>
                        </div>
                        <div className={s.featureGrid}>
                          {(report.recommended_features ?? []).filter(item => item && item !== '없음' && item !== '-').map((item, i) => (
                            <div key={i} className={s.featureChip}>
                              <span className={s.featureNum} style={{ background: `${acfg.color}18`, color: acfg.color }}>
                                {['①','②','③','④','⑤'][i]}
                              </span>
                              <span className={s.featureText}>{item}</span>
                            </div>
                          ))}
                        </div>
                        {report.needs_basis && report.needs_basis !== '-' && (
                          <p className={s.planningBasis}>{report.needs_basis}</p>
                        )}
                        <div className={s.planningFooter}>
                          {report.price_range !== '-' && (
                            <span className={s.planningPriceTag}>
                              권장 가격대 <strong>{report.price_range}</strong>
                            </span>
                          )}
                          <p className={s.needsQuestion}>"무엇을 팔 것인가?"</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── 03 시장 경쟁 현황 ── */}
                <div className={s.section}>
                  <SectionHead num="03" title="시장 경쟁 현황" />
                  <div className={s.twoColTable}>
                    {/* 브랜드 점유율 */}
                    <div className={s.tableBlock}>
                      <p className={s.tableBlockTitle}>브랜드 검색 점유율</p>
                      <BrandTable brands={brands} />
                    </div>
                    {/* 핵심 지표 */}
                    <div className={s.tableBlock}>
                      <p className={s.tableBlockTitle}>핵심 시장 지표</p>
                      <table className={s.dataTable}>
                        <tbody>
                          {[
                            { label: '검색 관심도 (현재)', val: metrics?.trend_score ?? '-' },
                            { label: '검색 관심도 (평균)', val: metrics?.avg_score ?? '-' },
                            { label: '기간 성장률',         val: growthStr, color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' },
                            { label: '시장 위험도',         val: metrics?.risk ?? '-', color: riskColor },
                            { label: '추천 소비 타깃',      val: report.target_segment !== '-' ? report.target_segment : '-' },
                            { label: '위험 핵심 요소',      val: report.risk_factor !== '-' ? report.risk_factor : '-' },
                          ].map(({ label, val, color }) => (
                            <tr key={label}>
                              <td className={s.metaLabel}>{label}</td>
                              <td className={s.numCell} style={color ? { color, fontWeight: 700 } : { fontWeight: 600 }}>{val}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {kwList.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <p className={s.tableBlockTitle} style={{ marginBottom: 8 }}>주목 키워드</p>
                          <div className={s.kwChips}>
                            {kwList.map((kw, i) => (
                              <span key={i} className={s.kwChip}>{kw}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── 04 매입·가격 전략 ── */}
                {priceData && priceData.price_insight && (
                  <div className={s.section}>
                    <SectionHead num="04" title="매입·가격 전략" />
                    <PriceTable priceData={priceData} category={category} />
                    {(report.timing !== '-' || report.inventory_advice !== '-') && (
                      <div className={s.priceStrategyRow}>
                        {[
                          { label: '권장 판매가', val: report.price_range !== '-' ? report.price_range : priceData.summary?.avg_price ? `${Math.round(priceData.summary.avg_price / 10000)}만원 수준` : '-' },
                          { label: '권장 재고',   val: report.inventory_advice !== '-' ? report.inventory_advice : '-', color: acfg.color },
                          { label: '권장 매입 시기', val: report.timing !== '-' ? report.timing : '-', color: acfg.color },
                          { label: '위험 요소',   val: report.risk_factor !== '-' ? report.risk_factor : (metrics?.risk ?? '-'), color: riskColor },
                        ].map(({ label, val, color }) => (
                          <div key={label} className={s.priceStrategyItem}>
                            <p className={s.priceStrategyLabel}>{label}</p>
                            <p className={s.priceStrategyVal} style={color ? { color } : {}}>{val}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    <p className={s.sectionQuestion}>"얼마나 들여오고 얼마에 팔 것인가?"</p>
                  </div>
                )}

                {/* ── 05 기회 & 위험 요인 ── */}
                <div className={s.section}>
                  <SectionHead num="05" title="기회 · 위험 요인 분석" />
                  <div className={s.twoCol}>
                    <div className={s.opportunityCard}>
                      <p className={s.factorHeader}>
                        <span className={s.factorDot} style={{ background: '#10b981' }} />
                        기회 요인
                      </p>
                      <ul className={s.factorList}>
                        {oppList.length > 0
                          ? oppList.map((item, i) => (
                              <li key={i} className={s.factorItem}>
                                <span className={s.factorCheck}>✔</span>{item}
                              </li>
                            ))
                          : <li className={s.factorEmpty}>분석 중</li>
                        }
                      </ul>
                    </div>
                    <div className={s.riskCard}>
                      <p className={s.factorHeader}>
                        <span className={s.factorDot} style={{ background: '#f59e0b' }} />
                        위험 요인
                      </p>
                      <ul className={s.factorList}>
                        {riskList.length > 0
                          ? riskList.map((item, i) => (
                              <li key={i} className={`${s.factorItem} ${s.factorRisk}`}>
                                <span className={s.factorWarn}>⚠</span>{item}
                              </li>
                            ))
                          : <li className={s.factorEmpty}>분석 중</li>
                        }
                      </ul>
                    </div>
                  </div>
                </div>

                {/* ── 06 AI 종합 판단 ── */}
                <div className={s.section}>
                  <SectionHead num="06" title="AI 종합 판단" />
                  <div className={s.conclusionCard}>
                    <div className={s.conclusionHeader}>
                      <span className={s.ragBadge}>RAG 강화</span>
                      <p className={s.conclusionSub}>{category} · AI 생성 분석 · {PERIOD_LABEL[period]}</p>
                    </div>
                    {(report.summary_lines?.length > 0 || report.summary) && (
                      <div className={s.conclusionNote}>
                        <p className={s.conclusionJudgeLabel}>AI 종합 판단</p>
                        {(report.summary_lines?.length > 0
                          ? report.summary_lines
                          : [report.summary]
                        ).filter(Boolean).map((sentence, i) => (
                          <p key={i} style={{ marginTop: i > 0 ? 8 : 0 }}>{sentence}</p>
                        ))}
                      </div>
                    )}
                    <div className={s.conclusionTable}>
                      {[
                        { label: '시장 전망',    val: `${growth != null ? (growth >= 0 ? '긍정' : '부정') : '-'} (${growthStr})` },
                        { label: '추천 제품군', val: report.recommended_products !== '-' ? report.recommended_products : '-' },
                        { label: '추천 소비층', val: report.target_segment !== '-' ? report.target_segment : '-' },
                        { label: '권장 시기',   val: report.timing !== '-' ? report.timing : '-' },
                        { label: '위험 요소',   val: report.risk_factor !== '-' ? report.risk_factor : (metrics?.risk ?? '-') },
                      ].map(({ label, val }) => (
                        <div key={label} className={s.conclusionRow}>
                          <span className={s.conclusionLabel}>{label}</span>
                          <span className={s.conclusionVal}>{val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* ── 07 실행 전략 ── */}
                {(report.product_strategy?.length > 0 || report.sales_strategy?.length > 0 || report.service_strategy?.length > 0) && (
                  <div className={s.section}>
                    <SectionHead num="07" title="실행 전략" />
                    <div className={s.strategyGrid}>
                      {[
                        { num: '①', title: '제품 전략', items: report.product_strategy ?? [], color: '#6366f1' },
                        { num: '②', title: '판매 전략', items: report.sales_strategy   ?? [], color: '#10b981' },
                        { num: '③', title: '서비스 전략', items: report.service_strategy ?? [], color: '#f59e0b' },
                      ].map(({ num, title, items, color }) => (
                        <div key={title} className={s.strategyCard} style={{ borderTopColor: color }}>
                          <p className={s.strategyTitle}>
                            <span style={{ color }}>{num}</span> {title}
                          </p>
                          <ol className={s.strategyList}>
                            {items.map((item, i) => (
                              <li key={i} className={s.strategyItem}>
                                <span className={s.strategyNum} style={{ background: `${color}18`, color }}>
                                  {['①','②','③'][i] ?? i + 1}
                                </span>
                                {item}
                              </li>
                            ))}
                          </ol>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── 08 예상 효과 ── */}
                {(report.expected_effects?.length > 0 || report.expected_sales_growth !== '-') && (
                  <div className={s.section}>
                    <SectionHead num="08" title="예상 효과" />
                    <div className={s.effectGrid}>
                      {/* 수요 방향 + 예상 매출 */}
                      <div className={s.effectCard} style={{ borderTopColor: '#10b981' }}>
                        <p className={s.effectCardTitle}>
                          <span style={{ color: '#10b981' }}>↑</span> 예상 매출 증가
                        </p>
                        <p className={s.effectGrowthText}>{report.expected_sales_growth !== '-' ? report.expected_sales_growth : '-'}</p>
                      </div>
                      {/* 기대 효과 리스트 */}
                      <div className={s.effectCard} style={{ borderTopColor: '#6366f1' }}>
                        <p className={s.effectCardTitle}>
                          <span style={{ color: '#6366f1' }}>★</span> 기대 효과
                        </p>
                        <ul className={s.effectList}>
                          {(report.expected_effects ?? []).map((item, i) => (
                            <li key={i} className={s.effectItem}>
                              <span className={s.effectBullet} style={{ color: '#6366f1' }}>{['①','②','③'][i]}</span>
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                      {/* 위험도 + 종합 판단 */}
                      <div className={s.effectCard} style={{ borderTopColor: riskColor }}>
                        <p className={s.effectCardTitle}>
                          <span style={{ color: riskColor }}>⚠</span> 위험도 · 종합 판단
                        </p>
                        <div className={s.effectRiskRow}>
                          <span className={s.effectRiskBadge} style={{ background: `${riskColor}18`, color: riskColor }}>
                            위험도 {metrics?.risk ?? '-'}
                          </span>
                        </div>
                        <p className={s.effectProjection}>{report.projection_summary !== '-' ? report.projection_summary : '-'}</p>
                      </div>
                    </div>
                    <p className={s.sectionQuestion}>"그래서 기대되는 결과는 무엇인가?"</p>
                  </div>
                )}

                {/* ── 리포트 푸터 ── */}
                <div className={s.reportFooter}>
                  <span>본 리포트는 네이버 DataLab 검색 데이터 및 Groq LLM 기반 AI 분석으로 생성되었습니다.</span>
                  <span>{today} · {PERIOD_LABEL[period]} 분석</span>
                </div>
              </>
            )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            periods={PERIODS} period={period} setPeriod={setPeriod}
            dataSources={['네이버 DataLab', 'Groq LLM', 'RAG (구매 패턴)']}
            onRefresh={loadData} loading={loading} fetchedAt={fetchedAt}
            onDownload={downloadExcel}
          />
        </div>
      </div>
    </div>
  );
}
