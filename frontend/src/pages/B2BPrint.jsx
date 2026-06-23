import { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config';
import s from '../styles/B2BPrint.module.css';

/* ── 공통 유틸 ── */
function fmtWon(p) {
  if (p == null) return '-';
  if (p >= 10000) return `${Math.round(p / 10000).toLocaleString()}만원`;
  return `${p.toLocaleString()}원`;
}

/** 어떤 값이든 안전하게 문자열로 변환 (객체·배열은 JSON.stringify) */
function toStr(v) {
  if (v == null) return '-';
  if (typeof v === 'string') return v || '-';
  if (typeof v === 'number') return String(v);
  if (Array.isArray(v)) return v.map(toStr).join(', ');
  try { return JSON.stringify(v); } catch { return '-'; }
}

/** 배열로 변환 — 배열이면 문자열 항목만, 객체면 값들을 펼침, 문자열이면 단일 배열 */
function toArr(v) {
  if (!v) return [];
  if (Array.isArray(v)) return v.filter(x => x != null && x !== '').map(x => (typeof x === 'object' ? toStr(x) : x));
  if (typeof v === 'string' && v !== '-') return [v];
  if (typeof v === 'object') return Object.values(v).filter(x => x != null).map(toStr);
  return [];
}

function SubHead({ num, title }) {
  return (
    <div className={s.subHead}>
      <span className={s.subNum}>{num}</span>
      <span className={s.subTitle}>{title}</span>
    </div>
  );
}

/* ══════════════════════════════════════════
   DASHBOARD SECTIONS
══════════════════════════════════════════ */
function DashboardSection({ data, sections, category }) {
  if (!data) return null;
  const show = (n) => sections.includes(n);

  const trend    = data.trend ?? [];
  const brands   = data.brands ?? [];
  const ageDist  = data.age_distribution ?? [];
  const keywords = data.keywords ?? [];
  const complaints = data.complaints ?? [];
  const complaint_summary = data.complaint_summary ?? [];
  const mr       = data.market_report ?? {};

  const latest = trend[trend.length - 1];

  return (
    <div className={s.pageBlock}>
      <div className={s.pageBlockHeader}>
        <div className={s.pageIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        </div>
        <span className={s.pageBlockTitle}>시장 분석</span>
        <span className={s.pageBlockSub}>{category}</span>
      </div>

      {show('01') && (
        <div className={s.secBlock}>
          <SubHead num="01" title="시장 현황 · 관심도 추이" />
          <div className={s.kpiRow}>
            {[
              { label: '현재 관심도 지수', val: latest?.ratio ?? '-', sub: '최신' },
              { label: '평균 관심도',      val: mr.avg_score != null ? Math.round(mr.avg_score) : '-', sub: '기간 평균' },
              { label: '성장률',           val: mr.growth_rate != null ? `${mr.growth_rate >= 0 ? '+' : ''}${mr.growth_rate}%` : '-', sub: '전기 대비', color: (mr.growth_rate ?? 0) >= 0 ? '#10b981' : '#ef4444' },
              { label: '시장 위험도',      val: mr.risk ?? '-', sub: '종합' },
            ].map(({ label, val, sub, color }) => (
              <div key={label} className={s.kpi}>
                <p className={s.kpiLabel}>{label}</p>
                <p className={s.kpiVal} style={color ? { color } : {}}>{val}</p>
                <p className={s.kpiSub}>{sub}</p>
              </div>
            ))}
          </div>
          {trend.length > 0 && (
            <div className={s.table}>
              <p className={s.tableTitle}>월별 관심도 추이 (최근 {Math.min(trend.length, 8)}개월)</p>
              <table>
                <thead><tr><th>기간</th><th>관심도 지수</th></tr></thead>
                <tbody>
                  {trend.slice(-8).map((t, i) => (
                    <tr key={i}><td>{t.period}</td><td>{t.ratio}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {show('02') && (
        <div className={s.secBlock}>
          <SubHead num="02" title="브랜드 점유율 · 핵심 소비층" />
          <div className={s.twoCol}>
            {brands.length > 0 && (
              <div className={s.table}>
                <p className={s.tableTitle}>브랜드 점유율 (상위 5개)</p>
                <table>
                  <thead><tr><th>브랜드</th><th>점유율</th></tr></thead>
                  <tbody>
                    {brands.slice(0, 5).map((b, i) => (
                      <tr key={i}>
                        <td>{b.brand}</td>
                        <td>
                          <div className={s.barWrap}>
                            <div className={s.bar} style={{ width: `${b.pct ?? 0}%` }} />
                            <span style={{ marginLeft: 6 }}>{b.pct}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {ageDist.length > 0 && (
              <div className={s.table}>
                <p className={s.tableTitle}>연령대별 관심도</p>
                <table>
                  <thead><tr><th>연령대</th><th>비율</th></tr></thead>
                  <tbody>
                    {ageDist.map((a, i) => (
                      <tr key={i}>
                        <td>{a.label ?? a.group ?? '-'}</td>
                        <td>{a.ratio ?? a.pct ?? '-'}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {show('03') && keywords.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="03" title="트렌드 분석 · 관심 키워드" />
          <div className={s.tagRow}>
            {keywords.slice(0, 20).map((kw, i) => (
              <span key={i} className={s.tag}>{typeof kw === 'string' ? kw : kw.keyword ?? kw.word ?? JSON.stringify(kw)}</span>
            ))}
          </div>
        </div>
      )}

      {show('04') && complaints.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="04" title="트렌드 분석 · 소비자 불만 요인" />
          {complaint_summary.length > 0 && (
            <div className={s.table} style={{ marginBottom: 12 }}>
              <p className={s.tableTitle}>불만 키워드 빈도 (상위 5개)</p>
              <table>
                <thead><tr><th>키워드</th><th>언급 수</th></tr></thead>
                <tbody>
                  {complaint_summary.slice(0, 5).map((c, i) => (
                    <tr key={i}><td>{c.tag}</td><td>{c.count}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {complaints.slice(0, 3).map((c, i) => (
            <div key={i} className={s.infoBox} style={{ marginBottom: 8 }}>
              <p className={s.infoTitle}>{c.brand}</p>
              <p className={s.infoText}>{c.title ?? c.complaint?.[0] ?? '-'}</p>
              {c.complaint && c.complaint.length > 0 && (
                <div className={s.tagRow} style={{ marginTop: 6 }}>
                  {c.complaint.slice(0, 5).map((t, j) => <span key={j} className={s.tag}>{t}</span>)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {show('05') && (
        <div className={s.secBlock}>
          <SubHead num="05" title="시장 구조 · 설치 환경 · 구매 목적" />
          {mr.summary && (
            <div className={s.infoBox}>
              <p className={s.infoTitle}>시장 분석 요약</p>
              <p className={s.infoText}>{toStr(mr.summary)}</p>
            </div>
          )}
          {brands.length > 0 && (
            <div className={s.kpiRow} style={{ marginTop: 12 }}>
              <div className={s.kpi}>
                <p className={s.kpiLabel}>대표 브랜드</p>
                <p className={s.kpiVal}>{brands[0]?.brand ?? '-'}</p>
                <p className={s.kpiSub}>점유율 1위</p>
              </div>
              <div className={s.kpi}>
                <p className={s.kpiLabel}>분석 브랜드 수</p>
                <p className={s.kpiVal}>{brands.length}</p>
                <p className={s.kpiSub}>경쟁 현황</p>
              </div>
            </div>
          )}
        </div>
      )}

      {show('06') && mr.summary && (
        <div className={s.secBlock}>
          <SubHead num="06" title="AI 종합 분석" />
          <div className={s.infoBox}>
            <p className={s.infoTitle}>종합 판단</p>
            <p className={s.infoText}>{toStr(mr.summary)}</p>
          </div>
          <div className={s.kpiRow} style={{ marginTop: 12 }}>
            {[
              { label: '트렌드 점수', val: mr.trend_score ?? '-', sub: '현재' },
              { label: '리뷰 언급', val: mr.review_mention_count?.toLocaleString() ?? '-', sub: '건수' },
              { label: '성장률', val: mr.growth_rate != null ? `${mr.growth_rate >= 0 ? '+' : ''}${mr.growth_rate}%` : '-', sub: '' },
              { label: '위험도', val: mr.risk ?? '-', sub: '' },
            ].map(({ label, val, sub }) => (
              <div key={label} className={s.kpi}>
                <p className={s.kpiLabel}>{label}</p>
                <p className={s.kpiVal}>{val}</p>
                <p className={s.kpiSub}>{sub}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   PRICE SECTIONS
══════════════════════════════════════════ */
function PriceSection({ data, sections, category }) {
  if (!data) return null;
  const show = (n) => sections.includes(n);

  const sum       = data.summary ?? data;
  const avgPrice  = sum?.avg_price    ?? data.avg_price;
  const minPrice  = sum?.min_price    ?? data.min_price;
  const medPrice  = sum?.median_price ?? data.median_price;
  const totalProd = sum?.total_products ?? data.total_products;
  const pi        = data.price_insight;
  const signal    = pi?.signal ?? '-';
  const SIGNAL_COLOR = { '매입 적기': '#10b981', '관망 권장': '#f59e0b', '적정가': '#6366f1' };
  const sigColor  = SIGNAL_COLOR[signal] ?? '#6366f1';
  const dist      = data.distribution ?? data.price_distribution ?? [];
  const brands    = data.brands ?? [];
  const priceHistory = data.price_history ?? [];

  return (
    <div className={s.pageBlock}>
      <div className={s.pageBlockHeader}>
        <div className={s.pageIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="1" x2="12" y2="23" />
            <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        </div>
        <span className={s.pageBlockTitle}>가격 분석</span>
        <span className={s.pageBlockSub}>{category}</span>
      </div>

      {show('01') && (
        <div className={s.secBlock}>
          <SubHead num="01" title="핵심 가격 지표" />
          <div className={s.kpiRow}>
            {[
              { label: '시장 평균가', val: fmtWon(avgPrice), sub: '전체 평균' },
              { label: '최저가',      val: fmtWon(minPrice),  sub: '현재 최저', color: '#10b981' },
              { label: '중간가',      val: fmtWon(medPrice),  sub: '중앙값' },
              { label: '분석 제품',   val: totalProd?.toLocaleString() ?? '-', sub: '개' },
              { label: 'AI 신호',     val: signal,             sub: '매입 판단', color: sigColor },
            ].map(({ label, val, sub, color }) => (
              <div key={label} className={s.kpi}>
                <p className={s.kpiLabel}>{label}</p>
                <p className={s.kpiVal} style={color ? { color } : {}}>{val}</p>
                <p className={s.kpiSub}>{sub}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {show('02') && brands.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="02" title="브랜드별 가격 경쟁력 분석" />
          <div className={s.table}>
            <table>
              <thead><tr><th>브랜드</th><th>평균가</th><th>최저가</th><th>최고가</th><th>제품 수</th></tr></thead>
              <tbody>
                {brands.slice(0, 8).map((b, i) => (
                  <tr key={i}>
                    <td>{b.brand}</td>
                    <td>{fmtWon(b.avg_price)}</td>
                    <td>{fmtWon(b.min_price)}</td>
                    <td>{fmtWon(b.max_price)}</td>
                    <td>{b.count?.toLocaleString() ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {show('03') && dist.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="03" title="가격 수준별 브랜드 비중" />
          <div className={s.table}>
            <table>
              <thead><tr><th>가격대</th><th>제품 수</th><th>비율</th></tr></thead>
              <tbody>
                {dist.slice(0, 8).map((d, i) => (
                  <tr key={i}>
                    <td>{d.range ?? d.label ?? '-'}</td>
                    <td>{d.count?.toLocaleString() ?? '-'}</td>
                    <td>{d.percentage != null ? `${d.percentage}%` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {show('04') && priceHistory.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="04" title="가격 이력 · 추이 분석" />
          <div className={s.table}>
            <table>
              <thead><tr><th>날짜</th><th>평균가</th><th>최저가</th></tr></thead>
              <tbody>
                {[...priceHistory].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10).map((h, i) => (
                  <tr key={i}>
                    <td>{h.date}</td>
                    <td>{fmtWon(h.avg_price)}</td>
                    <td>{fmtWon(h.min_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {show('05') && pi && (
        <div className={s.secBlock}>
          <SubHead num="05" title="AI 가격 인사이트" />
          <div className={s.infoBox} style={{ '--box-accent': sigColor }}>
            <p className={s.infoTitle} style={{ color: sigColor }}>AI 신호: {signal}</p>
            {pi.reason && <p className={s.infoText}>{toStr(pi.reason)}</p>}
            {pi.suggestion && <p className={s.infoText} style={{ marginTop: 8 }}>{toStr(pi.suggestion)}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   REPORT SECTIONS
══════════════════════════════════════════ */
function ReportSection({ data, sections, category }) {
  if (!data) return null;
  const show = (n) => sections.includes(n);

  const report  = data.report ?? {};
  const metrics = data.metrics ?? {};
  const action  = toStr(report.action ?? '-');
  const ACTION_COLOR = { '즉시 매입': '#10b981', '전략적 매입': '#3b82f6', '관망': '#f59e0b', '매입 보류': '#ef4444' };
  const actionColor = ACTION_COLOR[action] ?? '#6366f1';

  const oppList    = toArr(report.opportunity);
  const riskList   = toArr(report.risk_summary);
  const needsList  = toArr(report.consumer_needs);
  const basisList  = toArr(report.action_basis);
  const kwList     = toArr(report.key_keywords);
  const salesList  = toArr(report.sales_strategy);
  const serviceList= toArr(report.service_strategy);
  const effectList = toArr(report.expected_effects);
  const summaryLines = toArr(report.summary_lines);

  return (
    <div className={s.pageBlock}>
      <div className={s.pageBlockHeader}>
        <div className={s.pageIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </div>
        <span className={s.pageBlockTitle}>AI 전략 리포트</span>
        <span className={s.pageBlockSub}>{category}</span>
      </div>

      {show('01') && (
        <div className={s.secBlock}>
          <SubHead num="01" title="AI 최종 권고 및 판단 근거" />
          <div className={s.kpiRow}>
            {[
              { label: '최종 권고',   val: action,                   sub: 'AI 판단', color: actionColor },
              { label: '검색 관심도', val: metrics.trend_score ?? '-', sub: '현재 지수' },
              { label: '시장 성장률', val: metrics.growth_rate != null ? `${metrics.growth_rate >= 0 ? '+' : ''}${metrics.growth_rate}%` : '-', sub: '전기 대비', color: (metrics.growth_rate ?? 0) >= 0 ? '#10b981' : '#ef4444' },
              { label: '추천 시기',   val: toStr(report.timing ?? '-'),           sub: '매입 타이밍' },
              { label: '재고 조정',   val: toStr(report.inventory_advice ?? '-'), sub: '권장 수준' },
            ].map(({ label, val, sub, color }) => (
              <div key={label} className={s.kpi}>
                <p className={s.kpiLabel}>{label}</p>
                <p className={s.kpiVal} style={color ? { color } : {}}>{val}</p>
                <p className={s.kpiSub}>{sub}</p>
              </div>
            ))}
          </div>
          {report.action_reason && (
            <div className={s.infoBox} style={{ '--box-accent': actionColor }}>
              <p className={s.infoTitle}>판단 근거</p>
              <p className={s.infoText}>{toStr(report.action_reason)}</p>
            </div>
          )}
          {basisList.length > 0 && (
            <ul className={s.infoList}>{basisList.map((b, i) => <li key={i}>{b}</li>)}</ul>
          )}
          {kwList.length > 0 && (
            <div className={s.tagRow} style={{ marginTop: 10 }}>
              {kwList.map((kw, i) => <span key={i} className={s.tag}>{kw}</span>)}
            </div>
          )}
        </div>
      )}

      {show('02') && (needsList.length > 0 || report.product_brief) && (
        <div className={s.secBlock}>
          <SubHead num="02" title="소비자 니즈 및 상품 기획 제안" />
          {report.product_brief && report.product_brief !== '-' && (
            <div className={s.infoBox}>
              <p className={s.infoTitle}>상품 기획 제안</p>
              <p className={s.infoText}>{toStr(report.product_brief)}</p>
            </div>
          )}
          {needsList.length > 0 && (
            <div className={s.table}>
              <p className={s.tableTitle}>소비자 니즈</p>
              <ul className={s.infoList}>{needsList.map((n, i) => <li key={i}>{n}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      {show('03') && (
        <div className={s.secBlock}>
          <SubHead num="03" title="시장 경쟁 현황" />
          <div className={s.kpiRow}>
            <div className={s.kpi}>
              <p className={s.kpiLabel}>시장 위험도</p>
              <p className={s.kpiVal}>{toStr(metrics.risk ?? '-')}</p>
              <p className={s.kpiSub}>종합 평가</p>
            </div>
            <div className={s.kpi}>
              <p className={s.kpiLabel}>대표 브랜드</p>
              <p className={s.kpiVal}>{toStr(report.brand_focus ?? '-')}</p>
              <p className={s.kpiSub}>시장 1위</p>
            </div>
            {report.price_range && report.price_range !== '-' && (
              <div className={s.kpi}>
                <p className={s.kpiLabel}>주요 가격대</p>
                <p className={s.kpiVal}>{toStr(report.price_range)}</p>
                <p className={s.kpiSub}>경쟁 구간</p>
              </div>
            )}
          </div>
        </div>
      )}

      {show('04') && (salesList.length > 0 || serviceList.length > 0) && (
        <div className={s.secBlock}>
          <SubHead num="04" title="매입 · 가격 전략" />
          <div className={s.twoCol}>
            {salesList.length > 0 && (
              <div className={s.infoBox}>
                <p className={s.infoTitle}>영업 전략</p>
                <ul className={s.infoList}>{salesList.map((v, i) => <li key={i}>{v}</li>)}</ul>
              </div>
            )}
            {serviceList.length > 0 && (
              <div className={s.infoBox}>
                <p className={s.infoTitle}>서비스 전략</p>
                <ul className={s.infoList}>{serviceList.map((v, i) => <li key={i}>{v}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}

      {show('05') && (oppList.length > 0 || riskList.length > 0) && (
        <div className={s.secBlock}>
          <SubHead num="05" title="기회 · 위험 요인 분석" />
          <div className={s.twoCol}>
            {oppList.length > 0 && (
              <div className={s.infoBox}>
                <p className={s.infoTitle}>시장 기회</p>
                <ul className={s.infoList}>{oppList.map((o, i) => <li key={i}>{o}</li>)}</ul>
              </div>
            )}
            {riskList.length > 0 && (
              <div className={s.infoBox} style={{ '--box-accent': '#ef4444' }}>
                <p className={s.infoTitle}>리스크 요인</p>
                <ul className={s.infoList}>{riskList.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}

      {show('06') && summaryLines.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="06" title="AI 종합 판단" />
          <div className={s.infoBox}>
            <ul className={s.infoList}>{summaryLines.map((l, i) => <li key={i}>{l}</li>)}</ul>
          </div>
        </div>
      )}

      {show('07') && report.product_strategy && toArr(report.product_strategy).length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="07" title="실행 전략" />
          <ul className={s.infoList}>{toArr(report.product_strategy).map((v, i) => <li key={i}>{v}</li>)}</ul>
        </div>
      )}

      {show('08') && (effectList.length > 0 || report.projection_summary) && (
        <div className={s.secBlock}>
          <SubHead num="08" title="예상 효과" />
          {report.expected_sales_growth && report.expected_sales_growth !== '-' && (
            <div className={s.kpiRow}>
              <div className={s.kpi}>
                <p className={s.kpiLabel}>예상 매출 성장</p>
                <p className={s.kpiVal} style={{ color: '#10b981' }}>{toStr(report.expected_sales_growth)}</p>
                <p className={s.kpiSub}>전망</p>
              </div>
            </div>
          )}
          {effectList.length > 0 && (
            <ul className={s.infoList}>{effectList.map((e, i) => <li key={i}>{e}</li>)}</ul>
          )}
          {report.projection_summary && report.projection_summary !== '-' && (
            <div className={s.infoBox} style={{ marginTop: 10 }}>
              <p className={s.infoText}>{toStr(report.projection_summary)}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   FORECAST SECTIONS
══════════════════════════════════════════ */
function ForecastSection({ data, sections, category }) {
  if (!data) return null;
  const show = (n) => sections.includes(n);

  const history  = data.history  ?? [];
  const forecast = data.forecast ?? [];
  const timing   = data.timing_signal ?? {};
  const rag      = data.rag_insight;

  return (
    <div className={s.pageBlock}>
      <div className={s.pageBlockHeader}>
        <div className={s.pageIcon}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 17 7 11 11 14 15 8 21 14" />
            <polyline points="17 8 21 8 21 12" />
          </svg>
        </div>
        <span className={s.pageBlockTitle}>미래 예측</span>
        <span className={s.pageBlockSub}>{category}</span>
      </div>

      {show('01') && (
        <div className={s.secBlock}>
          <SubHead num="01" title="관심도 추세 · 예측 차트" />
          <div className={s.kpiRow}>
            {[
              { label: '트렌드 방향', val: data.trend_direction ?? '-', sub: '' },
              { label: '피크 시점',   val: data.peak_period?.slice(0,7) ?? '-', sub: '최고 수요 예상' },
              { label: '신뢰도',      val: data.confidence != null ? `${data.confidence}%` : '-', sub: '예측 정확도' },
              { label: '기울기',      val: data.slope != null ? (data.slope >= 0 ? `+${data.slope}` : `${data.slope}`) : '-', sub: '추세 강도', color: (data.slope ?? 0) >= 0 ? '#10b981' : '#ef4444' },
            ].map(({ label, val, sub, color }) => (
              <div key={label} className={s.kpi}>
                <p className={s.kpiLabel}>{label}</p>
                <p className={s.kpiVal} style={color ? { color } : {}}>{val}</p>
                <p className={s.kpiSub}>{sub}</p>
              </div>
            ))}
          </div>
          {history.length > 0 && (
            <div className={s.table}>
              <p className={s.tableTitle}>최근 실적 추이</p>
              <table>
                <thead><tr><th>기간</th><th>관심도 지수</th></tr></thead>
                <tbody>
                  {history.slice(-6).map((h, i) => (
                    <tr key={i}><td>{h.period}</td><td>{h.ratio}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {show('02') && forecast.length > 0 && (
        <div className={s.secBlock}>
          <SubHead num="02" title="핵심 예측 지표" />
          <div className={s.table}>
            <p className={s.tableTitle}>예측값 ({forecast.length}개월)</p>
            <table>
              <thead><tr><th>기간</th><th>예측 지수</th><th>하한</th><th>상한</th></tr></thead>
              <tbody>
                {forecast.slice(0, 8).map((f, i) => (
                  <tr key={i}>
                    <td>{f.period ?? f.date}</td>
                    <td>{typeof f.predicted === 'number' ? f.predicted.toFixed(1) : f.predicted ?? '-'}</td>
                    <td>{f.lower != null ? f.lower.toFixed(1) : '-'}</td>
                    <td>{f.upper != null ? f.upper.toFixed(1) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {show('03') && data.recommendation && (
        <div className={s.secBlock}>
          <SubHead num="03" title="월별 수요 영향도 · 계절 분석" />
          <div className={s.infoBox}>
            <p className={s.infoTitle}>수요 패턴 분석</p>
            <p className={s.infoText}>{toStr(data.recommendation)}</p>
          </div>
          {rag && (
            <div className={s.infoBox} style={{ marginTop: 8 }}>
              <p className={s.infoTitle}>RAG 기반 인사이트</p>
              <p className={s.infoText}>{toStr(rag)}</p>
            </div>
          )}
        </div>
      )}

      {show('04') && timing.message && (
        <div className={s.secBlock}>
          <SubHead num="04" title="3개월 전망 시나리오 · 기회 및 전략" />
          <div className={s.infoBox} style={{ '--box-accent': timing.type === 'buy' ? '#10b981' : timing.type === 'caution' ? '#f59e0b' : '#6366f1' }}>
            <p className={s.infoTitle}>{toStr(timing.label ?? '타이밍 권고')}</p>
            <p className={s.infoText}>{toStr(timing.message)}</p>
          </div>
          <div className={s.kpiRow} style={{ marginTop: 12 }}>
            {timing.peak_period && (
              <div className={s.kpi}>
                <p className={s.kpiLabel}>피크 시점</p>
                <p className={s.kpiVal}>{timing.peak_period.slice(0,7)}</p>
                <p className={s.kpiSub}>최고 수요</p>
              </div>
            )}
            {timing.days_to_peak != null && (
              <div className={s.kpi}>
                <p className={s.kpiLabel}>D-DAY</p>
                <p className={s.kpiVal}>{timing.days_to_peak}일</p>
                <p className={s.kpiSub}>피크까지</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   MAIN
══════════════════════════════════════════ */
const PAGE_ORDER = ['dashboard', 'price', 'report', 'forecast'];

export default function B2BPrint() {
  const [searchParams] = useSearchParams();
  const navigate       = useNavigate();
  const { user, token } = useAuth();

  const sectionsParam = searchParams.get('sections') ?? '';
  const category      = searchParams.get('category') ?? '에어컨';
  const period        = searchParams.get('period')   ?? '3m';

  // sections = { dashboard: ['01','02'], price: ['01'], ... }
  const pageSections = {};
  sectionsParam.split('|').forEach(part => {
    const idx = part.indexOf(':');
    if (idx === -1) return;
    const pageId = part.slice(0, idx);
    const nums   = part.slice(idx + 1).split(',').filter(Boolean);
    if (pageId && nums.length > 0) pageSections[pageId] = nums;
  });

  const activePages = PAGE_ORDER.filter(p => (pageSections[p]?.length ?? 0) > 0);

  const [dataMap, setDataMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const didPrint = useRef(false);

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin';

  /* body overflow를 auto로 바꿔 print 시 전체 콘텐츠가 출력되게 함 */
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'auto';
    return () => { document.body.style.overflow = prev; };
  }, []);

  useEffect(() => {
    if (!isB2BActive || !token || activePages.length === 0) { setLoading(false); return; }
    const headers = { Authorization: `Bearer ${token}` };
    const enc = encodeURIComponent(category);

    const fetchers = {};
    if (activePages.includes('dashboard')) fetchers.dashboard = fetch(`${API_BASE}/api/b2b/dashboard?category=${enc}&period=${period}`, { headers }).then(r => r.json());
    if (activePages.includes('price'))     fetchers.price     = fetch(`${API_BASE}/api/b2b/price?category=${enc}`,                      { headers }).then(r => r.json());
    if (activePages.includes('report'))    fetchers.report    = fetch(`${API_BASE}/api/b2b/ai-report?category=${enc}&period=${period}`,  { headers }).then(r => r.json());
    if (activePages.includes('forecast'))  fetchers.forecast  = fetch(`${API_BASE}/api/b2b/demand-forecast?category=${enc}`,            { headers }).then(r => r.json());

    const keys = Object.keys(fetchers);
    Promise.all(keys.map(k => fetchers[k]))
      .then(results => {
        const map = {};
        keys.forEach((k, i) => { map[k] = results[i]; });
        setDataMap(map);
        setLoading(false);
      })
      .catch(() => { setError('데이터를 불러오지 못했습니다'); setLoading(false); });
  }, [isB2BActive, token, category, period, sectionsParam]);

  useEffect(() => {
    if (!loading && !error && !didPrint.current && Object.keys(dataMap).length > 0) {
      didPrint.current = true;
      setTimeout(() => window.print(), 600);
    }
  }, [loading, error, dataMap]);

  const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });

  const totalSecs = activePages.reduce((acc, p) => acc + (pageSections[p]?.length ?? 0), 0);

  const pageLabels = { dashboard: '시장 분석', price: '가격 분석', report: 'AI 전략 리포트', forecast: '미래 예측' };
  const includedPageNames = activePages.map(p => pageLabels[p]).join(' · ');

  if (!isB2BActive) {
    return (
      <div className={s.center}>
        <p>B2B 계정으로 로그인이 필요합니다</p>
        <button onClick={() => navigate('/login')}>로그인</button>
      </div>
    );
  }

  return (
    <div className={s.page}>
      {/* 툴바 (출력 시 숨김) */}
      <div className={s.toolbar}>
        <button className={s.backBtn} onClick={() => navigate(-1)}>← 돌아가기</button>
        <div className={s.toolbarInfo}>
          <span className={s.catTag}>{category}</span>
          <span className={s.pagesTags}>
            {activePages.map(p => (
              <span key={p} className={s.pagesTag}>
                {pageLabels[p]} ({pageSections[p]?.length ?? 0}섹션)
              </span>
            ))}
          </span>
          <span className={s.totalTag}>총 {totalSecs}개 섹션</span>
        </div>
        <button className={s.printBtn} onClick={() => window.print()}>출력 / PDF 저장</button>
      </div>

      {/* 문서 */}
      <div className={s.doc}>
        <div className={s.docHeader}>
          <div>
            <p className={s.docLabel}>B2B 인텔리전스 리포트</p>
            <h1 className={s.docTitle}>{category} 종합 분석</h1>
            <p className={s.docMeta}>{today} 기준 &nbsp;·&nbsp; {includedPageNames} &nbsp;·&nbsp; 가전무쌍</p>
          </div>
          <div className={s.docLogo}>가전무쌍</div>
        </div>

        {loading && (
          <div className={s.center}>
            <div className={s.spinner} />
            <p>데이터 로딩 중... 잠시 후 출력 대화상자가 열립니다</p>
          </div>
        )}
        {error && <div className={s.errorBox}>{error}</div>}

        {!loading && !error && (
          <>
            {activePages.includes('dashboard') && (
              <DashboardSection data={dataMap.dashboard} sections={pageSections.dashboard ?? []} category={category} />
            )}
            {activePages.includes('price') && (
              <PriceSection data={dataMap.price} sections={pageSections.price ?? []} category={category} />
            )}
            {activePages.includes('report') && (
              <ReportSection data={dataMap.report} sections={pageSections.report ?? []} category={category} />
            )}
            {activePages.includes('forecast') && (
              <ForecastSection data={dataMap.forecast} sections={pageSections.forecast ?? []} category={category} />
            )}
          </>
        )}

        <div className={s.docFooter}>
          <span>본 리포트는 네이버 DataLab · 네이버 쇼핑 · Danawa · Groq LLM 데이터를 기반으로 생성되었습니다.</span>
          <span>{today}</span>
        </div>
      </div>
    </div>
  );
}
