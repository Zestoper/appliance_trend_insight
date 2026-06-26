import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import B2BSidebar from '../components/common/B2BSidebar';
import B2BPrintModal from '../components/common/B2BPrintModal';
import { useAuth } from '../context/AuthContext';
import s from '../styles/B2BForecast.module.css';
import { API_BASE } from '../config';

const PERIODS = [
  { label: '1개월', value: '1m' },
  { label: '3개월', value: '3m' },
  { label: '6개월', value: '6m' },
  { label: '1년',   value: '1y' },
];
const PERIOD_LABEL = { '1m': '최근 1개월', '3m': '최근 3개월', '6m': '최근 6개월', '1y': '최근 1년' };

function SectionHead({ num, title }) {
  return (
    <div className={s.sectionHead}>
      <span className={s.sectionNum}>{num}</span>
      <span className={s.sectionTitle}>{title}</span>
      <span className={s.sectionLine} />
    </div>
  );
}

/* ── 선형회귀 — 추세선용 ── */
function calcRegression(ys) {
  const n = ys.length;
  if (n < 2) return null;
  const xMean = (n - 1) / 2;
  const yMean = ys.reduce((a, b) => a + b, 0) / n;
  const ssxy = ys.reduce((acc, y, i) => acc + (i - xMean) * (y - yMean), 0);
  const ssxx = ys.reduce((acc, _, i) => acc + (i - xMean) ** 2, 0);
  const slope = ssxy / ssxx;
  const intercept = yMean - slope * xMean;
  const ssTot = ys.reduce((acc, y) => acc + (y - yMean) ** 2, 0);
  const ssRes = ys.reduce((acc, y, i) => acc + (y - (slope * i + intercept)) ** 2, 0);
  const r2 = ssTot > 0 ? Math.max(0, Math.min(1, 1 - ssRes / ssTot)) : 0;
  return { slope, intercept, r2 };
}

/* ── 예측 차트 ── */
function ForecastChart({ history, forecast, trainLastRatio }) {
  const reg = useMemo(() => {
    if (!history || history.length < 2) return null;
    return calcRegression(history.map(d => d.ratio));
  }, [history]);

  if (!history || history.length < 2) return <div className={s.noData}>데이터가 없습니다</div>;

  const W = 600, H = 180, padL = 40, padR = 16, padT = 14, padB = 30;

  // 예측값은 2년 학습 스케일 → 표시 스케일로 변환해 차트 경계 연속성 확보
  const lastRatio = history[history.length - 1]?.ratio ?? null;
  const sf = (trainLastRatio && lastRatio && trainLastRatio > 0)
    ? lastRatio / trainLastRatio
    : 1;
  const toDisplay = v => (v ?? 0) * sf;

  const histVals = history.map(d => d.ratio);
  const fcastVals = (forecast ?? []).flatMap(d =>
    [toDisplay(d.yhat ?? d.predicted), toDisplay(d.upper ?? d.ci_high)].filter(v => v != null && v > 0)
  );
  const allVals = [...histVals, ...fcastVals].filter(v => isFinite(v) && v >= 0);
  const maxV = allVals.length ? Math.max(...allVals) * 1.06 : 1;
  const minV = Math.max(0, Math.min(...allVals) * 0.9);
  const range = maxV - minV || 1;

  const totalLen = history.length + (forecast?.length ?? 0);
  const toX = i => padL + (i / Math.max(totalLen - 1, 1)) * (W - padL - padR);
  const toY = v => padT + (H - padT - padB) * (1 - (v - minV) / range);

  const histLine  = history.map((d, i) => `${toX(i).toFixed(1)},${toY(d.ratio).toFixed(1)}`).join(' ');
  const divX      = toX(history.length - 1);
  const fcastPts  = (forecast ?? []).map((d, i) => ({
    x: toX(history.length + i),
    y: toY(toDisplay(d.yhat ?? d.predicted ?? 0)),
  }));
  const fcastLine = fcastPts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const regLine   = reg
    ? history.map((_, i) => {
        const v = Math.max(minV, reg.slope * i + reg.intercept);
        return `${toX(i).toFixed(1)},${toY(v).toFixed(1)}`;
      }).join(' ')
    : null;

  const histIdxs = [0, Math.floor(history.length * 0.45), Math.floor(history.length * 0.82)];
  const xLabels  = [
    ...histIdxs.map(i => ({ x: toX(i), label: (history[i]?.period ?? '').slice(5), color: 'var(--b2b-muted)' })),
    ...(forecast?.length > 0 ? [{ x: toX(totalLen - 1), label: (forecast[forecast.length - 1]?.period ?? '').slice(5), color: '#10b981' }] : []),
  ];
  const yVals = [maxV, (maxV + minV) / 2, minV].map(v => ({ v: Math.round(v), y: toY(v) }));

  return (
    <div className={s.chartWrap}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
        {[0.25, 0.5, 0.75].map(t => (
          <line key={t} x1={padL} x2={W - padR}
            y1={padT + t * (H - padT - padB)} y2={padT + t * (H - padT - padB)}
            stroke="var(--b2b-line)" strokeWidth="1" />
        ))}
        <line x1={divX} y1={padT - 4} x2={divX} y2={H - padB + 4}
          stroke="rgba(99,102,241,0.35)" strokeWidth="1" strokeDasharray="4 3" />
        <text x={divX + 3} y={padT + 1} textAnchor="start" fontSize="8" fill="rgba(99,102,241,0.7)" fontWeight="700">현재</text>
        <polyline points={histLine} fill="none" stroke="#ef4444" strokeWidth="1.5"
          strokeLinecap="round" strokeLinejoin="round" />
        {history.map((d, i) => (
          <circle key={`hd-${i}`} cx={toX(i)} cy={toY(d.ratio)} r="2.5"
            fill="#ef4444" stroke="#ef4444" strokeWidth="0.5" />
        ))}
        {fcastPts.length > 0 && (
          <polyline
            points={`${toX(history.length - 1).toFixed(1)},${toY(history[history.length - 1].ratio).toFixed(1)} ${fcastLine}`}
            fill="none" stroke="#10b981" strokeWidth="1.5"
            strokeDasharray="6 3" strokeLinecap="round" strokeLinejoin="round" />
        )}
        {fcastPts.map((p, i) => (
          <circle key={`fd-${i}`} cx={p.x} cy={p.y} r="2.5"
            fill="#10b981" stroke="#10b981" strokeWidth="0.5" />
        ))}
        {regLine && (
          <polyline points={regLine} fill="none" stroke="#94a3b8" strokeWidth="1.2"
            strokeDasharray="5 3" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
        )}
        <text x={padL + 4} y={padT + 9} textAnchor="start" fontSize="8" fill="var(--b2b-muted)" opacity="0.7">관심도 지수</text>
        {yVals.map(({ v, y }) => (
          <text key={v} x={padL - 5} y={y + 4} textAnchor="end" fontSize="9" fill="var(--b2b-muted)">{v}</text>
        ))}
        {xLabels.map((xl, i) => (
          <text key={i} x={xl.x} y={H - 6} textAnchor="middle" fontSize="9" fill={xl.color}>{xl.label}</text>
        ))}
      </svg>
      <div className={s.chartLegend}>
        <span className={s.legendItem}><span className={s.legendActual} />실제 데이터</span>
        <span className={s.legendItem}><span className={s.legendDashed} />선형회귀 추세선</span>
        <span className={s.legendItem}><span className={s.legendForecast} />Prophet 예측</span>
        <span className={s.legendNote}>* DataLab + Prophet 모델</span>
      </div>
    </div>
  );
}

/* ── 월 숫자 파싱 (한국어 "3월" → 3) ── */
function parseMonthNum(label) {
  return parseInt(label.replace(/[^0-9]/g, ''), 10) || 0;
}

/* ── 성수기 기간 계산 (양수 영향도 월 범위) ── */
function calcPeakSeason(monthlyEffects) {
  if (!monthlyEffects || monthlyEffects.length === 0) return null;
  const pos = monthlyEffects.filter(m => m.effect > 0);
  if (pos.length === 0) return null;
  const nums = pos.map(m => parseMonthNum(m.month));
  return { start: Math.min(...nums), end: Math.max(...nums), count: pos.length };
}


/* ── 영향도 레벨 (▲▲▲ 개수) ── */
function effectLevel(effect, max) {
  const ratio = max > 0 ? Math.abs(effect) / max : 0;
  const count = ratio > 0.66 ? 3 : ratio > 0.33 ? 2 : ratio > 0.08 ? 1 : 0;
  return { count, isPos: effect >= 0 };
}

/* ── Access Denied ── */
function AccessDenied({ user, navigate }) {
  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.denied}>
        <p className={s.deniedTitle}>
          {!user ? '로그인이 필요합니다' : user.user_type !== 'b2b' ? 'B2B 계정 전용입니다' : '승인 대기 중입니다'}
        </p>
        <p className={s.deniedDesc}>
          {!user ? 'B2B 계정으로 로그인해주세요' : 'B2B 가입 후 이용할 수 있어요'}
        </p>
        <button className={s.deniedBtn} onClick={() => navigate(!user ? '/login' : '/b2b')}>
          {!user ? '로그인' : 'B2B 홈으로'}
        </button>
      </div>
    </div>
  );
}

/* ── Main ── */
export default function B2BForecast() {
  const navigate   = useNavigate();
  const { user, token } = useAuth();
  const [category, setCategory] = useState('에어컨');
  const [period, setPeriod]     = useState('3m');
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [fetchedAt, setFetchedAt] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [printModal, setPrintModal] = useState(false);

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin';
  const loadData = () => setRefreshTick(t => t + 1);

  useEffect(() => {
    if (!isB2BActive) return;
    setLoading(true); setError(null); setData(null);
    fetch(`${API_BASE}/api/b2b/demand-forecast?category=${encodeURIComponent(category)}&period=${period}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setError(d.error); setLoading(false); return; }
        setData(d); setFetchedAt(new Date()); setLoading(false);
      })
      .catch(() => { setError('서버에 연결할 수 없습니다'); setLoading(false); });
  }, [category, period, isB2BActive, refreshTick]);

  if (!isB2BActive) return <AccessDenied user={user} navigate={navigate} />;

  const history  = data?.history  ?? [];
  const forecast = data?.forecast ?? [];

  /* ─ 수요 방향 ─ */
  const TREND_CONFIG = {
    상승: { color: '#10b981', icon: '↑' },
    하락: { color: '#ef4444', icon: '↓' },
    유지: { color: '#6366f1', icon: '→' },
  };

  /* ─ 향후 3개월 % 변화 ─ */
  const lastRatio      = history.length > 0 ? history[history.length - 1].ratio : null;
  // 예측값은 2년 학습 스케일 기준 → 동일 스케일의 train_last_ratio 사용
  const trainLastRatio = data?.train_last_ratio ?? null;
  const refRatio       = trainLastRatio ?? lastRatio;   // fallback: display scale
  const next3Avg  = forecast.length > 0
    ? forecast.slice(0, 3).reduce((a, f) => a + (f.yhat ?? f.predicted ?? 0), 0) / Math.min(3, forecast.length)
    : null;
  const trendPct = (refRatio && next3Avg && refRatio > 0)
    ? Math.round((next3Avg - refRatio) / refRatio * 100)
    : null;

  const displayDir = trendPct == null
    ? (data?.trend_direction === '상승' ? '상승' : data?.trend_direction === '하락' ? '하락' : '유지')
    : trendPct > 5 ? '상승' : trendPct < -5 ? '하락' : '유지';
  const tcfg = TREND_CONFIG[displayDir];

  /* ─ 예상 피크 ─ */
  const peakF = forecast.length > 0
    ? forecast.reduce((a, b) => (b.yhat ?? b.predicted ?? 0) > (a.yhat ?? a.predicted ?? 0) ? b : a, forecast[0])
    : null;
  const peakPeriod = data?.peak_period?.slice(0, 7) ?? peakF?.period?.slice(0, 7) ?? '-';
  const peakMonth  = peakPeriod !== '-' ? `${parseInt(peakPeriod.slice(5), 10)}월` : '-';
  const peakVal    = peakF ? Math.round(peakF.yhat ?? peakF.predicted ?? 0) : null;

  /* ─ 시나리오 % — 3개월 평균 기반, 낙관·비관은 기준치 대비 편차 ─ */
  const fore3   = forecast.slice(0, 3);
  const baseY3  = fore3.length
    ? fore3.reduce((s, f) => s + (f.yhat ?? f.predicted ?? 0), 0) / fore3.length
    : 0;
  const optY3   = fore3.length
    ? fore3.reduce((s, f) => s + (f.ci_high ?? f.upper ?? f.yhat ?? f.predicted ?? 0), 0) / fore3.length
    : baseY3 * 1.15;
  const pessY3  = fore3.length
    ? fore3.reduce((s, f) => s + (f.ci_low ?? f.lower ?? f.yhat ?? f.predicted ?? 0), 0) / fore3.length
    : baseY3 * 0.85;

  // 기준: 현재 대비 절대 변화 (train 스케일 기준 비교)
  const basePct = refRatio > 0 ? Math.round((baseY3 - refRatio) / refRatio * 100) : 0;
  // 낙관·비관: 기준치 대비 ± 편차 (항상 낙관 ≥ 0, 비관 ≤ 0)
  const optPct  = refRatio > 0 ? Math.round((Math.max(optY3, baseY3) - baseY3) / refRatio * 100) : 0;
  const pessPct = refRatio > 0 ? Math.round((Math.min(pessY3, baseY3) - baseY3) / refRatio * 100) : 0;

  /* ─ 성수기 기간 ─ */
  const peakSeason = calcPeakSeason(data?.influence?.monthly_effects);

  /* ─ RAG 인사이트 (구조화 JSON) ─ */
  const ri = (data?.rag_insight && typeof data.rag_insight === 'object') ? data.rag_insight : {};

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>
        <div className={s.layout}>
          <div className={s.main}>

            {loading && (
              <div className={s.loadingWrap}>
                <div className={s.spinner} />
                <p>"{category}" 미래 수요 예측 분석 중...</p>
              </div>
            )}
            {error && <div className={s.error}>{error}</div>}

            {!loading && data && (
              <>
                {/* ── 리포트 헤더 ── */}
                {(() => {
                  const today = fetchedAt
                    ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
                    : new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
                  const dirColor = tcfg.color;
                  return (
                    <div className={s.reportHeader}>
                      <div className={s.reportHeaderTop}>
                        <div>
                          <p className={s.reportLabel}>B2B 미래 수요 예측 리포트</p>
                          <h1 className={s.reportTitle}>{category} 수요 예측 분석</h1>
                          <p className={s.reportMeta}>{today} 기준 · {PERIOD_LABEL[period]} · DataLab + Prophet + XGBoost 앙상블</p>
                        </div>
                        <div className={s.reportStatusBadge} style={{ borderColor: `${dirColor}40`, background: `${dirColor}08` }}>
                          <span className={s.reportStatusIcon} style={{ color: dirColor }}>{tcfg.icon}</span>
                          <span className={s.reportStatusText} style={{ color: dirColor }}>{displayDir}</span>
                        </div>
                      </div>
                      <div className={s.reportKpiRow}>
                        {[
                          { label: '수요 방향',   val: `${tcfg.icon} ${displayDir}`, sub: '향후 전망',          color: tcfg.color },
                          { label: '예상 변화율',  val: trendPct != null ? `${trendPct >= 0 ? '+' : ''}${trendPct}%` : '-', sub: '향후 3개월 기준', color: trendPct != null ? (trendPct >= 0 ? '#10b981' : '#ef4444') : undefined },
                          { label: '예상 피크',   val: peakMonth,       sub: '수요 최고점 시점' },
                          { label: '성수기 기간', val: peakSeason ? `${peakSeason.start}~${peakSeason.end}월` : '-', sub: peakSeason ? `약 ${peakSeason.count}개월` : '계절 분석 기반' },
                          { label: '예측 모델',   val: 'Prophet + XGBoost', sub: '앙상블 예측 모델' },
                        ].map(({ label, val, sub, color }) => (
                          <div key={label} className={s.reportKpi}>
                            <p className={s.reportKpiLabel}>{label}</p>
                            <p className={s.reportKpiVal} style={color ? { color } : {}}>{val}</p>
                            <p className={s.reportKpiSub}>{sub}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}

                {/* ── 매입 타이밍 신호 배너 ── */}
                {data?.timing_signal && (() => {
                  const ts = data.timing_signal;
                  const COLOR = { buy: '#10b981', wait: '#ef4444', hold: '#6366f1' };
                  const ICON  = { buy: '▼', wait: '⏸', hold: '─' };
                  const c = COLOR[ts.type] ?? '#6b7280';
                  return (
                    <div className={s.timingBanner} style={{ borderLeftColor: c, background: `${c}0d` }}>
                      <div className={s.timingBannerLeft}>
                        <span className={s.timingBannerIcon} style={{ color: c }}>{ICON[ts.type]}</span>
                        <div>
                          <span className={s.timingBannerLabel} style={{ color: c }}>{ts.label}</span>
                          {ts.days_to_peak > 0 && (
                            <span className={s.timingBannerDays} style={{ color: c }}>
                              {ts.days_to_buy > 0
                                ? ` · 매입까지 D-${ts.days_to_buy}일 · 피크 D-${ts.days_to_peak}일`
                                : ` · 성수기 진입까지 D-${ts.days_to_peak}일 (${ts.peak_period?.slice(0,7)})`}
                            </span>
                          )}
                          <p className={s.timingBannerMsg}>{ts.message}</p>
                        </div>
                      </div>
                      <a className={s.timingBannerCta} href="/b2b/price" style={{ background: c }}>
                        가격 분석 →
                      </a>
                    </div>
                  );
                })()}

                {/* ── Section 1: 예측 차트 ── */}
                <div className={s.section}>
                  <SectionHead num="01" title="관심도 추세 · 예측 차트" />
                  <div className={s.card}>
                    <div className={s.cardHeader}>
                      <div>
                        <p className={s.cardTitle}>미래 수요 예측 차트</p>
                        <p className={s.cardSub}>{category} · {data.time_unit ?? '일별'} 단위 · DataLab + Prophet 모델</p>
                      </div>
                      <span className={s.ragBadge}>RAG 강화</span>
                    </div>
                    <ForecastChart history={history} forecast={forecast} trainLastRatio={trainLastRatio} />
                  </div>
                </div>

                {/* ── Section 2: 예측 지표 3카드 ── */}
                <div className={s.section}>
                  <SectionHead num="02" title="핵심 예측 지표" />
                  <div className={s.metricsRow}>
                    <div className={s.metricCard} style={{ borderTop: `3px solid ${tcfg.color}` }}>
                      <p className={s.metricLabel}>① 수요 방향</p>
                      <p className={s.metricVal} style={{ color: tcfg.color, fontSize: 36, fontWeight: 900, lineHeight: 1.1 }}>
                        {tcfg.icon} {displayDir}
                      </p>
                      <p className={s.metricSub} style={{ color: tcfg.color, fontWeight: 700, fontSize: 13, marginTop: 6 }}>
                        {trendPct != null
                          ? `향후 3개월 ${trendPct >= 0 ? '+' : ''}${trendPct}%`
                          : '앙상블 모델 기반'}
                      </p>
                    </div>
                    <div className={s.metricCard}>
                      <p className={s.metricLabel}>② 예상 피크 시점</p>
                      <p className={s.metricVal} style={{ color: '#6366f1' }}>{peakMonth}</p>
                      <p className={s.metricSub}>
                        {peakVal != null ? `최대 수요 예상 (지수 ${peakVal})` : '수요 최고점 예측'}
                      </p>
                    </div>
                    <div className={s.metricCard}>
                      <p className={s.metricLabel}>③ 성수기 기간</p>
                      {peakSeason ? (
                        <>
                          <p className={s.metricVal} style={{ color: '#f59e0b' }}>
                            {peakSeason.start}월~{peakSeason.end}월
                          </p>
                          <p className={s.metricSub}>계절 수요 집중 ({peakSeason.count}개월)</p>
                        </>
                      ) : (
                        <>
                          <p className={s.metricVal} style={{ color: '#f59e0b' }}>-</p>
                          <p className={s.metricSub}>데이터 부족</p>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── Section 3: 월별 수요 영향도 ── */}
                {data.influence && (
                  <div className={s.section}>
                    <SectionHead num="03" title="월별 수요 영향도 · 계절 분석" />
                    <div className={s.card}>
                      <div className={s.cardHeader}>
                        <div>
                          <p className={s.cardTitle}>계절별 수요 강도</p>
                          <p className={s.cardSub}>
                            성수기 {data.influence.peak_month} · 비수기 {data.influence.low_month}
                          </p>
                        </div>
                        <div style={{ display: 'flex', gap: 10, fontSize: 11, color: 'var(--b2b-muted)' }}>
                          <span style={{ color: '#6366f1', fontWeight: 700 }}>▲</span><span>증가</span>
                          <span style={{ fontWeight: 700 }}>→</span><span>보합</span>
                          <span style={{ color: '#ef4444', fontWeight: 700 }}>▼</span><span>감소</span>
                        </div>
                      </div>
                      <div className={s.monthGrid}>
                        {(() => {
                          const effects = [...(data.influence.monthly_effects ?? [])]
                            .sort((a, b) => parseMonthNum(a.month) - parseMonthNum(b.month));
                          const maxE = Math.max(...effects.map(e => Math.abs(e.effect)), 0.01);
                          return effects.map(({ month, effect }) => {
                            const { count, isPos } = effectLevel(effect, maxE);
                            const pct      = Math.abs(effect) / maxE * 100;
                            const arrows   = count > 0 ? (isPos ? '▲' : '▼').repeat(count) : '→';
                            const arrColor = count === 0 ? 'var(--b2b-muted)' : isPos ? '#6366f1' : '#ef4444';
                            const barColor = count === 0 ? 'rgba(148,163,184,0.4)'
                              : isPos ? 'rgba(99,102,241,0.65)' : 'rgba(239,68,68,0.5)';
                            return (
                              <div key={month} className={s.monthItem}>
                                <span className={s.monthName}>{month}</span>
                                <span className={s.monthArrow} style={{ color: arrColor }}>{arrows}</span>
                                <div className={s.monthBarWrap}>
                                  <div className={s.monthBar} style={{ width: `${pct}%`, background: barColor }} />
                                </div>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Section 4: 5카드 시나리오 그리드 ── */}
                <div className={s.section}>
                  <SectionHead num="04" title="3개월 전망 시나리오 · 기회 및 전략" />
                  <div className={s.scenarioGrid}>

                    {/* ① 수요 시나리오 */}
                    <div className={s.scenarioCard}>
                      <p className={s.scenarioTitle}>① 수요 시나리오</p>
                      <div className={s.scenarioRows}>
                        <div className={s.scenarioRow}>
                          <span className={s.scenarioDot} style={{ background: '#10b981' }} />
                          <span className={s.scenarioLabel}>낙관</span>
                          <span className={s.scenarioDesc}>수요 회복 시</span>
                          <span className={s.scenarioPct} style={{ color: '#10b981' }}>
                            {optPct >= 0 ? '+' : ''}{optPct}%
                          </span>
                        </div>
                        <div className={s.scenarioRow}>
                          <span className={s.scenarioDot} style={{ background: '#6366f1' }} />
                          <span className={s.scenarioLabel}>기준</span>
                          <span className={s.scenarioDesc}>현재 예측</span>
                          <span className={s.scenarioPct} style={{ color: '#6366f1' }}>
                            {basePct >= 0 ? '+' : ''}{basePct}%
                          </span>
                        </div>
                        <div className={s.scenarioRow}>
                          <span className={s.scenarioDot} style={{ background: '#ef4444' }} />
                          <span className={s.scenarioLabel}>비관</span>
                          <span className={s.scenarioDesc}>수요 둔화 지속</span>
                          <span className={s.scenarioPct} style={{ color: '#ef4444' }}>
                            {pessPct <= 0 ? '' : '+'}{pessPct}%
                          </span>
                        </div>
                      </div>
                      <p className={s.scenarioNote}>
                        기준: 현재 대비 · 낙관·비관: 기준치 대비 ±편차
                      </p>
                    </div>

                    {/* ② 월별 예상 수요 */}
                    <div className={s.scenarioCard}>
                      <p className={s.scenarioTitle}>② 월별 예상 수요</p>
                      {(() => {
                        const baseline = data?.monthly_baseline ?? {};
                        const byMonth = forecast.reduce((acc, f) => {
                          const mon = parseInt((f.period ?? '').slice(5, 7), 10);
                          if (!mon) return acc;
                          const val = f.yhat ?? f.predicted ?? 0;
                          if (!acc[mon]) acc[mon] = { mon, sum: val, cnt: 1 };
                          else { acc[mon].sum += val; acc[mon].cnt += 1; }
                          return acc;
                        }, {});
                        const monthRows = Object.values(byMonth)
                          .sort((a, b) => a.mon - b.mon)
                          .map(({ mon, sum, cnt }) => ({ mon, val: sum / cnt }))
                          .slice(0, 5);
                        // 컬럼 레이블: monthly_baseline이 있으면 "전년 동월 대비", 없으면 "현재 대비"
                        const hasBaseline = Object.keys(baseline).length > 0;
                        return (
                          <div className={s.mdTable}>
                            <div className={s.mdHeader}>
                              <span>월</span><span>추세</span>
                              <span>{hasBaseline ? '전년 동월 대비' : '현재 대비'}</span>
                            </div>
                            {monthRows.map(({ mon, val }, i) => {
                              const prev  = i > 0 ? monthRows[i - 1].val : null;
                              const diff  = prev != null ? val - prev : 0;
                              const dir   = prev == null ? null : diff > 0.5 ? 'up' : diff < -0.5 ? 'down' : 'flat';
                              const dirChar  = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '→';
                              // monthly_baseline 우선 사용, 없으면 train_last_ratio 폴백
                              const bval  = baseline[mon] ?? refRatio;
                              const pct   = bval && bval > 0
                                ? Math.round((val - bval) / bval * 100)
                                : null;
                              const pctColor = pct == null ? '#94a3b8'
                                : pct > 0 ? '#10b981' : pct < 0 ? '#ef4444' : '#94a3b8';
                              const dirColor = dir === 'up' ? '#10b981' : dir === 'down' ? '#ef4444' : '#94a3b8';
                              return (
                                <div key={mon} className={s.mdRow}>
                                  <span className={s.mdMonth}>{mon}월</span>
                                  <span className={s.mdDir} style={{ color: dirColor }}>{dirChar}</span>
                                  <span className={s.mdLevel} style={{ color: pctColor, fontWeight: 700 }}>
                                    {pct != null ? `${pct >= 0 ? '+' : ''}${pct}%` : '-'}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}
                      <p className={s.scenarioNote}>2년 월별 평균 대비 예측 변화율</p>
                    </div>

                    {/* ③ 기회 요인 */}
                    <div className={s.scenarioCard}>
                      <p className={s.scenarioTitle}>③ 기회 요인</p>
                      <ul className={s.factorList}>
                        {(ri.opportunity ?? []).length > 0
                          ? ri.opportunity.map((item, i) => (
                              <li key={i} className={s.factorItem}>
                                <span className={s.factorCheck}>✔</span>{item}
                              </li>
                            ))
                          : <li className={s.factorEmpty}>분석 데이터 준비 중</li>
                        }
                      </ul>
                    </div>

                    {/* ④ 위험 요인 */}
                    <div className={s.scenarioCard}>
                      <p className={s.scenarioTitle}>④ 위험 요인</p>
                      <ul className={s.factorList}>
                        {(ri.risk ?? []).length > 0
                          ? ri.risk.map((item, i) => (
                              <li key={i} className={`${s.factorItem} ${s.factorRisk}`}>
                                <span className={s.factorWarn}>⚠</span>{item}
                              </li>
                            ))
                          : <li className={s.factorEmpty}>분석 데이터 준비 중</li>
                        }
                      </ul>
                    </div>

                    {/* ⑤ 구매·판매 전략 (전체 너비) */}
                    <div className={`${s.scenarioCard} ${s.scenarioCardFull}`}>
                      <p className={s.scenarioTitle}>⑤ 예측 기반 실행 전략</p>
                      <ol className={s.strategyList}>
                        {(ri.strategy ?? []).length > 0
                          ? ri.strategy.map((item, i) => (
                              <li key={i} className={s.strategyItem}>
                                <span className={s.strategyNum}>{i + 1}</span>{item}
                              </li>
                            ))
                          : <li className={s.factorEmpty}>분석 데이터 준비 중</li>
                        }
                      </ol>
                    </div>

                  </div>
                </div>

                <div className={s.reportFooter}>
                  <span>
                    본 리포트는 네이버 DataLab + Prophet + XGBoost 앙상블 모델 기반으로 생성되었습니다.
                    {data?.data_sources?.length > 0 && (
                      <span className={s.footerSources}>
                        {' '}· 공공데이터 활용: {data.data_sources.map(ds => `${ds.name}(${ds.var})`).join(', ')}
                      </span>
                    )}
                  </span>
                  <span>{fetchedAt ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) : ''} · {PERIOD_LABEL[period]}</span>
                </div>
              </>
            )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            periods={PERIODS} period={period} setPeriod={setPeriod}
            dataSources={[
              '네이버 DataLab',
              'Prophet (시계열)',
              'XGBoost (앙상블)',
              '선형회귀 (영향도)',
              'Groq LLM',
              ...[...new Set((data?.data_sources ?? []).map(ds => ds.name))].map(n => `${n} (공공데이터)`),
            ]}
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
    </div>
  );
}
