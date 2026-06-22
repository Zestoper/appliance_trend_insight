import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import B2BSidebar from '../components/common/B2BSidebar';
import { useAuth } from '../context/AuthContext';
import s from '../styles/B2BPrice.module.css';
import { API_BASE } from '../config';

const CATEGORIES = ['에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기', 'TV'];
const BRAND_COLORS = ['#6366f1', '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function fmtWon(p) {
  if (p == null) return '-';
  if (p >= 10000) return `${Math.round(p / 10000).toLocaleString()}만원`;
  return `${p.toLocaleString()}원`;
}

// 카테고리별 실제 시장가 기반 tier 기준 (단위: 원)
const TIER_THRESHOLDS = {
  '에어컨':    [800000, 1800000],
  '냉장고':    [700000, 1500000],
  '세탁기':    [600000, 1200000],
  '건조기':    [500000, 1000000],
  '공기청정기': [250000, 600000],
  '로봇청소기': [400000, 900000],
  '식기세척기': [400000, 900000],
  'TV':        [600000, 1500000],
};

function priceTier(avg, category) {
  if (avg == null) return '-';
  const [low, high] = TIER_THRESHOLDS[category] ?? [500000, 1000000];
  if (avg < low)  return '보급형';
  if (avg < high) return '중간';
  return '프리미엄';
}

function tierColor(tier) {
  if (tier === '보급형') return '#10b981';
  if (tier === '중간')   return '#6366f1';
  return '#f59e0b';
}

/* ── Distribution SVG Bar Chart ── */
function DistributionChart({ distribution }) {
  if (!distribution || distribution.length === 0) return <div className={s.noData}>데이터 없음</div>;
  const maxCount = Math.max(...distribution.map(d => d.count), 1);
  const W = 340, H = 110, padB = 28, padT = 12, padL = 28, padR = 6;
  const chartW = W - padL - padR;
  const barW = chartW / distribution.length - 4;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      {/* Y axis unit label — 차트 내부 상단 좌측 */}
      <text x={padL + 3} y={padT + 9} textAnchor="start" fontSize="8" fill="#8e8e93" opacity="0.8">제품 수</text>
      {distribution.map((d, i) => {
        const bh = Math.max(((d.count / maxCount) * (H - padT - padB)), 3);
        const bx = padL + i * (chartW / distribution.length) + 2;
        const by = H - padB - bh;
        return (
          <g key={i}>
            <rect x={bx} y={by} width={barW} height={bh}
              fill={BRAND_COLORS[i % BRAND_COLORS.length]}
              rx="3" opacity="0.85" />
            <text x={bx + barW / 2} y={by - 3} textAnchor="middle" fontSize="8" fill="#8e8e93">
              {d.count}
            </text>
            <text x={bx + barW / 2} y={H - 6} textAnchor="middle" fontSize="7.5" fill="#8e8e93">
              {(d.label ?? d.range ?? '').replace('만원', '')}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ── Price History Line Chart ── */
function PriceHistoryChart({ history }) {
  if (!history || history.length < 2) return null;
  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date));
  const W = 560, H = 130, padL = 56, padR = 16, padT = 14, padB = 28;
  const prices = sorted.map(d => d.avg_price);
  const minP = Math.min(...prices) * 0.97;
  const maxP = Math.max(...prices) * 1.03;
  const rng  = maxP - minP || 1;
  const toX  = i => padL + (i / Math.max(sorted.length - 1, 1)) * (W - padL - padR);
  const toY  = v => padT + (H - padT - padB) * (1 - (v - minP) / rng);
  const pts  = sorted.map((d, i) => `${toX(i).toFixed(1)},${toY(d.avg_price).toFixed(1)}`).join(' ');

  // X 레이블: 최대 4개만
  const step = Math.max(1, Math.floor(sorted.length / 4));
  const xIdx = [0];
  for (let i = step; i < sorted.length - 1; i += step) xIdx.push(i);
  xIdx.push(sorted.length - 1);
  const unique = [...new Set(xIdx)];

  // Y 레이블
  const yMid = (maxP + minP) / 2;
  const yVals = [maxP, yMid, minP];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      {/* Y axis lines */}
      {yVals.map((v, i) => (
        <line key={i} x1={padL} x2={W - padR}
          y1={toY(v)} y2={toY(v)}
          stroke="var(--b2b-line)" strokeWidth="1" />
      ))}
      {/* Y axis labels */}
      {yVals.map((v, i) => (
        <text key={i} x={padL - 5} y={toY(v) + 3.5}
          textAnchor="end" fontSize="8.5" fill="#8e8e93">
          {v >= 10000 ? `${Math.round(v / 10000)}만` : `${Math.round(v / 1000)}천`}
        </text>
      ))}
      {/* Line */}
      <polyline points={pts} fill="none" stroke="#6366f1" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />
      {/* Dots */}
      {sorted.map((d, i) => (
        <circle key={i} cx={toX(i)} cy={toY(d.avg_price)} r="2.5"
          fill="#6366f1" opacity="0.75" />
      ))}
      {/* X labels */}
      {unique.map(i => (
        <text key={i} x={toX(i)} y={H - 6}
          textAnchor="middle" fontSize="8" fill="#8e8e93">
          {sorted[i].date.slice(5)}
        </text>
      ))}
    </svg>
  );
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
          {!user ? 'B2B 계정으로 로그인해주세요' : user.user_type !== 'b2b' ? 'B2B 가입 후 이용할 수 있어요' : '관리자 승인 후 사용 가능합니다'}
        </p>
        <button className={s.deniedBtn} onClick={() => navigate(!user ? '/login' : '/b2b')}>
          {!user ? '로그인' : 'B2B 홈으로'}
        </button>
      </div>
    </div>
  );
}

/* ── Main Page ── */
export default function B2BPrice() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [category, setCategory] = useState('에어컨');
  const [data, setData]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [fetchedAt, setFetchedAt] = useState(null);

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin';

  const loadData = () => {
    if (!isB2BActive) return;
    setLoading(true);
    setError(null);
    setData(null);
    fetch(`${API_BASE}/api/b2b/price?category=${encodeURIComponent(category)}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setFetchedAt(new Date()); setLoading(false); })
      .catch(() => { setError('서버에 연결할 수 없습니다'); setLoading(false); });
  };

  useEffect(() => { loadData(); }, [category, isB2BActive]);

  if (!isB2BActive) return <AccessDenied user={user} navigate={navigate} />;

  // Normalize data fields — API may return summary or flat fields
  const sum = data?.summary ?? data;
  const avgPrice    = sum?.avg_price    ?? data?.avg_price;
  const minPrice    = sum?.min_price    ?? data?.min_price;
  const medianPrice = sum?.median_price ?? data?.median_price;
  const totalProds  = sum?.total_products ?? data?.total_products;
  const distribution = data?.distribution ?? data?.price_distribution ?? [];

  // 가격 변동률 계산 (price_history 배열 활용 — Danawa 백필 데이터)
  const priceHistory = data?.price_history ?? [];
  const priceChangeData = (() => {
    if (priceHistory.length < 2) return null;
    const sorted = [...priceHistory].sort((a, b) => a.date.localeCompare(b.date));
    const current = sorted[sorted.length - 1];
    const sixMonthStr = (() => {
      const d = new Date(); d.setMonth(d.getMonth() - 6); return d.toISOString().slice(0, 10);
    })();
    const past = sorted.find(h => h.date <= sixMonthStr) ?? sorted[0];
    if (past.date === current.date) return null;
    const pct = Math.round((current.avg_price - past.avg_price) / past.avg_price * 1000) / 10;
    const daysAgo = Math.round((Date.now() - new Date(past.date)) / 86400000);
    const periodLabel = daysAgo >= 150 ? '6개월 전' : daysAgo >= 80 ? '3개월 전' : daysAgo >= 25 ? '1개월 전' : `${daysAgo}일 전`;
    return { past: past.avg_price, current: current.avg_price, pct, periodLabel };
  })();

  const brandRows = (data?.by_brand ?? []).map(b => ({ brand: b.brand, avg: b.avg_price, count: b.count }));

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>

        <div className={s.layout}>
          <div className={s.main}>

        {/* ── Loading / Error ── */}
        {loading && (
          <div className={s.loadingWrap}>
            <div className={s.spinner} />
            <p>"{category}" 가격 데이터 수집 중...</p>
          </div>
        )}
        {error && <div className={s.error}>{error}</div>}
        {!loading && data?.error && <div className={s.error}>{data.error}</div>}

        {!loading && data && !data.error && (
          <>
            {/* ── Section 1: Key Price Metrics ── */}
            <div className={s.section}>
              <div className={s.sectionLabelRow}>
                <p className={s.sectionLabel}>핵심 가격 지표</p>
                {totalProds != null && (
                  <span className={s.sectionMeta}>분석 제품 수 {totalProds.toLocaleString()}개 · 네이버 쇼핑 기준</span>
                )}
              </div>
              <div className={s.metricsRow}>
                <div className={s.metricCard}>
                  <p className={s.metricLabel}>평균가</p>
                  <p className={s.metricVal} style={{ color: '#6366f1' }}>{fmtWon(avgPrice)}</p>
                  <p className={s.metricSub}>분석 제품 평균</p>
                </div>
                <div className={s.metricCard}>
                  <p className={s.metricLabel}>최저가</p>
                  <p className={s.metricVal} style={{ color: '#10b981' }}>{fmtWon(minPrice)}</p>
                  <p className={s.metricSub}>현재 최저 판매가</p>
                </div>
                <div className={s.metricCard}>
                  <p className={s.metricLabel}>중간가</p>
                  <p className={s.metricVal} style={{ color: '#3b82f6' }}>{fmtWon(medianPrice)}</p>
                  <p className={s.metricSub}>중앙값 기준</p>
                </div>
              </div>
            </div>

            {/* ── Section 2: Brand Table + 가격 변동률 ── */}
            <div className={s.section}>
              <p className={s.sectionLabel}>가격 경쟁력 분석</p>
              <div className={s.twoCol}>

                {/* Brand Table */}
                <div className={s.darkCard}>
                  <p className={s.darkCardTitle}>브랜드별 가격 분석</p>
                  <p className={s.darkCardSub}>평균 판매가 기준 · 최저~최고가: {fmtWon(minPrice)}~{fmtWon(data?.summary?.max_price ?? data?.max_price)}</p>
                  {brandRows.length > 0 ? (
                    <table className={s.brandTable}>
                      <thead>
                        <tr>
                          <th>브랜드</th>
                          <th>평균가</th>
                          <th>가격 수준</th>
                        </tr>
                      </thead>
                      <tbody>
                        {brandRows.slice(0, 8).map((b, i) => {
                          const tier = priceTier(b.avg, category);
                          return (
                            <tr key={i}>
                              <td className={s.btBrand}>
                                <span className={s.btDot} style={{ background: BRAND_COLORS[i % BRAND_COLORS.length] }} />
                                {b.brand}
                              </td>
                              <td className={s.btPrice}>{fmtWon(b.avg)}</td>
                              <td>
                                <span className={s.tierBadge} style={{ color: tierColor(tier), background: `${tierColor(tier)}18` }}>
                                  {tier}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <div className={s.noData}>브랜드 데이터가 없습니다</div>
                  )}
                </div>

                {/* 가격 변동률 card */}
                <div className={s.card}>
                  <p className={s.cardTitle}>가격 변동률</p>
                  {priceChangeData ? (
                    <div className={s.priceChangeBox}>
                      <div className={s.priceChangeRow}>
                        <span className={s.priceChangeTimeLabel}>{priceChangeData.periodLabel} 평균가</span>
                        <span className={s.priceChangePastVal}>{fmtWon(priceChangeData.past)}</span>
                      </div>
                      <div className={s.priceChangeDivider} />
                      <div className={s.priceChangeRow}>
                        <span className={s.priceChangeTimeLabel}>현재 평균가</span>
                        <span className={s.priceChangeCurrentVal}>{fmtWon(priceChangeData.current)}</span>
                      </div>
                      <p className={`${s.priceChangePct} ${priceChangeData.pct >= 0 ? s.priceChangeUp : s.priceChangeDown}`}>
                        {priceChangeData.pct >= 0 ? '↑' : '↓'} {priceChangeData.pct >= 0 ? '+' : ''}{priceChangeData.pct}%
                      </p>
                    </div>
                  ) : (
                    <div className={s.priceChangeBox}>
                      <p className={s.noData}>이력 데이터 수집 중</p>
                      <p style={{ fontSize: 11, color: 'var(--b2b-text3)', textAlign: 'center' }}>
                        Danawa 백필 실행 후 다음 조회 시 표시됩니다
                      </p>
                    </div>
                  )}
                </div>

              </div>
            </div>

            {/* ── Section 3: 가격 수준별 브랜드 비중 ── */}
            {brandRows.length > 0 && (() => {
              const [low, high] = TIER_THRESHOLDS[category] ?? [500000, 1000000]
              const tierDefs = [
                { key: '프리미엄', label: `프리미엄 (${Math.round(high/10000)}만원 이상)`, color: '#f59e0b' },
                { key: '중간',     label: `중가 (${Math.round(low/10000)}~${Math.round(high/10000)}만원)`, color: '#6366f1' },
                { key: '보급형',   label: `보급형 (${Math.round(low/10000)}만원 이하)`,   color: '#10b981' },
              ]
              const tierCnt = brandRows.reduce((acc, b) => {
                const t = priceTier(b.avg, category)
                acc[t] = (acc[t] || 0) + b.count
                return acc
              }, {})
              const total = Object.values(tierCnt).reduce((a, b) => a + b, 0) || 1
              const bars = tierDefs
                .map(t => ({ ...t, count: tierCnt[t.key] || 0, pct: Math.round((tierCnt[t.key] || 0) / total * 100) }))
                .filter(t => t.count > 0)
              return (
                <div className={s.section}>
                  <p className={s.sectionLabel}>가격 수준별 브랜드 비중</p>
                  <div className={s.card}>
                    <p className={s.cardTitle}>가격 수준별 브랜드 비중</p>
                    <p className={s.cardSub}>브랜드별 판매 제품 수 기준 · 네이버 쇼핑</p>
                    <div className={s.tierBars}>
                      {bars.map(t => (
                        <div key={t.key} className={s.tierBarRow}>
                          <span className={s.tierBarLabel}>{t.label}</span>
                          <div className={s.tierBarTrack}>
                            <div className={s.tierBarFill} style={{ width: `${t.pct}%`, background: t.color }} />
                          </div>
                          <span className={s.tierBarPct} style={{ color: t.color }}>{t.pct}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })()}

            {/* ── Section 4: 가격 이력 차트 ── */}
            {priceHistory.length > 0 && (
              <div className={s.section}>
                <p className={s.sectionLabel}>가격 이력</p>
                <div className={s.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                    <div>
                      <p className={s.cardTitle}>평균가 추이</p>
                      <p className={s.cardSub}>Danawa 수집 기준 · {priceHistory.length}일 이력</p>
                    </div>
                    {priceHistory.length < 14 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 10,
                        background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)' }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b',
                          animation: 'pulse 1.5s infinite' }} />
                        <span style={{ fontSize: 11, color: '#f59e0b', fontWeight: 700 }}>
                          백필 중 ({priceHistory.length}/14일)
                        </span>
                      </div>
                    )}
                  </div>
                  <PriceHistoryChart history={priceHistory} />
                </div>
              </div>
            )}

            {/* ── Section 5: AI 가격 인사이트 ── */}
            {data.price_insight && !data.price_insight._groq_error && (
              (() => {
                const pi = data.price_insight;
                const SIGNAL_CFG = {
                  '매입 적기': { color: '#10b981', bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)' },
                  '관망 권장': { color: '#f59e0b', bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.2)' },
                  '적정가':    { color: '#6366f1', bg: 'rgba(99,102,241,0.06)',  border: 'rgba(99,102,241,0.2)' },
                };
                const scfg = SIGNAL_CFG[pi.signal] ?? SIGNAL_CFG['적정가'];

                const changeCtx = priceChangeData
                  ? `현재 평균 가격은 ${fmtWon(avgPrice)}으로, ${priceChangeData.periodLabel} (${fmtWon(priceChangeData.past)}) 대비 ${priceChangeData.pct >= 0 ? `${priceChangeData.pct}% 상승` : `${Math.abs(priceChangeData.pct)}% 하락`}한 상태입니다.`
                  : null;

                const brandCtx = pi.brand_pick
                  ? `${pi.brand_pick} 등 주요 브랜드의 가격 구조가 ${priceTier(brandRows.find(b => b.brand === pi.brand_pick)?.avg ?? brandRows[0]?.avg, category)} 수준에 형성되어 있습니다.`
                  : null;

                const points = [pi.reason, changeCtx, brandCtx, pi.strategy].filter(Boolean);

                return (
                  <div className={s.section}>
                    <p className={s.sectionLabel}>AI 가격 인사이트</p>
                    <div className={s.insightCard} style={{ background: scfg.bg, borderColor: scfg.border }}>
                      <div className={s.insightHeader}>
                        <span className={s.insightSignalBig} style={{ color: scfg.color }}>{pi.signal}</span>
                        {pi.brand_pick && (
                          <span className={s.insightBrandBadge}>{pi.brand_pick} 납품 추천</span>
                        )}
                      </div>
                      <div className={s.insightPoints}>
                        {points.map((pt, i) => (
                          <div key={i} className={s.insightPointRow}>
                            <span className={s.insightNum} style={{ color: scfg.color }}>
                              {['①','②','③','④'][i]}
                            </span>
                            <p className={s.insightPointText}>{pt}</p>
                          </div>
                        ))}
                      </div>
                      {pi.summary && (
                        <div className={s.insightSummaryBox}>
                          <p className={s.insightSummaryText}>{pi.summary}</p>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })()
            )}

            {/* ── Section 6: 예비 공간 ── */}
            <div className={s.section}>
              <div className={s.emptyPlaceholder} />
            </div>
          </>
        )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            dataSources={['네이버 쇼핑 API', 'Danawa', 'Groq LLM']}
            onRefresh={loadData} loading={loading} fetchedAt={fetchedAt}
            onDownload={() => window.print()}
          />
        </div>
      </div>
    </div>
  );
}
