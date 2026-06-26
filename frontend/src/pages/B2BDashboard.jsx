import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import B2BSidebar from '../components/common/B2BSidebar'
import B2BPrintModal from '../components/common/B2BPrintModal'
import { useAuth } from '../context/AuthContext'
import s from '../styles/B2BDashboard.module.css'
import { API_BASE } from '../config'

const CATEGORIES = ['에어컨', '냉장고', '세탁기', '건조기', '공기청정기', '로봇청소기', '식기세척기', 'TV']
const PERIODS = [
  { label: '1개월', value: '1m' },
  { label: '3개월', value: '3m' },
  { label: '6개월', value: '6m' },
  { label: '1년',   value: '1y' },
]
const PERIOD_LABEL = { '1m': '최근 1개월', '3m': '최근 3개월', '6m': '최근 6개월', '1y': '최근 1년' }
const BRAND_COLORS = ['#6366f1', '#a855f7', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function SectionHead({ num, title }) {
  return (
    <div className={s.sectionHead}>
      <span className={s.sectionNum}>{num}</span>
      <span className={s.sectionTitle}>{title}</span>
      <span className={s.sectionLine} />
    </div>
  )
}

/* ── Trend chart (bold black) ── */
function TrendChart({ data }) {
  if (!data || data.length < 2) return <div className={s.noData}>데이터 없음</div>
  const W = 560, H = 180, PAD = { t: 10, b: 30, l: 42, r: 28 }
  const ratios = data.map(d => d.ratio)
  const min = Math.min(...ratios), max = Math.max(...ratios)
  const range = max - min || 1
  const px = i => PAD.l + (i / (data.length - 1)) * (W - PAD.l - PAD.r)
  const py = v => PAD.t + (1 - (v - min) / range) * (H - PAD.t - PAD.b)
  const points = data.map((d, i) => ({ x: px(i), y: py(d.ratio) }))
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')

  const labelIndices = [0, 0.25, 0.5, 0.75, 1].map(t => Math.round(t * (data.length - 1)))
  const xLabels = labelIndices
    .filter((idx, i, arr) => i === 0 || px(idx) - px(arr[i - 1]) > 50)
    .map(idx => ({ label: data[idx]?.period?.slice(5, 10) ?? '', x: px(idx) }))
  const yVals = [max, (max + min) / 2, min].map(v => ({ v: Math.round(v), y: py(v) }))

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map(t => (
        <line key={t} x1={PAD.l} x2={W - PAD.r}
          y1={PAD.t + t * (H - PAD.t - PAD.b)} y2={PAD.t + t * (H - PAD.t - PAD.b)}
          stroke="var(--b2b-line)" strokeWidth="1" />
      ))}
      {/* Line */}
      <path d={pathD} fill="none" stroke="var(--b2b-text)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {/* First & last dot only */}
      <circle cx={points[0].x} cy={points[0].y} r="4" fill="var(--b2b-text)" />
      <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="4" fill="var(--b2b-text)" />
      {/* Y axis unit label — 차트 내부 상단 좌측 */}
      <text x={PAD.l + 4} y={PAD.t + 9} textAnchor="start" fontSize="8" fill="var(--b2b-muted)" opacity="0.7">관심도 지수</text>
      {/* Y labels */}
      {yVals.map(({ v, y }) => (
        <text key={v} x={PAD.l - 5} y={y + 4} textAnchor="end" fontSize="9" fill="var(--b2b-muted)">{v}</text>
      ))}
      {/* X labels */}
      {xLabels.map((xl, i) => (
        <text key={i} x={xl.x} y={H - 6}
          textAnchor={i === xLabels.length - 1 ? 'end' : 'middle'}
          fontSize="9" fill="var(--b2b-muted)">{xl.label}</text>
      ))}
    </svg>
  )
}

/* ── Brand donut ── */
function BrandDonut({ brands }) {
  if (!brands || brands.length === 0) return <div className={s.noData}>데이터 없음</div>
  const R = 42, cx = 52, cy = 52, stroke = 16
  let cum = 0
  const slices = brands.slice(0, 6).map((b, i) => {
    const start = cum; cum += b.pct
    return { ...b, start, color: BRAND_COLORS[i % BRAND_COLORS.length] }
  })
  function arc(sp, pct) {
    if (pct >= 100) pct = 99.99
    const a1 = (sp / 100) * 2 * Math.PI - Math.PI / 2
    const a2 = ((sp + pct) / 100) * 2 * Math.PI - Math.PI / 2
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1)
    const x2 = cx + R * Math.cos(a2), y2 = cy + R * Math.sin(a2)
    return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 ${pct > 50 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
  }
  return (
    <div className={s.donutWrap}>
      <svg width={104} height={104} style={{ flexShrink: 0 }}>
        {slices.map((sl, i) => (
          <path key={i} d={arc(sl.start, sl.pct)}
            fill="none" stroke={sl.color} strokeWidth={stroke} strokeLinecap="butt" />
        ))}
      </svg>
      <div className={s.donutLegend}>
        {slices.map((sl, i) => (
          <div key={i} className={s.donutLegendRow}>
            <span className={s.donutDot} style={{ background: sl.color }} />
            <span>{sl.brand}</span>
            <span className={s.donutPct}>{sl.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Age bars ── */
function AgeBars({ age }) {
  if (!age || age.length === 0) return <div className={s.noData}>데이터 없음</div>
  const maxPct = Math.max(...age.map(a => a.pct))
  return (
    <div className={s.ageBarList}>
      {age.map((a, i) => (
        <div key={i} className={s.ageBarRow}>
          <span className={s.ageBarLabel}>{a.label}</span>
          <div className={s.ageBarTrack}>
            <div className={s.ageBarFill} style={{ width: `${(a.pct / maxPct) * 100}%` }} />
          </div>
          <span className={s.ageBarPct}>{a.pct}%</span>
        </div>
      ))}
    </div>
  )
}

/* ── Source donut (mini) — 데이터 출처 비율 ── */
function SourceDonut({ news, blog, cafe = 0, youtube = 0, shopping = 0 }) {
  const total = (news + blog + cafe + youtube + shopping) || 1
  const data = [
    { label: '뉴스',       count: news,     color: '#3b82f6' },
    { label: '블로그',     count: blog,     color: '#10b981' },
    { label: '카페',       count: cafe,     color: '#f59e0b' },
    { label: 'YouTube',   count: youtube,  color: '#ef4444' },
    { label: '네이버쇼핑', count: shopping, color: '#6366f1' },
  ].filter(d => d.count > 0)
  if (data.length === 0) data.push({ label: '수집 중', count: 1, color: '#8888a8' })
  const R = 26, cx = 30, cy = 30, sw = 10
  let cum = 0
  const slices = data.map(d => {
    const pct = d.count / total * 100
    const start = cum; cum += pct
    return { ...d, pct, start }
  })
  function arc(sp, pct) {
    if (pct >= 100) pct = 99.99
    const a1 = (sp / 100) * 2 * Math.PI - Math.PI / 2
    const a2 = ((sp + pct) / 100) * 2 * Math.PI - Math.PI / 2
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1)
    const x2 = cx + R * Math.cos(a2), y2 = cy + R * Math.sin(a2)
    return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 ${pct > 50 ? 1 : 0} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`
  }
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 6 }}>
      <svg width={60} height={60} style={{ flexShrink: 0 }}>
        {slices.map((sl, i) => (
          <path key={i} d={arc(sl.start, sl.pct)}
            fill="none" stroke={sl.color} strokeWidth={sw} strokeLinecap="butt" />
        ))}
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {slices.map((sl, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: sl.color, flexShrink: 0 }} />
            <span style={{ color: 'var(--b2b-text3)' }}>{sl.label}</span>
            <span style={{ marginLeft: 4, fontWeight: 700, color: sl.color }}>{Math.round(sl.pct)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Horizontal bar chart — 지역별/설치형태/구매목적/연관가전 ── */
function HBar({ data, color }) {
  if (!data || data.length === 0) return <div style={{ fontSize: 12, color: 'var(--b2b-muted)', textAlign: 'center', padding: '16px 0' }}>데이터 없음</div>
  const max = Math.max(...data.map(d => d.pct), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {data.map((d, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 68, fontSize: 11.5, fontWeight: 600, color: 'var(--b2b-text3)', flexShrink: 0 }}>{d.label}</span>
          <div style={{ flex: 1, height: 8, background: 'var(--b2b-surface)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: `${(d.pct / max) * 100}%`, height: '100%', background: color, borderRadius: 999, transition: 'width 0.6s ease' }} />
          </div>
          <span style={{ width: 34, fontSize: 12, fontWeight: 700, color, textAlign: 'right', flexShrink: 0 }}>{d.pct}%</span>
        </div>
      ))}
    </div>
  )
}

/* ── Complaint source modal ── */
function ComplaintSourceModal({ tag, product, sources, onClose }) {
  const filtered = sources.filter(a => a.title?.includes(tag) || a.description?.includes(tag))
  const shown = filtered.length > 0 ? filtered : sources
  return (
    <div className={s.modalBackdrop} onClick={onClose}>
      <div className={s.modalBox} onClick={e => e.stopPropagation()}>
        <div className={s.modalHeader}>
          <div>
            <span className={s.modalTag}>{tag}</span>
            <p className={s.modalProduct}>{product}</p>
          </div>
          <button className={s.modalClose} onClick={onClose}>✕</button>
        </div>
        {shown.length === 0
          ? <p className={s.modalEmpty}>관련 기사를 찾을 수 없습니다.</p>
          : shown.map((a, i) => (
            <a key={i} href={a.link} target="_blank" rel="noreferrer" className={s.modalArticle}>
              <div className={s.modalArticleMeta}>
                <span className={`${s.modalSourceBadge} ${a.source === '블로그' ? s.modalSourceBlog : s.modalSourceNews}`}>
                  {a.source ?? '뉴스'}
                </span>
                <span className={s.modalArticleDate}>{a.pubDate}</span>
              </div>
              <p className={s.modalArticleTitle}>{a.title}</p>
              <p className={s.modalArticleDesc}>{a.description}</p>
            </a>
          ))
        }
      </div>
    </div>
  )
}

/* ── Keyword section (관심 / 불만) ── */
function KeywordSection({ title, items, isComplaint, token, category }) {
  const [selected, setSelected] = useState(0)
  const [modal, setModal] = useState(null)
  const [reviewData, setReviewData] = useState(null)
  const [reviewLoading, setReviewLoading] = useState(false)

  useEffect(() => { setSelected(0); setReviewData(null) }, [items])

  useEffect(() => {
    if (isComplaint || !token || !category) return
    const tags = isComplaint
      ? []
      : items.slice(0, 10).map(w => (typeof w === 'string' ? w : w.word))
    const word = tags[selected]
    if (!word) return
    setReviewData(null)
    setReviewLoading(true)
    fetch(`${API_BASE}/api/b2b/keyword-review?category=${encodeURIComponent(category)}&keyword=${encodeURIComponent(word)}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setReviewData(d); setReviewLoading(false) })
      .catch(() => setReviewLoading(false))
  }, [selected, token, category, isComplaint, items])

  if (!items || items.length === 0) return null

  const isComp = isComplaint

  // ── complaints: 동일 태그 묶기 — 소스·제품·근거 병합 ──
  const tagItems = isComp
    ? (() => {
        const map = new Map()
        items.forEach(c => {
          ;(c.complaint ?? []).forEach(t => {
            if (!map.has(t)) map.set(t, { tag: t, products: [], brands: [], sources: [], evidence: '' })
            const e = map.get(t)
            if (c.product && !e.products.includes(c.product)) e.products.push(c.product)
            if (c.brand  && !e.brands.includes(c.brand))     e.brands.push(c.brand)
            const existLinks = new Set(e.sources.map(s => s.link))
            ;(c.sources ?? []).forEach(s => { if (!existLinks.has(s.link)) { e.sources.push(s); existLinks.add(s.link) } })
            if (!e.evidence) e.evidence = (c.evidence ?? {})[t] ?? ''
          })
        })
        return [...map.values()].slice(0, 10)
      })()
    : []

  // ── keywords: string 또는 {word, count, examples} 객체 ──
  const kwItems = isComp
    ? []
    : items.slice(0, 10).map((w, i) => ({
        word:     typeof w === 'string' ? w : (w.word ?? String(w)),
        count:    typeof w === 'object' ? (w.count ?? 0) : 0,
        examples: typeof w === 'object' ? (w.examples ?? []) : [],
        rank:     i + 1,
      }))

  const tags = isComp
    ? tagItems.map(ti => ti.tag)
    : kwItems.map(k => k.word)

  // selected가 범위를 벗어나면 0으로 리셋
  const sel = selected < tags.length ? selected : 0

  // ── complaints: 선택된 태그 ──
  const selTagItem  = isComp ? (tagItems[sel] ?? null) : null
  const selTag      = tags[sel] ?? ''
  const selProducts = selTagItem?.products ?? []
  const selBrands   = selTagItem?.brands ?? []
  const selEvidence = selTagItem?.evidence ?? ''

  const relatedSources = isComp
    ? (() => {
        const srcs = selTagItem?.sources ?? []
        const sorted = [...srcs].sort((a, b) => {
          const da = a.pubDate ? new Date(a.pubDate).getTime() : 0
          const db = b.pubDate ? new Date(b.pubDate).getTime() : 0
          return db - da
        })
        const exact = sorted.filter(src => (src.title + ' ' + (src.description ?? '')).includes(selTag))
        const rest  = sorted.filter(src => !(src.title + ' ' + (src.description ?? '')).includes(selTag))
        return [...exact, ...rest].slice(0, 3)
      })()
    : []

  const relatedTags = isComp
    ? tags.filter(t => t !== selTag).slice(0, 4)
    : tags.filter((_, i) => i !== sel).slice(0, 4)

  // ── keywords: 분류 ──
  const selKw = kwItems[sel] ?? null
  const KW_BRANDS  = new Set(['LG', '삼성', '삼성전자', '위니아', '캐리어', '대우', '코웨이', '쿠쿠', '다이슨', '샤오미', '파나소닉', '하이얼', '미디어', '린나이', '청호'])
  const KW_INSTALL = ['벽걸이', '스탠드', '창문형', '2in1', '드럼', '통돌이', '빌트인', '일반형', '양문형', '4도어', '이동형', '천장형']
  const KW_FUNC    = ['인버터', '청정', '절전', '스마트', '제균', '항균', '에너지', '냉난방', '제습', '히트펌프', '쾌속', '냉방', '난방', 'AI', '저소음', '급속']
  const classifyKw = w => {
    if (!w) return '기타'
    if (KW_BRANDS.has(w)) return '브랜드'
    if (KW_INSTALL.some(k => w.includes(k))) return '설치 형태'
    if (KW_FUNC.some(k => w.includes(k))) return '기능 키워드'
    return '기타'
  }
  const kwType = classifyKw(selKw?.word)

  // ── 관심 키워드 그룹 ──
  const GROUP_ORDER = ['기능 키워드', '설치 형태', '브랜드', '기타']
  const GROUP_COLOR = { '기능 키워드': '#f59e0b', '설치 형태': '#10b981', '브랜드': '#6366f1', '기타': '#94a3b8' }
  const kwGroups = !isComp ? GROUP_ORDER.reduce((acc, g) => {
    acc[g] = kwItems
      .map((kw, i) => ({ ...kw, origIdx: i }))
      .filter(kw => classifyKw(kw.word) === g)
    return acc
  }, {}) : {}

  // ── 불만 키워드 연관도: 선택 태그와 같은 기사에 함께 등장한 비율(co-occurrence) ──
  const selSrcLinks = new Set((selTagItem?.sources ?? []).map(src => src.link))
  const relatedTagsScored = isComp
    ? tags.filter(t => t !== selTag).slice(0, 5).map(t => {
        const item = tagItems.find(ti => ti.tag === t)
        const coCount = (item?.sources ?? []).filter(src => selSrcLinks.has(src.link)).length
        const pct = selSrcLinks.size > 0 ? Math.round(coCount / selSrcLinks.size * 100) : 0
        return { tag: t, pct }
      }).filter(({ pct }) => pct > 0).sort((a, b) => b.pct - a.pct)
    : []

  return (
    <div className={s.kwCard}>
      <div className={s.kwHeader}>
        <span className={s.kwTitle}>{title} TOP{tags.length}</span>
        <span className={s.kwNote}>키워드 클릭 시 상세 보기</span>
      </div>

      {/* ── 관심 키워드: 그룹별 렌더 ── */}
      {!isComp && (
        <div className={s.kwGroupList}>
          {GROUP_ORDER.filter(g => kwGroups[g]?.length > 0).map(g => (
            <div key={g} className={s.kwGroupRow}>
              <span className={s.kwGroupLabel} style={{ color: GROUP_COLOR[g] }}>{g}</span>
              <div className={s.kwGroupTags}>
                {kwGroups[g].map(kw => (
                  <span
                    key={kw.origIdx}
                    className={`${s.tag} ${kw.origIdx === sel ? s.tagActive : ''}`}
                    style={kw.origIdx === sel ? { borderColor: GROUP_COLOR[g], color: GROUP_COLOR[g] } : {}}
                    onClick={() => setSelected(kw.origIdx)}
                  >
                    {kw.word}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── 불만 키워드: 기존 플랫 태그 ── */}
      {isComp && (
        <div className={s.tagRow}>
          {tags.map((t, i) => {
            const count = tagItems[i]?.products?.length ?? 0
            return (
              <span key={i}
                className={`${s.tag} ${i === sel ? s.tagComplaintActive : ''}`}
                onClick={() => setSelected(i)}>
                {t}
                {count > 1 && (
                  <span className={`${s.tagCountBadge} ${i === sel ? s.tagCountBadgeActive : ''}`}>
                    {count}
                  </span>
                )}
              </span>
            )
          })}
        </div>
      )}


      {/* ── 불만 키워드 상세 ── */}
      {isComp && tags[sel] && (
        <div className={s.kwComplaintDetail}>
          <div className={s.kwQuoteCol}>
            {selBrands.length > 0 && (
              <p style={{ fontSize: 11, color: 'var(--b2b-muted)', marginBottom: 8 }}>
                출처: <strong style={{ color: 'var(--b2b-text2)' }}>{selBrands.join(' · ')}</strong>
                {selProducts.length > 0 && (
                  <span> · {selProducts.length > 1 ? `${selProducts.length}개 제품` : selProducts[0]}</span>
                )}
              </p>
            )}
            {/* Groq가 추출한 핵심 근거 문장 */}
            {selEvidence && (
              <div className={s.kwEvidenceBox}>
                <span className={s.kwEvidenceLabel}>AI 근거</span>
                <p className={s.kwEvidenceText}>"{selEvidence}"</p>
              </div>
            )}
            <p className={s.kwSubTitle} style={{ marginTop: selEvidence ? 12 : 0 }}>최근 관련 콘텐츠 TOP3</p>
            {relatedSources.length > 0
              ? relatedSources.map((src, i) => (
                  <a
                    key={i}
                    href={src.link}
                    target="_blank"
                    rel="noreferrer"
                    className={s.kwSourceCard}
                  >
                    <div className={s.kwSourceMeta}>
                      <span className={`${s.kwSourceBadge} ${
                        src.source === 'YouTube' ? s.kwBadgeYt :
                        src.source === '카페'    ? s.kwBadgeCafe :
                        src.source === '뉴스'    ? s.kwBadgeNews :
                                                   s.kwBadgeBlog
                      }`}>{src.source}</span>
                      <span className={s.kwSourceDate}>{src.pubDate?.slice(0, 10)}</span>
                      {src.channel && <span className={s.kwSourceDate}>{src.channel}</span>}
                    </div>
                    <p className={s.kwSourceTitle}>{src.title}</p>
                    {src.description && (
                      <p className={s.kwSourceDesc}>{src.description.substring(0, 60)}...</p>
                    )}
                  </a>
                ))
              : <p style={{ fontSize: 12, color: 'var(--b2b-muted)' }}>관련 콘텐츠 없음</p>
            }
          </div>
          <div className={s.kwRightCol}>
            <div className={s.kwAssocBox}>
              <p className={s.kwSubTitle}>키워드 연관도</p>
              {relatedTagsScored.length > 0
                ? relatedTagsScored.map(({ tag: t, pct }) => (
                    <div key={t} className={s.kwRelatedRow}>
                      <span className={s.kwRelatedItem}>{t}</span>
                      <span className={s.kwRelatedPct}>{pct}%</span>
                    </div>
                  ))
                : <span style={{ fontSize: 12, color: 'var(--b2b-muted)' }}>-</span>
              }
            </div>
            <div>
              <p className={s.kwSubTitle}>출처 비율</p>
              <SourceDonut
                news={relatedSources.filter(s => s.source === '뉴스').length}
                blog={relatedSources.filter(s => s.source === '블로그').length}
                cafe={relatedSources.filter(s => s.source === '카페').length}
                youtube={relatedSources.filter(s => s.source === 'YouTube').length}
              />
            </div>
          </div>
        </div>
      )}

      {/* ── 관심 키워드 상세 ── */}
      {!isComp && selKw && (
        <div className={s.kwDetails}>
          <div>
            <p className={s.kwSubTitle}>함께 등장하는 키워드</p>
            {relatedTags.length > 0
              ? relatedTags.map((t, i) => (
                  <span key={i} className={s.kwRelatedItem}>{t}</span>
                ))
              : <span style={{ fontSize: 12, color: 'var(--b2b-muted)' }}>-</span>
            }
            {selKw?.count > 0 && (() => {
              const maxCount = Math.max(...kwItems.map(k => k.count), 1)
              const barPct = Math.round((selKw.count / maxCount) * 100)
              return (
                <>
                  <p className={s.kwSubTitle} style={{ marginTop: 14 }}>쇼핑 노출 빈도</p>
                  <div className={s.kwFreqBar}>
                    <div className={s.kwFreqFill} style={{ width: `${barPct}%` }} />
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--b2b-muted)', marginTop: 4 }}>
                    {selKw.count}개 제품 · 상위 {barPct}% 빈도
                  </p>
                  <p className={s.kwSubTitle} style={{ marginTop: 14 }}>리뷰 언급량</p>
                  {reviewLoading
                    ? <p style={{ fontSize: 11, color: 'var(--b2b-muted)' }}>불러오는 중...</p>
                    : reviewData
                      ? (
                        <>
                          <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--b2b-text)', marginTop: 4 }}>
                            {reviewData.total.toLocaleString()}건
                          </p>
                          <p style={{ fontSize: 11, color: 'var(--b2b-muted)', marginTop: 2 }}>
                            블로그 {reviewData.blog.toLocaleString()} · 카페 {reviewData.cafe.toLocaleString()}
                          </p>
                        </>
                      )
                    : null
                  }
                </>
              )
            })()}
          </div>
          <div>
            <p className={s.kwSubTitle}>키워드 유형</p>
            <span style={{
              display: 'inline-block', padding: '4px 14px', borderRadius: 999,
              fontSize: 12, fontWeight: 700,
              background: kwType === '브랜드'   ? 'rgba(99,102,241,0.1)' :
                          kwType === '설치 형태' ? 'rgba(16,185,129,0.1)' :
                          kwType === '기능 특성' ? 'rgba(245,158,11,0.1)' : 'rgba(0,0,0,0.06)',
              color: kwType === '브랜드'   ? '#6366f1' :
                     kwType === '설치 형태' ? '#10b981' :
                     kwType === '기능 특성' ? '#f59e0b' : 'var(--b2b-text2)',
            }}>{kwType}</span>
            {selKw.count > 0 && (
              <p style={{ fontSize: 11, color: 'var(--b2b-muted)', marginTop: 10, lineHeight: 1.6 }}>
                {selKw.count}개 제품에서 등장<br />
                <span style={{ color: 'var(--b2b-text3)' }}>네이버 쇼핑 기준</span>
              </p>
            )}
          </div>
        </div>
      )}

      {modal && (
        <ComplaintSourceModal
          tag={modal.tag}
          product={modal.product}
          sources={modal.sources}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}

export default function B2BDashboard() {
  const navigate = useNavigate()
  const { user, token } = useAuth()
  const [category, setCategory] = useState('에어컨')
  const [period, setPeriod] = useState('3m')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [trendCtx, setTrendCtx] = useState(null)
  const [envSignal, setEnvSignal] = useState(null)
  const [fetchedAt, setFetchedAt] = useState(null)
  const [printModal, setPrintModal] = useState(false)

  const isB2BActive = (user?.user_type === 'b2b' && user?.status === 'active') || user?.role === 'admin'
  const [refreshTick, setRefreshTick] = useState(0)

  const loadData = () => setRefreshTick(t => t + 1)

  useEffect(() => {
    if (!isB2BActive) return
    setLoading(true)
    setError(null)
    setData(null)
    setTrendCtx(null)
    setEnvSignal(null)
    fetch(`${API_BASE}/api/b2b/dashboard?category=${encodeURIComponent(category)}&period=${period}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setFetchedAt(new Date()); setLoading(false) })
      .catch(() => { setError('서버에 연결할 수 없습니다'); setLoading(false) })

    fetch(`${API_BASE}/api/b2b/trend-context?category=${encodeURIComponent(category)}&period=${period}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => setTrendCtx(d))
      .catch(() => {})

    fetch(`${API_BASE}/api/b2b/env-signal?category=${encodeURIComponent(category)}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => setEnvSignal(d))
      .catch(() => {})
  }, [category, period, isB2BActive, refreshTick])

  if (!isB2BActive) {
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
    )
  }

  const report = data?.market_report
  const trend = data?.trend ?? []
  const brands = data?.brands ?? []
  const age = data?.age_distribution ?? []
  const keywords = data?.keywords ?? []
  const complaints = data?.complaints ?? []
  const complaintSummary = data?.complaint_summary ?? []

  const topAge = age.length > 0 ? age.reduce((a, b) => a.pct > b.pct ? a : b) : null
  const growthPositive = (report?.growth_rate ?? 0) >= 0

  return (
    <div className={s.page} data-scroll-container>
      <Navbar />
      <div className={s.container}>

        <div className={s.layout}>
          <div className={s.main}>

        {loading && (
          <div className={s.loadingWrap}>
            <div className={s.spinner} />
            <p>"{category}" 시장 데이터 분석 중...</p>
          </div>
        )}
        {error && <div className={s.error}>{error}</div>}

        {!loading && data && (
          <>
            {/* ── 리포트 헤더 ── */}
            {(() => {
              const today = fetchedAt
                ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
                : new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
              const growth = report?.growth_rate ?? 0
              const growthColor = growth >= 0 ? '#10b981' : '#ef4444'
              return (
                <div className={s.reportHeader}>
                  <div className={s.reportHeaderTop}>
                    <div>
                      <p className={s.reportLabel}>B2B 시장 현황 분석 리포트</p>
                      <h1 className={s.reportTitle}>{category} 시장 동향 분석</h1>
                      <p className={s.reportMeta}>{today} 기준 · {PERIOD_LABEL[period]} · DataLab + Groq LLM + RAG</p>
                    </div>
                    <div className={s.reportStatusBadge} style={{ borderColor: `${growthColor}40`, background: `${growthColor}08` }}>
                      <span className={s.reportStatusIcon} style={{ color: growthColor }}>{growth >= 0 ? '↑' : '↓'}</span>
                      <span className={s.reportStatusText} style={{ color: growthColor }}>{growth >= 0 ? '성장세' : '하락세'}</span>
                    </div>
                  </div>
                  <div className={s.reportKpiRow}>
                    {[
                      { label: '검색 관심도',  val: report?.trend_score ?? '-',         sub: '현재 지수 (0~100)' },
                      { label: '증감률',        val: growth != null ? `${growth >= 0 ? '+' : ''}${growth}%` : '-', sub: '전기 대비', color: growthColor },
                      { label: '대표 브랜드',   val: report?.brand_focus ?? brands[0]?.brand ?? '-', sub: '검색 점유 1위' },
                      { label: '핵심 소비층',   val: topAge?.label ?? '-',               sub: 'DataLab 연령 분석' },
                      { label: '브랜드 수',     val: brands.length > 0 ? `${brands.length}개` : '-', sub: '검색 노출 기준' },
                    ].map(({ label, val, sub, color }) => (
                      <div key={label} className={s.reportKpi}>
                        <p className={s.reportKpiLabel}>{label}</p>
                        <p className={s.reportKpiVal} style={color ? { color } : {}}>{val}</p>
                        <p className={s.reportKpiSub}>{sub}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })()}

            {/* ── 외부 환경 신호 카드 ── */}
            {envSignal && envSignal.signals?.length > 0 && (
              <div className={s.envSignalCard}>
                <p className={s.envSignalTitle}>외부 환경 신호 <span className={s.envSignalBadge}>공공데이터</span></p>
                <div className={s.envSignalRow}>
                  {envSignal.signals.map((sig, i) => (
                    <div key={i} className={`${s.envSignalItem} ${s[`envLevel_${sig.level}`]}`}>
                      <span className={s.envSignalIcon}>{sig.icon}</span>
                      <span className={s.envSignalLabel}>{sig.label}</span>
                    </div>
                  ))}
                  {envSignal.vars?.kma_temp != null && (
                    <div className={s.envSignalMeta}>
                      {envSignal.vars.kma_temp}°C · {envSignal.vars.kma_humidity}% 습도
                      {envSignal.vars.air_pm25 != null && ` · PM2.5 ${envSignal.vars.air_pm25}㎍`}
                      {' · '}<span className={s.envSignalSource}>{envSignal.sources?.join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Section 1: 시장 현황 ── */}
            <div className={s.section}>
              <SectionHead num="01" title="시장 현황 · 관심도 추이" />
              <div className={s.marketNowGrid}>
                <div className={s.trendCard}>
                  <TrendChart data={trend} />
                  <div className={s.chartDivider} />
                  <p className={s.chartLabel}>관심도 추이</p>
                  <p className={s.sourceNote}>*DataLab · 검색량을 0~100으로 정규화한 상대적인 값</p>
                </div>
                <div className={s.metricsCol}>
                  <div className={`${s.metricCard} ${s.metricCardActive}`}>
                    <p className={s.metricCardLabel}>관심도 지수</p>
                    <p className={s.metricCardValue}>{report?.trend_score ?? '-'}</p>
                  </div>
                  <div className={s.metricCard}>
                    <p className={s.metricCardLabel}>증감률</p>
                    <p className={`${s.metricCardValue} ${growthPositive ? s.metricUp : s.metricDown}`}>
                      {report?.growth_rate != null ? `${growthPositive ? '+' : ''}${report.growth_rate}%` : '-'}
                    </p>
                  </div>
                  <div className={s.metricCard}>
                    <p className={s.metricCardLabel}>대표 브랜드</p>
                    <p className={s.metricCardValue} style={{ fontSize: 16 }}>{report?.brand_focus ?? brands[0]?.brand ?? '-'}</p>
                  </div>
                  <div className={s.metricCard}>
                    <p className={s.metricCardLabel}>핵심 소비층</p>
                    <p className={s.metricCardValue} style={{ fontSize: 16 }}>{topAge?.label ?? '-'}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Section 2: 브랜드 & 소비층 ── */}
            <div className={s.section}>
              <SectionHead num="02" title="브랜드 점유율 · 핵심 소비층" />
              <div className={s.twoCol}>
                <div className={s.card}>
                  <p className={s.cardTitle}>브랜드 점유율</p>
                  <p className={s.cardSub}>쇼핑 API 기준</p>
                  <BrandDonut brands={brands} />
                </div>
                <div className={s.card}>
                  <p className={s.cardTitle}>주요 소비층</p>
                  <p className={s.cardSub}>DataLab 연령대별 관심도</p>
                  <AgeBars age={age} />
                </div>
              </div>
            </div>

            {/* ── Section 3: 관심 키워드 ── */}
            {keywords.length > 0 && (
              <div className={s.section}>
                <SectionHead num="03" title="트렌드 분석 · 관심 키워드" />
                <KeywordSection title="주요 관심 키워드" items={keywords} isComplaint={false} token={token} category={category} />
              </div>
            )}

            {/* ── Section 4: 불만 키워드 ── */}
            {complaints.length > 0 && (
              <div className={s.section}>
                <SectionHead num="04" title="트렌드 분석 · 소비자 불만 요인" />
                <KeywordSection title="불만 키워드" items={complaints} isComplaint={true} />

                {/* 불만 빈도 분석 */}
                {complaintSummary.length > 0 && (
                  <div className={s.complaintSummaryCard}>
                    <p className={s.complaintSummaryTitle}>불만 빈도 분석 <span className={s.complaintSummaryNote}>제품 {complaints.length}개 기준</span></p>
                    <div className={s.complaintBars}>
                      {complaintSummary.map((item, i) => (
                        <div key={item.tag} className={s.complaintBarRow}>
                          <span className={s.complaintBarRank}>{i + 1}</span>
                          <span className={s.complaintBarTag}>{item.tag}</span>
                          <div className={s.complaintBarTrack}>
                            <div
                              className={s.complaintBarFill}
                              style={{ width: `${item.pct}%` }}
                            />
                          </div>
                          <span className={s.complaintBarPct}>{item.pct}%</span>
                          <div className={s.complaintBrands}>
                            {(item.brands ?? []).slice(0, 3).map(b => (
                              <span key={b} className={s.complaintBrandChip}>{b}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Section 5: 트렌드 분석 · 사용 환경 ── */}
            {trendCtx && (
              <div className={s.section}>
                <SectionHead num="05" title="시장 구조 · 설치 환경 · 구매 목적" />
                <div className={s.contextGrid}>
                  <div className={s.card}>
                    <p className={s.cardTitle}>주요 사용 환경</p>
                    <p className={s.cardSub}>지역별 검색 비율 (AI 추정)</p>
                    <HBar data={trendCtx.region} color="#6366f1" />
                  </div>
                  <div className={s.card}>
                    <p className={s.cardTitle}>설치 형태</p>
                    <p className={s.cardSub}>제품명 기준 분류</p>
                    <HBar data={trendCtx.install} color="#3b82f6" />
                  </div>
                  <div className={s.card}>
                    <p className={s.cardTitle}>구매 목적</p>
                    <p className={s.cardSub}>소비자 니즈 분석 (AI 분석)</p>
                    <HBar data={trendCtx.purpose} color="#10b981" />
                  </div>
                  <div className={s.card}>
                    <p className={s.cardTitle}>연관 가전</p>
                    <p className={s.cardSub}>함께 구매되는 제품 (AI 분석)</p>
                    <HBar data={trendCtx.related} color="#f59e0b" />
                  </div>
                </div>
              </div>
            )}

            {/* ── AI 요약 ── */}
            {report?.summary && (
              <div className={s.section}>
                <SectionHead num="06" title="AI 종합 분석" />
                <div className={s.card}>
                  {typeof report.summary === 'object' ? (
                    <div className={s.aiReport}>
                      {report.summary.growth_potential && (
                        <div className={s.aiReportRow}>
                          <span className={s.aiReportNum}>①</span>
                          <div>
                            <span className={s.aiReportLabel}>시장 성장 가능성</span>
                            <span className={`${s.aiReportBadge} ${
                              report.summary.growth_potential === '높음' ? s.aiBadgeHigh :
                              report.summary.growth_potential === '낮음' ? s.aiBadgeLow : s.aiBadgeMid
                            }`}>{report.summary.growth_potential}</span>
                          </div>
                        </div>
                      )}
                      {report.summary.competition_factors?.length > 0 && (
                        <div className={s.aiReportRow}>
                          <span className={s.aiReportNum}>②</span>
                          <div>
                            <span className={s.aiReportLabel}>주요 경쟁 요인</span>
                            <div className={s.aiTagList}>
                              {report.summary.competition_factors.map((f, i) => (
                                <span key={i} className={s.aiTag}>{f}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      {report.summary.risk_factors?.length > 0 && (
                        <div className={s.aiReportRow}>
                          <span className={s.aiReportNum}>③</span>
                          <div>
                            <span className={s.aiReportLabel}>주의 요소</span>
                            <div className={s.aiTagList}>
                              {report.summary.risk_factors.map((f, i) => (
                                <span key={i} className={`${s.aiTag} ${s.aiTagRisk}`}>{f}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      {(report.summary.conclusion_lines?.length > 0 || report.summary.conclusion) && (
                        <div className={s.aiReportRow}>
                          <span className={s.aiReportNum}>④</span>
                          <div style={{ flex: 1 }}>
                            <span className={s.aiReportLabel}>종합 판단</span>
                            <div>
                              {(report.summary.conclusion_lines ?? report.summary.conclusion?.split('\n\n') ?? []).map((para, i) => (
                                <p key={i} className={s.aiConclusion} style={{ marginTop: i > 0 ? 10 : 0 }}>
                                  {para}
                                </p>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ marginTop: 8 }}>
                      {String(report.summary).split('\n\n').filter(Boolean).map((para, i) => (
                        <p key={i} className={s.kwSummary} style={{ marginTop: i > 0 ? 10 : 0 }}>{para}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div className={s.reportFooter}>
              <span>본 리포트는 네이버 DataLab 검색 데이터, Groq LLM 분석, RAG 소비자 반응 기반으로 생성되었습니다.</span>
              <span>{fetchedAt ? fetchedAt.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) : ''} · {PERIOD_LABEL[period]}</span>
            </div>
          </>
        )}
          </div>

          <B2BSidebar
            category={category} setCategory={setCategory}
            periods={PERIODS} period={period} setPeriod={setPeriod}
            dataSources={['네이버 DataLab', 'Groq LLM', 'RAG (구매 패턴)', '소비자 불만 데이터']}
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
  )
}
