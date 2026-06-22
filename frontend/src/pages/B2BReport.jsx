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

const ACTION_CONFIG = {
  '매입 확대': { color: '#10b981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)', icon: '↑' },
  '매입 유지': { color: '#6366f1', bg: 'rgba(99,102,241,0.06)', border: 'rgba(99,102,241,0.2)', icon: '→' },
  '재고 축소': { color: '#f59e0b', bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.2)',  icon: '↓' },
  '관망':      { color: '#8b5cf6', bg: 'rgba(139,92,246,0.06)',  border: 'rgba(139,92,246,0.2)',  icon: '◎' },
};
const RISK_COLOR = { 낮음: '#10b981', 중간: '#f59e0b', 높음: '#ef4444' };
const BRAND_COLORS = ['#6366f1', '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b'];

const SIGNAL_CFG = {
  '매입 적기':   { color: '#10b981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.2)'  },
  '관망 권장':   { color: '#8b5cf6', bg: 'rgba(139,92,246,0.08)', border: 'rgba(139,92,246,0.2)' },
  '적정가':      { color: '#6366f1', bg: 'rgba(99,102,241,0.08)',  border: 'rgba(99,102,241,0.2)'  },
};

function PriceInsightSection({ priceData, category }) {
  const ins     = priceData.price_insight;
  const summary = priceData.summary;
  const byBrand = priceData.by_brand ?? [];
  const history = priceData.price_history ?? [];

  const signal  = ins.signal ?? '적정가';
  const cfg     = SIGNAL_CFG[signal] ?? SIGNAL_CFG['적정가'];

  const changePct  = summary?.price_change_pct;
  const changeStr  = changePct != null
    ? `${changePct >= 0 ? '+' : ''}${changePct}%`
    : null;

  // 3개월 전 대비 가격 변화 (가격 히스토리 기반)
  let longChangeStr = null;
  if (history.length >= 2) {
    const oldest = history[0].avg_price;
    const latest = history[history.length - 1].avg_price;
    const pct    = Math.round((latest - oldest) / Math.max(oldest, 1) * 100);
    if (history.length >= 7) {
      longChangeStr = `${history.length}일 누적 ${pct >= 0 ? '+' : ''}${pct}%`
    }
  }

  // 브랜드 pick vs 시장 평균 비교
  const marketAvg   = summary?.avg_price;
  const brandPick   = ins.brand_pick;
  const brandInfo   = byBrand.find(b => b.brand === brandPick);
  const brandAvgStr = brandInfo
    ? `${brandPick} 평균가(${Math.round(brandInfo.avg_price / 10000)}만원)가 시장 평균(${Math.round(marketAvg / 10000)}만원) 수준`
    : null;

  // 근거 리스트 구성
  const basisItems = [
    changeStr     && `전일 대비 ${changeStr}`,
    longChangeStr && longChangeStr,
    ins.reason,
    brandAvgStr   && `${brandAvgStr}으로 안정적`,
  ].filter(Boolean);

  return (
    <div className={s.section}>
      <p className={s.sectionLabel}>AI 가격 인사이트</p>
      <div className={s.priceInsightCard} style={{ borderColor: cfg.border, background: cfg.bg }}>

        {/* 상단: 시그널 + 브랜드 픽 */}
        <div className={s.piHeader}>
          <span className={s.piSignal} style={{ color: cfg.color, borderColor: cfg.border }}>
            {signal}
          </span>
          {brandPick && brandPick !== '-' && (
            <span className={s.piBrandPick} style={{ color: cfg.color }}>
              {brandPick} 선매입 추천
            </span>
          )}
        </div>

        <div className={s.piBody}>
          {/* 근거 */}
          {basisItems.length > 0 && (
            <div className={s.piCol}>
              <p className={s.piColTitle}>근거</p>
              <ul className={s.piBasisList}>
                {basisItems.map((item, i) => (
                  <li key={i} className={s.piBasisItem}>
                    <span className={s.piCheck} style={{ color: cfg.color }}>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 추천 */}
          {(ins.strategy || ins.summary) && (
            <div className={s.piCol}>
              <p className={s.piColTitle}>추천</p>
              <ul className={s.piBasisList}>
                {ins.strategy && ins.strategy !== '-' && (
                  <li className={s.piBasisItem}>
                    <span className={s.piCheck} style={{ color: cfg.color }}>→</span>
                    {ins.strategy}
                  </li>
                )}
                {brandPick && brandPick !== '-' && ins.strategy && (
                  <li className={s.piBasisItem}>
                    <span className={s.piCheck} style={{ color: cfg.color }}>→</span>
                    {brandPick} 중심의 선매입 전략 추천
                  </li>
                )}
              </ul>
              {ins.summary && ins.summary !== '-' && (
                <p className={s.piSummary}>{ins.summary}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
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

  /* 기회/위험 요인 — 배열 또는 구 문자열 fallback */
  const oppList  = Array.isArray(report?.opportunity)  ? report.opportunity  : (report?.opportunity  ? [report.opportunity]  : []);
  const riskList = Array.isArray(report?.risk_summary) ? report.risk_summary : (report?.risk_summary ? [report.risk_summary] : []);
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
                {/* ── Section 1: AI 최종 권고 ── */}
                <div className={s.section}>
                  <p className={s.sectionLabel}>AI 최종 권고</p>

                  {/* 메인 배너 */}
                  <div className={s.heroBanner} style={{ background: acfg.bg, borderColor: acfg.border }}>
                    <div className={s.heroLeft}>
                      <p className={s.heroAction} style={{ color: acfg.color }}>
                        {acfg.icon} {action}
                      </p>
                      <p className={s.heroReason}>{report.action_reason}</p>
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
                          <span className={s.heroMetricVal} style={{ color: acfg.color }}>
                            {report.timing !== '-' ? report.timing : '-'}
                          </span>
                        </div>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>권장 재고</span>
                          <span className={s.heroMetricVal} style={{ color: acfg.color }}>
                            {report.inventory_advice !== '-' ? report.inventory_advice : '-'}
                          </span>
                        </div>
                        <div className={s.heroMetric}>
                          <span className={s.heroMetricLabel}>위험도</span>
                          <span className={s.heroMetricVal} style={{ color: riskColor }}>
                            {metrics?.risk ?? '-'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* AI 판단 근거 */}
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

                {/* ── Section 1.5: AI 가격 인사이트 ── */}
                {priceData && priceData.price_insight && (
                  <PriceInsightSection priceData={priceData} category={category} />
                )}

                {/* ── Section 2: 핵심 지표 ── */}
                <div className={s.section}>
                  <p className={s.sectionLabel}>핵심 지표</p>
                  <div className={s.metricsRow}>
                    <div className={s.metricCard}>
                      <p className={s.metricLabel}>성장률</p>
                      <p className={s.metricVal}
                        style={{ color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
                        {growthStr}
                      </p>
                      <p className={s.metricSub}>전기 대비 관심도 변화</p>
                    </div>
                    <div className={s.metricCard}>
                      <p className={s.metricLabel}>추천 타깃</p>
                      <p className={s.metricVal} style={{ color: '#6366f1', fontSize: '22px' }}>
                        {report.target_segment !== '-' ? report.target_segment : '-'}
                      </p>
                      <p className={s.metricSub}>
                        {report.price_range !== '-' ? `추천 가격대 ${report.price_range}` : 'AI 추천 소비 타깃'}
                      </p>
                    </div>
                    <div className={s.metricCard}>
                      <p className={s.metricLabel}>핵심 키워드</p>
                      <div className={s.kwChips}>
                        {kwList.length > 0
                          ? kwList.map((kw, i) => (
                              <span key={i} className={s.kwChip}>{kw}</span>
                            ))
                          : <span className={s.metricSub}>-</span>
                        }
                      </div>
                    </div>
                  </div>
                </div>

                {/* ── Section 3: 기회 & 위험 요인 ── */}
                <div className={s.section}>
                  <p className={s.sectionLabel}>기회 & 위험 요인</p>
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

                {/* ── Section 4: AI 종합 결론 ── */}
                <div className={s.section}>
                  <p className={s.sectionLabel}>AI 종합 결론</p>
                  <div className={s.conclusionCard}>
                    <div className={s.conclusionHeader}>
                      <span className={s.ragBadge}>RAG 강화</span>
                      <p className={s.conclusionSub}>{category} · AI 생성 분석</p>
                    </div>
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
                    {brands.length > 0 && (
                      <div className={s.brandsWrap}>
                        {brands.slice(0, 6).map((b, i) => (
                          <span key={i} className={s.brandChip}>
                            <span className={s.brandDot} style={{ background: BRAND_COLORS[i % BRAND_COLORS.length] }} />
                            {b.brand} <strong>{b.pct}%</strong>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* ── Section 5: 실행 전략 ── */}
                {(report.product_strategy?.length > 0 || report.sales_strategy?.length > 0 || report.service_strategy?.length > 0) && (
                  <div className={s.section}>
                    <p className={s.sectionLabel}>실행 전략</p>
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
              </>
            )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            periods={PERIODS} period={period} setPeriod={setPeriod}
            dataSources={['네이버 DataLab', 'Groq LLM', 'RAG (구매 패턴)']}
            onRefresh={loadData} loading={loading} fetchedAt={fetchedAt}
            onDownload={() => window.print()}
          />
        </div>
      </div>
    </div>
  );
}
