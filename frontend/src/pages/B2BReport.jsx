import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import B2BSidebar from '../components/common/B2BSidebar';
import B2BPrintModal from '../components/common/B2BPrintModal';
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

function SectionHead({ num, title }) {
  return (
    <div className={s.sectionHead}>
      <span className={s.sectionNum}>{num}</span>
      <span className={s.sectionTitle}>{title}</span>
      <span className={s.sectionLine} />
    </div>
  );
}

/* backward-compat: 구 string 배열 → {title, evidence, meaning} */
function normFactor(item) {
  if (!item) return { title: '-', evidence: '-', meaning: '-' };
  if (typeof item === 'string') {
    const colon = item.indexOf(': ');
    return { title: colon > -1 ? item.slice(0, colon) : item, evidence: colon > -1 ? item.slice(colon + 2) : '', meaning: '' };
  }
  return { title: item.title ?? '-', evidence: item.evidence ?? '-', meaning: item.meaning ?? '-' };
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
  const [forecastData, setForecastData] = useState(null);
  const [accuracy,  setAccuracy]      = useState(null);
  const [printModal, setPrintModal]     = useState(false);
  const [marketModal, setMarketModal]   = useState(false);

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin';
  const loadData = () => setRefreshTick(t => t + 1);

  useEffect(() => {
    if (!isB2BActive) return;
    setLoading(true); setError(null); setData(null); setPriceData(null); setForecastData(null);
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API_BASE}/api/b2b/ai-report?category=${encodeURIComponent(category)}&period=${period}`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/b2b/price?category=${encodeURIComponent(category)}`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/b2b/demand-forecast?category=${encodeURIComponent(category)}&period=${period}`, { headers }).then(r => r.json()),
    ])
      .then(([d, pd, fd]) => {
        setData(d); setPriceData(pd); setForecastData(fd);
        setFetchedAt(new Date()); setLoading(false);
      })
      .catch(() => { setError('서버에 연결할 수 없습니다'); setLoading(false); });
  }, [category, period, isB2BActive, refreshTick]);

  useEffect(() => {
    if (!isB2BActive) return;
    fetch(`${API_BASE}/api/b2b/prediction-accuracy?days=90`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setAccuracy).catch(() => {});
  }, [isB2BActive, token]);

  if (!isB2BActive) return <AccessDenied user={user} navigate={navigate} />;

  const report  = data?.report;
  const metrics = data?.metrics;
  const brands  = data?.brands ?? [];
  const ctx     = data?.context ?? {};
  const action  = report?.action ?? '관망';
  const acfg    = ACTION_CONFIG[action] ?? ACTION_CONFIG['관망'];

  const growth    = metrics?.growth_rate;
  const growthStr = growth != null ? `${growth >= 0 ? '+' : ''}${growth}%` : '-';
  const riskColor = RISK_COLOR[metrics?.risk] ?? '#8e8e93';
  const today     = fetchedAt
    ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });

  const ins       = priceData?.price_insight;
  const psum      = priceData?.summary;
  const insSignal = ins?.signal
    ? (Object.keys(SIGNAL_CFG).find(k => ins.signal.includes(k)) ?? ins.signal.slice(0, 6))
    : '-';
  const sigCfg    = ins ? (SIGNAL_CFG[insSignal] ?? SIGNAL_CFG['적정가']) : null;

  const oppList  = Array.isArray(report?.opportunity)  ? report.opportunity  : (report?.opportunity  ? [report.opportunity]  : []);
  const riskList = Array.isArray(report?.risk_summary) ? report.risk_summary : (report?.risk_summary ? [report.risk_summary] : []);
  const basisList = report?.action_basis ?? [];
  const kwList    = report?.key_keywords ?? [];

  /* forecast */
  const timing    = forecastData?.timing_signal;
  const ragInsight = forecastData?.rag_insight ?? {};
  const fcConf    = forecastData?.confidence;
  const fcDir     = forecastData?.trend_direction;
  const TIMING_CFG = {
    buy:  { color: '#10b981', bg: 'rgba(16,185,129,0.07)', border: 'rgba(16,185,129,0.2)' },
    hold: { color: '#6366f1', bg: 'rgba(99,102,241,0.07)', border: 'rgba(99,102,241,0.2)' },
    wait: { color: '#f59e0b', bg: 'rgba(245,158,11,0.07)', border: 'rgba(245,158,11,0.2)' },
  };
  const tcfg = timing ? (TIMING_CFG[timing.type] ?? TIMING_CFG.hold) : null;

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>
        <div className={s.layout}>
          <div className={s.main}>

            {loading && (
              <div className={s.loadingWrap}>
                <div className={s.spinner} />
                <p>"{category}" B2B 전략 리포트 생성 중...</p>
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
                      <p className={s.reportLabel}>B2B 상품 운영 전략 리포트</p>
                      <h1 className={s.reportTitle}>{category} B2B 판매 전략 리포트</h1>
                      <p className={s.reportMeta}>{today} 기준 &nbsp;·&nbsp; {PERIOD_LABEL[period]} &nbsp;·&nbsp; 네이버 DataLab · Groq LLM</p>
                    </div>
                    <div className={s.reportActionBadge} style={{ background: acfg.bg, borderColor: acfg.border }}>
                      <span className={s.reportActionIcon} style={{ color: acfg.color }}>{acfg.icon}</span>
                      <span className={s.reportActionText} style={{ color: acfg.color }}>{action}</span>
                    </div>
                  </div>
                  <div className={s.reportKpiRow}>
                    {[
                      { label: '검색 관심도',  val: metrics?.trend_score != null ? metrics.trend_score : '-',
                        sub: metrics?.avg_score != null ? `기간 평균 ${metrics.avg_score} 대비` : '현재 지수',
                        color: metrics?.trend_score != null && metrics?.avg_score != null
                          ? (metrics.trend_score >= metrics.avg_score ? '#10b981' : '#ef4444') : undefined },
                      { label: '시장 성장률',  val: growthStr, sub: '전기 대비 (기간 전반 vs 후반)', color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' },
                      { label: '가격 신호',    val: insSignal, sub: '매입 시그널', color: sigCfg?.color },
                      { label: '시장 평균가',  val: psum?.avg_price ? fmt만(psum.avg_price) : '-', sub: '네이버 쇼핑 기준' },
                      ...(accuracy?.overall_accuracy != null
                        ? [{ label: 'AI 적중률', val: `${accuracy.overall_accuracy}%`, sub: '최근 90일', color: '#6366f1' }]
                        : []),
                    ].map(({ label, val, sub, color }) => (
                      <div key={label} className={s.reportKpi}>
                        <p className={s.reportKpiLabel}>{label}</p>
                        <p className={s.reportKpiVal} style={color ? { color } : {}}>{val}</p>
                        <p className={s.reportKpiSub}>{sub}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── 01 AI 핵심 요약 & 매입 권고 ── */}
                <div className={s.section}>
                  <SectionHead num="01" title="AI 핵심 요약 & 매입 권고" />

                  <div className={s.heroBanner} style={{ background: acfg.bg, borderColor: acfg.border }}>
                    {/* 최종 권고 */}
                    <div className={s.heroTopRow}>
                      <div className={s.heroActionPill} style={{ color: acfg.color, borderColor: acfg.border }}>
                        <span>{acfg.icon}</span> 최종 권고: {action}
                      </div>
                      {report.risk_factor && report.risk_factor !== '-' && (
                        <span className={s.heroRiskBadge} style={{ color: riskColor, borderColor: `${riskColor}44`, background: `${riskColor}0e` }}>
                          핵심 리스크: {report.risk_factor}
                        </span>
                      )}
                    </div>

                    {/* 판단 문장 */}
                    {report.action_reason && (
                      <p className={s.heroJudgeText}>{report.action_reason}</p>
                    )}

                    {/* 4-grid: 권장 상품군·가격대·재고·시기 */}
                    <div className={s.heroDecisionGrid}>
                      {[
                        { label: '권장 상품군',  val: report.recommended_products !== '-' ? report.recommended_products : '-', color: acfg.color },
                        { label: '권장 가격대',  val: report.price_range !== '-' ? report.price_range : (psum?.avg_price ? `${fmt만(psum.avg_price)} 수준` : '-'), color: acfg.color },
                        { label: '권장 재고',    val: report.inventory_advice !== '-' ? report.inventory_advice : '-', color: acfg.color },
                        { label: '권장 시기',    val: report.timing !== '-' ? report.timing : '-', color: acfg.color },
                      ].map(({ label, val, color }) => (
                        <div key={label} className={s.heroDecisionItem}>
                          <p className={s.heroDecisionLabel}>{label}</p>
                          <p className={s.heroDecisionVal} style={{ color }}>{val}</p>
                        </div>
                      ))}
                    </div>

                    {/* 핵심 키워드 */}
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

                  {/* Decision Score */}
                  {(() => {
                    const g = metrics?.growth_rate ?? 0
                    const scoreItems = [
                      { label: '검색 트렌드',  score: Math.max(-15, Math.min(22, Math.round(g * 0.8 + (g >= 0 ? 12 : 8)))) },
                      { label: '계절성',       score: ctx?.peak_months ? 18 : 8 },
                      { label: '가격 안정성',  score: ins?.signal?.includes('매입') ? 12 : ins?.signal?.includes('적정') ? 8 : 4 },
                      { label: '소비자 니즈',  score: Math.min((report?.consumer_needs?.length ?? 0) * 4 + 6, 14) },
                      { label: '브랜드 경쟁',  score: -(brands.length > 5 ? 10 : brands.length > 3 ? 7 : 4) },
                      { label: '재고 리스크',  score: -(metrics?.risk === '높음' ? 10 : metrics?.risk === '중간' ? 6 : 3) },
                    ]
                    const totalScore = scoreItems.reduce((s, item) => s + item.score, 0)
                    return (
                      <div className={s.decisionScoreCard}>
                        <div className={s.dsHeader}>
                          <p className={s.dsTitle}>Decision Score</p>
                          <div className={s.dsTotalPill} style={{ background: acfg.bg, color: acfg.color, borderColor: acfg.border }}>
                            총 {totalScore}점 &nbsp;·&nbsp; {action}
                          </div>
                        </div>
                        <div className={s.dsScoreGrid}>
                          {scoreItems.map(({ label, score }) => (
                            <div key={label} className={s.dsItem}>
                              <span className={s.dsLabel}>{label}</span>
                              <div className={s.dsBarWrap}>
                                <div className={s.dsBarFill} style={{
                                  width: `${Math.round(Math.abs(score) / 22 * 100)}%`,
                                  background: score >= 0 ? '#10b981' : '#ef4444',
                                  float: score >= 0 ? 'left' : 'right',
                                }} />
                              </div>
                              <span className={s.dsScore} style={{ color: score >= 0 ? '#10b981' : '#ef4444' }}>
                                {score >= 0 ? `+${score}` : score}
                              </span>
                            </div>
                          ))}
                        </div>
                        <div className={s.dsCriteria}>
                          <span className={totalScore >= 40 ? s.dsCriteriaActive : s.dsCriteriaInactive}>40점 이상 → 매입 확대</span>
                          <span className={s.dsCriteriaDot}>·</span>
                          <span className={totalScore >= 20 && totalScore < 40 ? s.dsCriteriaActive : s.dsCriteriaInactive}>20~39점 → 관망</span>
                          <span className={s.dsCriteriaDot}>·</span>
                          <span className={totalScore < 20 ? s.dsCriteriaActive : s.dsCriteriaInactive}>20점 미만 → 매입 축소</span>
                        </div>
                      </div>
                    )
                  })()}

                  {/* 추천 이유 / 반대 이유 / 최종 판단 */}
                  {(oppList.length > 0 || riskList.length > 0) && (
                    <div className={s.proConRow}>
                      {oppList.length > 0 && (
                        <div className={s.proCard}>
                          <p className={s.proConTitle} style={{ color: '#10b981' }}>추천 이유</p>
                          {oppList.slice(0, 3).map((item, i) => {
                            const f = normFactor(item)
                            return (
                              <div key={i} className={s.proConItem}>
                                <span className={s.proConMark} style={{ color: '#10b981' }}>✓</span>
                                <p className={s.proConText}><strong>{f.title}</strong>{f.meaning ? ` — ${f.meaning}` : ''}</p>
                              </div>
                            )
                          })}
                        </div>
                      )}
                      {riskList.length > 0 && (
                        <div className={s.conCard}>
                          <p className={s.proConTitle} style={{ color: '#f59e0b' }}>반대 이유</p>
                          {riskList.slice(0, 3).map((item, i) => {
                            const f = normFactor(item)
                            return (
                              <div key={i} className={s.proConItem}>
                                <span className={s.proConMark} style={{ color: '#f59e0b' }}>⚠</span>
                                <p className={s.proConText}><strong>{f.title}</strong>{f.meaning ? ` — ${f.meaning}` : ''}</p>
                              </div>
                            )
                          })}
                        </div>
                      )}
                      <div className={s.proConConclusion} style={{ borderColor: acfg.border, background: acfg.bg }}>
                        <p className={s.proConConclusionLabel}>최종 판단</p>
                        <p className={s.proConConclusionText} style={{ color: acfg.color }}>
                          {report.action_reason
                            ? report.action_reason.split(/(?<=[.。])\s+/).filter(Boolean)[0] ?? report.action_reason
                            : `현재는 ${action} 전략의 기대효과가 가장 높다고 판단됩니다.`}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* AI 의사결정 과정 (PASS/RISK) + 사용 데이터 현황 */}
                  <div className={s.decisionRow}>
                    {report.decision_chain?.length > 0 && (
                      <div className={s.decisionChainCard}>
                        <p className={s.decisionChainTitle}>AI 의사결정 과정</p>
                        {[
                          { key: '①', label: '검색 트렌드',  isPass: (metrics?.growth_rate ?? 0) >= 0 },
                          { key: '②', label: '계절성',       isPass: !!ctx?.peak_months },
                          { key: '③', label: '가격 신호',    isPass: !!(ins?.signal?.includes('매입') || ins?.signal?.includes('적정')) },
                          { key: '④', label: '소비자 니즈',  isPass: (report.consumer_needs?.length ?? 0) > 0 },
                        ].map(({ key, label, isPass }, i) => (
                          <div key={i} className={s.dcStep}>
                            <div className={s.dcStepLeft}>
                              <span className={s.dcStepNum} style={{ color: acfg.color }}>{key}</span>
                              <div>
                                <span className={s.dcStepLabel}>{label}</span>
                                {report.decision_chain[i] && (
                                  <p className={s.dcStepDetail}>{report.decision_chain[i].replace(/^[^:]+:\s*/, '')}</p>
                                )}
                              </div>
                            </div>
                            <span className={s.dcBadge} style={{
                              background: isPass ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                              color: isPass ? '#10b981' : '#f59e0b',
                              border: `1px solid ${isPass ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
                            }}>
                              {isPass ? 'PASS ✓' : 'RISK ⚠'}
                            </span>
                          </div>
                        ))}
                        <div className={s.dcStep}>
                          <div className={s.dcStepLeft}>
                            <span className={s.dcStepNum} style={{ color: acfg.color }}>⑤</span>
                            <div>
                              <span className={s.dcStepLabel}>경쟁 구도</span>
                              <p className={s.dcStepDetail}>
                                {brands.length > 0
                                  ? `${brands.slice(0,3).map(b => b.brand ?? b.name ?? '').join('·')} 집중 구조`
                                  : '경쟁 데이터 분석 중'}
                              </p>
                            </div>
                          </div>
                          <span className={s.dcBadge} style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)' }}>
                            RISK ⚠
                          </span>
                        </div>
                        <div className={s.dcFinal} style={{ background: acfg.bg, borderColor: acfg.border, color: acfg.color }}>
                          ⑥ 최종 판단: {action}
                        </div>
                      </div>
                    )}
                    <div className={s.dataStatusCard}>
                      <p className={s.dataStatusTitle}>사용 데이터 현황</p>
                      {[
                        { label: '검색 트렌드', source: '네이버 DataLab',  ok: !!(metrics?.growth_rate != null || metrics?.current_ratio) },
                        { label: '가격 데이터', source: '네이버 쇼핑 API', ok: !!psum },
                        { label: '계절성 분석', source: '과거 12개월',      ok: !!ctx?.peak_months },
                        { label: '리뷰 데이터', source: '소비자 키워드',    ok: (report?.consumer_needs?.length ?? 0) > 0 },
                        { label: '실시간 재고', source: '미연동',           ok: false },
                      ].map(({ label, source, ok }) => {
                        const mark = ok ? '✓' : '△';
                        return (
                          <div key={label} className={s.dataStatusItem}>
                            <span className={s.dataStatusMark} style={{ color: ok ? '#10b981' : '#f59e0b' }}>{mark}</span>
                            <div>
                              <span className={s.dataStatusLabel}>{label}</span>
                              <span className={s.dataStatusSource}>{source}</span>
                            </div>
                          </div>
                        );
                      })}
                      {report.ai_confidence > 0 && (
                        <div className={s.dataStatusConf}>
                          <span style={{ color: acfg.color, fontWeight: 700 }}>AI 신뢰도 {report.ai_confidence}%</span>
                          <span className={s.dataStatusConfNote}>
                            {report.ai_confidence >= 80 ? '충분한 데이터 확보' :
                             report.ai_confidence >= 60 ? '일부 데이터 제한 있음' :
                             '데이터 부족으로 참고 수준'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── 02 시장 현황 요약 ── */}
                <div className={s.section}>
                  <SectionHead num="02" title="시장 현황 요약" />
                  <div className={s.marketOverviewGrid}>
                    {/* 브랜드 경쟁 구도 (top 3) */}
                    <div className={s.tableBlock}>
                      <p className={s.tableBlockTitle}>브랜드 경쟁 구도</p>
                      {brands.length > 0 ? (
                        <table className={s.dataTable}>
                          <thead>
                            <tr><th>브랜드</th><th>점유율</th></tr>
                          </thead>
                          <tbody>
                            {brands.slice(0, 3).map((b, i) => (
                              <tr key={i}>
                                <td>
                                  <span className={s.brandDot2} style={{ background: BRAND_COLORS[i] }} />
                                  {b.brand}
                                </td>
                                <td className={s.numCell}><strong>{b.pct}%</strong></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : <p className={s.emptyText}>데이터 없음</p>}
                      {report.target_segment && report.target_segment !== '-' && (
                        <div className={s.segmentTag}>
                          <span className={s.segmentLabel}>핵심 소비층</span>
                          <span className={s.segmentVal}>{report.target_segment}</span>
                        </div>
                      )}
                    </div>

                    {/* 시장 해석 카드 */}
                    <div className={s.marketInterpCard}>
                      <p className={s.tableBlockTitle}>시장 해석</p>
                      <p className={s.marketInterpText}>
                        관심도는 {PERIOD_LABEL[period]} 기준{' '}
                        <strong style={{ color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
                          {growth != null ? `${Math.abs(growth)}% ${(growth ?? 0) >= 0 ? '상승' : '하락'}
                        ` : '보합'}
                        </strong>
                        이며, {ctx.peak_months ?? '-'} 성수기 진입 전 수요 집중이 예상됩니다.
                      </p>
                      <ul className={s.marketInterpList}>
                        <li>{ctx.peak_months ?? '성수기'} 전 재고 확보 필요</li>
                        <li>검색량 상승 품목 중심 노출 강화</li>
                        {brands.length >= 2 && (
                          <li>{brands[0]?.brand} 중심 경쟁 구조 — 기능 차별화 필요</li>
                        )}
                        {ctx.related?.[0] && (
                          <li>{ctx.related[0].label} 연관 가전 패키지 기회 존재</li>
                        )}
                      </ul>
                      <div className={s.marketKpiRow}>
                        <div className={s.marketKpiItem}>
                          <span className={s.marketKpiLabel}>현재 관심도</span>
                          <span className={s.marketKpiVal}>{metrics?.trend_score ?? '-'}</span>
                        </div>
                        <div className={s.marketKpiItem}>
                          <span className={s.marketKpiLabel}>기간 평균</span>
                          <span className={s.marketKpiVal}>{metrics?.avg_score ?? '-'}</span>
                        </div>
                        <div className={s.marketKpiItem}>
                          <span className={s.marketKpiLabel}>성장률</span>
                          <span className={s.marketKpiVal} style={{ color: (growth ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>{growthStr}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* ── 03 가격 전략 판단 ── */}
                {priceData && (
                  <div className={s.section}>
                    <SectionHead num="03" title="가격 전략 판단" />
                    {!ins && (
                      <p className={s.emptyText} style={{ padding: '20px 0' }}>가격 데이터를 불러오는 중이거나 해당 카테고리의 가격 분석 데이터가 없습니다.</p>
                    )}
                    {ins && (<>

                    {/* 핵심 전략 카드 */}
                    <div className={s.strategyTopGrid}>
                      {[
                        { label: '가격 신호',     val: insSignal ?? '-', color: sigCfg?.color },
                        { label: '재고 전략',     val: report.inventory_advice !== '-' ? report.inventory_advice : '-' },
                        { label: '주력 브랜드',   val: report.brand_focus || (brands[0]?.brand ?? '-') },
                        { label: '주력 제품군',   val: report.recommended_products !== '-' ? report.recommended_products : '-' },
                        { label: '매입 시점',     val: report.timing !== '-' ? report.timing : (timing?.label ?? '-') },
                        { label: '핵심 위험 요소', val: report.risk_factor !== '-' ? report.risk_factor : (riskList[0] ? normFactor(riskList[0]).title : '-') },
                      ].map(({ label, val, color }) => (
                        <div key={label} className={s.strategyTopItem}>
                          <p className={s.strategyTopLabel}>{label}</p>
                          <p className={s.strategyTopVal} style={color ? { color } : {}}>{val}</p>
                        </div>
                      ))}
                    </div>

                    {/* 4 가격 KPI */}
                    <div className={s.priceKpiRow}>
                      {[
                        { label: '시장 평균가', val: fmt만(psum?.avg_price) },
                        { label: '중위가',      val: fmt만(psum?.median_price) },
                        { label: '최저가',      val: fmt만(psum?.min_price) },
                        { label: '권장 판매가', val: report.price_range !== '-' ? report.price_range : '-', color: acfg.color },
                      ].map(({ label, val, color }) => (
                        <div key={label} className={s.priceKpiItem}>
                          <p className={s.priceKpiLabel}>{label}</p>
                          <p className={s.priceKpiVal} style={color ? { color } : {}}>{val}</p>
                        </div>
                      ))}
                    </div>

                    {/* 가격 시그널 */}
                    <div className={s.priceSignalRow} style={{ borderColor: sigCfg?.border, background: sigCfg?.bg }}>
                      <span className={s.priceSignalBadge} style={{ color: sigCfg?.color, borderColor: sigCfg?.border }}>
                        {insSignal}
                      </span>
                      <span className={s.priceSignalReason}>{ins.reason}</span>
                    </div>

                    {/* 가격 포지셔닝 판단 */}
                    {ins.strategy && ins.strategy !== '-' && (
                      <div className={s.positioningCard}>
                        <p className={s.positioningTitle}>가격 포지셔닝 판단</p>
                        <p className={s.positioningText}>{ins.strategy}</p>
                      </div>
                    )}
                  </>)}
                  </div>
                )}

                {/* ── 04 수요 예측 & 매입 타이밍 ── */}
                {forecastData && !forecastData.error && timing && (
                  <div className={s.section}>
                    <SectionHead num="04" title="수요 예측 & 매입 타이밍" />

                    {/* 타이밍 KPI */}
                    <div className={s.forecastKpiRow}>
                      {[
                        { label: '수요 피크',    val: forecastData.peak_period?.slice(0, 7) ?? '-' },
                        { label: '매입 권장',     val: timing.label, color: tcfg?.color },
                        { label: '성수기 진입까지', val: timing.days_to_peak > 0 ? `D-${timing.days_to_peak}일` : '피크 통과', color: tcfg?.color },
                        { label: '예측 신뢰도',   val: fcConf != null ? `${fcConf}%` : '-',
                          color: fcConf >= 80 ? '#10b981' : fcConf >= 60 ? '#f59e0b' : '#ef4444' },
                        { label: '트렌드',        val: fcDir === '상승' ? '↑ 상승' : fcDir === '하락' ? '↓ 하락' : '→ 안정', color: fcDir === '상승' ? '#10b981' : fcDir === '하락' ? '#ef4444' : '#6366f1' },
                      ].map(({ label, val, color }) => (
                        <div key={label} className={s.forecastKpiItem}>
                          <p className={s.forecastKpiLabel}>{label}</p>
                          <p className={s.forecastKpiVal} style={color ? { color } : {}}>{val}</p>
                        </div>
                      ))}
                    </div>

                    {/* 예측 모델 정보 + 신뢰도 이유 */}
                    <div className={s.forecastModelRow}>
                      <div className={s.forecastDataSources}>
                        <span className={s.forecastDataLabel}>예측에 사용된 데이터</span>
                        {['검색량', '계절성', '가격 신호', '소비자 반응', 'RAG 인사이트'].map(src => (
                          <span key={src} className={s.forecastDataChip}>{src}</span>
                        ))}
                        {forecastData.model_info?.used && (
                          <span className={s.forecastModelChip}>
                            {forecastData.model_info.used === 'ensemble' ? 'Prophet + XGBoost 앙상블' :
                             forecastData.model_info.used === 'prophet'   ? 'Prophet 모델' : '선형 회귀'}
                          </span>
                        )}
                      </div>
                      <p className={s.forecastConfNote}>
                        {fcConf >= 80 ? `신뢰도 ${fcConf}% — 데이터가 충분합니다. 예측 결과를 의사결정에 활용하세요.` :
                         fcConf >= 60 ? `신뢰도 ${fcConf}% — 일부 데이터가 부족합니다. 추세 참고 수준으로 활용하세요.` :
                         <>신뢰도 {fcConf}% — 최근 데이터가 부족하여 신뢰도가 낮습니다.{' '}
                           <button className={s.marketModalBtn} onClick={() => setMarketModal(true)}>시장 상황 확인 →</button>
                         </>}
                      </p>
                    </div>

                    {/* 예측 신뢰구간 테이블 */}
                    {forecastData.forecast?.length > 0 && (
                      <div className={s.forecastCiTable}>
                        <p className={s.tableBlockTitle}>수요 예측 구간 (신뢰구간 포함)</p>
                        <table className={s.dataTable}>
                          <thead>
                            <tr>
                              <th>기간</th>
                              <th className={s.numTh}>예측값</th>
                              <th className={s.numTh}>하한</th>
                              <th className={s.numTh}>상한</th>
                              <th className={s.numTh}>오차 범위</th>
                            </tr>
                          </thead>
                          <tbody>
                            {forecastData.forecast.slice(0, 5).map((f, i) => {
                              const hasCI = f.ci_low != null && f.ci_high != null && (f.ci_low > 0 || f.ci_high > 0);
                              const range = hasCI ? Math.round((f.ci_high - f.ci_low) / 2 * 10) / 10 : null;
                              return (
                                <tr key={i}>
                                  <td>{f.period?.slice(0, 7)}</td>
                                  <td className={s.numCell}><strong>{f.predicted}</strong></td>
                                  <td className={s.numCell} style={{ color: hasCI ? '#ef4444' : 'var(--b2b-muted)' }}>
                                    {hasCI ? f.ci_low : '-'}
                                  </td>
                                  <td className={s.numCell} style={{ color: hasCI ? '#10b981' : 'var(--b2b-muted)' }}>
                                    {hasCI ? f.ci_high : '-'}
                                  </td>
                                  <td className={s.numCell} style={{ color: 'var(--b2b-text2)', fontSize: 11 }}>
                                    {range != null ? `±${range}` : '데이터 부족'}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                        {forecastData.forecast.slice(0, 5).every(f => !f.ci_low && !f.ci_high) && (
                          <p style={{ fontSize: 11, color: 'var(--b2b-muted)', marginTop: 8 }}>
                            * 데이터 기간이 짧아 신뢰구간을 계산할 수 없습니다. 3개월 이상 기간을 선택하면 신뢰구간이 표시됩니다.
                          </p>
                        )}
                      </div>
                    )}

                    {/* 타이밍 메시지 */}
                    <div className={s.timingCard} style={{ borderColor: tcfg?.border, background: tcfg?.bg }}>
                      <span className={s.timingBadge} style={{ color: tcfg?.color, borderColor: tcfg?.border }}>
                        {timing.label}
                      </span>
                      <p className={s.timingMessage} style={{ color: tcfg?.color }}>{timing.message}</p>
                    </div>

                    {/* 기회 / 위험 / 전략 from forecast RAG */}
                    {(ragInsight.opportunity?.length > 0 || ragInsight.risk?.length > 0) && (
                      <div className={s.forecastInsightGrid}>
                        {ragInsight.opportunity?.length > 0 && (
                          <div className={s.forecastInsightCard} style={{ borderTopColor: '#10b981' }}>
                            <p className={s.forecastInsightTitle} style={{ color: '#10b981' }}>↑ 기회 요인</p>
                            <ul className={s.forecastInsightList}>
                              {ragInsight.opportunity.map((item, i) => (
                                <li key={i}><span style={{ color: '#10b981' }}>✔</span> {item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {ragInsight.risk?.length > 0 && (
                          <div className={s.forecastInsightCard} style={{ borderTopColor: '#f59e0b' }}>
                            <p className={s.forecastInsightTitle} style={{ color: '#f59e0b' }}>⚠ 위험 요인</p>
                            <ul className={s.forecastInsightList}>
                              {ragInsight.risk.map((item, i) => (
                                <li key={i}><span style={{ color: '#f59e0b' }}>!</span> {item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {ragInsight.strategy?.length > 0 && (
                          <div className={s.forecastInsightCard} style={{ borderTopColor: acfg.color }}>
                            <p className={s.forecastInsightTitle} style={{ color: acfg.color }}>→ 대응 전략</p>
                            <ul className={s.forecastInsightList}>
                              {ragInsight.strategy.map((item, i) => (
                                <li key={i}><span style={{ color: acfg.color }}>→</span> {item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ── 05 소비자 니즈 기반 상품 제안 ── */}
                {(report.consumer_needs?.length > 0 || report.consumer_complaints?.length > 0) && (
                  <div className={s.section}>
                    <SectionHead num="05" title="소비자 니즈 기반 상품 제안" />

                    {report.product_brief && report.product_brief !== '-' && (
                      <div className={s.productBriefBanner}>
                        <span className={s.productBriefIcon} style={{ color: acfg.color }}>◎</span>
                        <p className={s.productBriefText}>{report.product_brief}</p>
                      </div>
                    )}

                    <div className={s.planningGrid}>
                      <div className={s.planningCard}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: '#10b981' }}>
                          <span className={s.planningCardTag} style={{ background: '#10b98118', color: '#10b981' }}>소비자 니즈</span>
                          <p className={s.planningCardSub}>쇼핑 키워드에서 도출</p>
                        </div>
                        <ul className={s.planningList}>
                          {(report.consumer_needs ?? []).filter(v => v && v !== '없음' && v !== '-').map((item, i) => (
                            <li key={i} className={s.planningItem}>
                              <span className={s.planningBullet} style={{ color: '#10b981' }}>→</span>{item}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className={s.planningCard}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: '#f59e0b' }}>
                          <span className={s.planningCardTag} style={{ background: '#f59e0b18', color: '#f59e0b' }}>주요 불만</span>
                          <p className={s.planningCardSub}>불만 키워드에서 도출</p>
                        </div>
                        <ul className={s.planningList}>
                          {(report.consumer_complaints ?? []).filter(v => v && v !== '없음' && v !== '-').map((item, i) => (
                            <li key={i} className={s.planningItem}>
                              <span className={s.planningBullet} style={{ color: '#f59e0b' }}>!</span>{item}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div className={s.planningCard} style={{ gridColumn: '1 / -1' }}>
                        <div className={s.planningCardHead} style={{ borderLeftColor: acfg.color }}>
                          <span className={s.planningCardTag} style={{ background: `${acfg.color}18`, color: acfg.color }}>추천 상품 조건</span>
                          <p className={s.planningCardSub}>니즈 충족 + 불만 해소 기능</p>
                        </div>
                        <div className={s.featureGrid}>
                          {(report.recommended_features ?? []).filter(v => v && v !== '없음' && v !== '-').map((item, i) => (
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
                        {report.price_range !== '-' && (
                          <div className={s.planningFooter}>
                            <span className={s.planningPriceTag}>
                              권장 가격대 <strong>{report.price_range}</strong>
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* 소비자 구매 맥락 */}
                    {(ctx.purpose?.length > 0 || ctx.install?.length > 0 || ctx.related?.length > 0) && (
                      <div className={s.buyingContextCard}>
                        <p className={s.tableBlockTitle}>소비자 구매 맥락</p>
                        <div className={s.buyingContextGrid}>
                          {ctx.purpose?.length > 0 && (
                            <div className={s.buyingContextItem}>
                              <p className={s.buyingContextLabel}>구매 목적</p>
                              <div className={s.buyingContextTags}>
                                {ctx.purpose.slice(0, 3).map((p, i) => (
                                  <span key={i} className={s.contextTag}>{p.label} {p.pct}%</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {ctx.install?.length > 0 && (
                            <div className={s.buyingContextItem}>
                              <p className={s.buyingContextLabel}>설치 형태</p>
                              <div className={s.buyingContextTags}>
                                {ctx.install.slice(0, 3).map((p, i) => (
                                  <span key={i} className={s.contextTag}>{p.label} {p.pct}%</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {ctx.related?.length > 0 && (
                            <div className={s.buyingContextItem}>
                              <p className={s.buyingContextLabel}>연관 가전</p>
                              <div className={s.buyingContextTags}>
                                {ctx.related.slice(0, 3).map((p, i) => (
                                  <span key={i} className={s.contextTag}>{p.label}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {ctx.region?.length > 0 && (
                            <div className={s.buyingContextItem}>
                              <p className={s.buyingContextLabel}>주요 지역</p>
                              <div className={s.buyingContextTags}>
                                {ctx.region.slice(0, 3).map((p, i) => (
                                  <span key={i} className={s.contextTag}>{p.label} {p.pct}%</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ── 06 AI 실행 전략 & 예상 효과 ── */}
                <div className={s.section}>
                  <SectionHead num="06" title="AI 실행 전략 & 예상 효과" />

                  {/* 기회 / 위험 요인 — 근거 + 의미 구조 */}
                  {(oppList.length > 0 || riskList.length > 0) && (
                    <div className={s.factorGrid}>
                      {oppList.length > 0 && (
                        <div className={s.factorCard}>
                          <p className={s.factorHeader}>
                            <span className={s.factorDot} style={{ background: '#10b981' }} />시장 기회
                          </p>
                          <div className={s.factorList}>
                            {oppList.map((item, i) => {
                              const f = normFactor(item);
                              return (
                                <div key={i} className={s.factorItem2}>
                                  <p className={s.factorItemTitle} style={{ color: '#10b981' }}>{i + 1}. {f.title}</p>
                                  {f.evidence && <p className={s.factorItemEv}><span className={s.factorEvLabel}>근거</span>{f.evidence}</p>}
                                  {f.meaning  && <p className={s.factorItemMean}><span className={s.factorMeanLabel}>의미</span>{f.meaning}</p>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      {riskList.length > 0 && (
                        <div className={s.factorCard}>
                          <p className={s.factorHeader}>
                            <span className={s.factorDot} style={{ background: '#f59e0b' }} />위험 요인
                          </p>
                          <div className={s.factorList}>
                            {riskList.map((item, i) => {
                              const f = normFactor(item);
                              return (
                                <div key={i} className={s.factorItem2}>
                                  <p className={s.factorItemTitle} style={{ color: '#f59e0b' }}>{i + 1}. {f.title}</p>
                                  {f.evidence && <p className={s.factorItemEv}><span className={s.factorEvLabel}>근거</span>{f.evidence}</p>}
                                  {f.meaning  && <p className={s.factorItemMean}><span className={s.factorMeanLabel}>의미</span>{f.meaning}</p>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 실행 전략 (근거 포함) */}
                  {(report.product_strategy?.length > 0 || report.sales_strategy?.length > 0 || report.service_strategy?.length > 0) && (
                    <div className={s.strategyGrid}>
                      {[
                        { num: '①', title: '제품 전략',   items: report.product_strategy  ?? [], color: '#6366f1', basis: basisList[3] ?? basisList[0] },
                        { num: '②', title: '판매 전략',   items: report.sales_strategy    ?? [], color: '#10b981', basis: basisList[0] ?? basisList[1] },
                        { num: '③', title: '서비스 전략', items: report.service_strategy  ?? [], color: '#f59e0b', basis: basisList[1] ?? basisList[2] },
                      ].map(({ num, title, items, color, basis }) => (
                        <div key={title} className={s.strategyCard} style={{ borderTopColor: color }}>
                          <p className={s.strategyTitle}><span style={{ color }}>{num}</span> {title}</p>
                          {basis && (
                            <p className={s.strategyBasis}>
                              <span className={s.strategyBasisLabel}>근거</span>{basis.split('—')[0]?.trim() ?? basis}
                            </p>
                          )}
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
                  )}

                  {/* 예상 효과 */}
                  {report.expected_effects?.length > 0 && (
                    <div className={s.effectSimpleCard}>
                      <p className={s.tableBlockTitle}>예상 효과</p>
                      <ul className={s.effectSimpleList}>
                        {report.expected_effects.map((item, i) => (
                          <li key={i} className={s.effectSimpleItem}>
                            <span style={{ color: acfg.color, fontWeight: 900 }}>{['①','②','③','④'][i]}</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* AI 최종 판단 (한 줄) */}
                  <div className={s.conclusionCard}>
                    <div className={s.conclusionHeader}>
                      <span className={s.ragBadge}>AI 최종 판단</span>
                    </div>
                    <p className={s.conclusionOneLine} style={{ color: acfg.color }}>
                      {report.action_reason
                        ? (report.action_reason.split(/(?<=[.。])\s+/).filter(Boolean)[0] ?? report.action_reason)
                        : `현재는 ${action} 전략의 기대효과가 가장 높다고 판단됩니다.`}
                    </p>
                  </div>
                </div>

                {/* ── 이번 주 Action List ── */}
                {report.action_list?.length > 0 && (
                  <div className={s.section}>
                    <SectionHead num="07" title="이번 주 꼭 해야 할 Action List" />
                    <div className={s.actionListCard}>
                      {report.action_list.map((item, i) => (
                        <div key={i} className={s.actionListItem} style={{ borderLeftColor: i < 2 ? acfg.color : i < 4 ? '#f59e0b' : '#6b7280' }}>
                          <div className={s.actionListLeft}>
                            <div className={s.actionStars}>
                              {Array.from({ length: 5 }).map((_, si) => (
                                <span key={si} style={{ color: si < item.stars ? '#f59e0b' : '#374151', fontSize: 14 }}>★</span>
                              ))}
                            </div>
                            <p className={s.actionText}>{item.action}</p>
                          </div>
                          <div className={s.actionListRight}>
                            {item.budget && item.budget !== '별도 예산 없음' && (
                              <span className={s.actionBudget}>{item.budget}</span>
                            )}
                            <span className={s.actionDept}>{item.dept}</span>
                            <span className={s.actionTiming} style={{ color: i < 2 ? acfg.color : '#6b7280' }}>{item.timing}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── 데이터 출처 & 분석 방법론 ── */}
                <div className={s.dataSourceSection}>
                  <p className={s.dataSourceTitle}>데이터 출처 및 분석 방법론</p>
                  <div className={s.dataSourceGrid}>
                    {[
                      { name: '네이버 DataLab', desc: '검색 트렌드 · 연령별 관심도', icon: '📊' },
                      { name: '네이버 쇼핑 API', desc: '브랜드 점유율 · 가격 · 쇼핑 키워드', icon: '🛒' },
                      { name: '네이버 블로그/카페', desc: '소비자 리뷰 · 불만 데이터', icon: '💬' },
                      { name: 'Groq LLM', desc: 'AI 전략 분석 · 인사이트 생성', icon: '🤖' },
                      { name: 'Prophet + XGBoost', desc: '수요 예측 앙상블 모델 (공공데이터 외부변수 반영)', icon: '📈' },
                      { name: 'RAG (pgvector)', desc: '소비자 반응 패턴 기반 인사이트', icon: '🧠' },
                      { name: '기상청 ASOS', desc: '기온·습도 기반 수요 외부 변수 (data.go.kr)', icon: '🌤' },
                      { name: '에어코리아', desc: 'PM2.5·PM10 대기질 지수 (data.go.kr)', icon: '🌫' },
                    ].map(src => (
                      <div key={src.name} className={s.dataSourceItem}>
                        <p className={s.dataSourceName}>{src.icon} {src.name}</p>
                        <p className={s.dataSourceDesc}>{src.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── 리포트 푸터 ── */}
                <div className={s.reportFooter}>
                  <span>본 리포트는 네이버 DataLab · 기상청 ASOS 등 공공데이터 및 Groq LLM 기반 AI 분석으로 생성되었습니다.</span>
                  <span>{today} · {PERIOD_LABEL[period]} 분석</span>
                </div>
              </>
            )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            periods={PERIODS} period={period} setPeriod={setPeriod}
            dataSources={['네이버 DataLab', 'Groq LLM', 'RAG (구매 패턴)', '기상청 ASOS (공공데이터)']}
            onRefresh={loadData} loading={loading} fetchedAt={fetchedAt}
            onDownload={() => setPrintModal(true)}
          />
        </div>
      </div>
      <B2BPrintModal
        open={printModal}
        onClose={() => setPrintModal(false)}
        category={category}
        period={period}
      />

      {/* ── 시장 상황 모달 ── */}
      {marketModal && (
        <div className={s.mmOverlay} onClick={() => setMarketModal(false)}>
          <div className={s.mmPanel} onClick={e => e.stopPropagation()}>
            <div className={s.mmHeader}>
              <div>
                <p className={s.mmLabel}>현재 시장 상황</p>
                <h2 className={s.mmTitle}>{category} 시장 현황 요약</h2>
              </div>
              <button className={s.mmClose} onClick={() => setMarketModal(false)}>✕</button>
            </div>

            {/* KPI 4개 */}
            <div className={s.mmKpiRow}>
              {[
                { label: '검색 관심도', val: metrics?.trend_score ?? '-',
                  sub: metrics?.avg_score != null ? `기간 평균 ${metrics.avg_score}` : '',
                  color: metrics?.trend_score >= metrics?.avg_score ? '#10b981' : '#ef4444' },
                { label: '시장 성장률', val: metrics?.growth_rate != null
                    ? `${metrics.growth_rate >= 0 ? '+' : ''}${metrics.growth_rate}%` : '-',
                  color: (metrics?.growth_rate ?? 0) >= 0 ? '#10b981' : '#ef4444' },
                { label: '시장 위험도', val: metrics?.risk ?? '-',
                  color: metrics?.risk === '낮음' ? '#10b981' : metrics?.risk === '중간' ? '#f59e0b' : '#ef4444' },
                { label: '가격 신호', val: insSignal, color: sigCfg?.color },
              ].map(({ label, val, sub, color }) => (
                <div key={label} className={s.mmKpiItem}>
                  <p className={s.mmKpiLabel}>{label}</p>
                  <p className={s.mmKpiVal} style={{ color }}>{val}</p>
                  {sub && <p className={s.mmKpiSub}>{sub}</p>}
                </div>
              ))}
            </div>

            {/* 브랜드 경쟁 */}
            {brands?.length > 0 && (
              <div className={s.mmBlock}>
                <p className={s.mmBlockTitle}>브랜드 경쟁 구도 (상위 {Math.min(brands.length, 5)}개)</p>
                <div className={s.mmBrandList}>
                  {brands.slice(0, 5).map((b, i) => (
                    <div key={i} className={s.mmBrandRow}>
                      <span className={s.mmBrandName}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: ['#6366f1','#a855f7','#3b82f6','#06b6d4','#10b981'][i], display: 'inline-block', marginRight: 8 }} />
                        {b.brand}
                      </span>
                      <div className={s.mmBrandBarWrap}>
                        <div className={s.mmBrandBar} style={{ width: `${b.pct}%`, background: ['#6366f1','#a855f7','#3b82f6','#06b6d4','#10b981'][i] }} />
                      </div>
                      <span className={s.mmBrandPct}>{b.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 가격 현황 */}
            {priceData?.summary && (
              <div className={s.mmBlock}>
                <p className={s.mmBlockTitle}>가격 현황</p>
                <div className={s.mmPriceRow}>
                  {[
                    { label: '평균가', val: priceData.summary.avg_price ? fmt만(priceData.summary.avg_price) : '-' },
                    { label: '최저가', val: priceData.summary.min_price ? fmt만(priceData.summary.min_price) : '-' },
                    { label: '최고가', val: priceData.summary.max_price ? fmt만(priceData.summary.max_price) : '-' },
                  ].map(({ label, val }) => (
                    <div key={label} className={s.mmPriceItem}>
                      <p className={s.mmPriceLabel}>{label}</p>
                      <p className={s.mmPriceVal}>{val}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 매입 타이밍 */}
            {timing && (
              <div className={s.mmBlock}>
                <p className={s.mmBlockTitle}>매입 타이밍 신호</p>
                <div className={s.mmTimingCard} style={{ background: tcfg?.bg, borderColor: tcfg?.border }}>
                  <span style={{ color: tcfg?.color, fontWeight: 700 }}>{timing.label}</span>
                  <p style={{ color: tcfg?.color, fontSize: 13, marginTop: 6 }}>{timing.message}</p>
                </div>
              </div>
            )}

            <p className={s.mmFooter}>네이버 DataLab · 쇼핑 API 기반 · {today} 기준</p>
          </div>
        </div>
      )}
    </div>
  );
}
