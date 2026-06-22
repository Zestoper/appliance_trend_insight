import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/Timing.module.css'
import { API_BASE } from '../config'

const QUICK_EXAMPLES = [
  '삼성 비스포크 냉장고',
  'LG 스타일러',
  '다이슨 에어랩',
  '삼성 갤럭시 버즈',
  '로보락 로봇청소기',
  'LG 휘센 에어컨',
  '삼성 드럼세탁기',
  '브레빌 에스프레소',
]

const COLOR_MAP = {
  green:  { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.3)', text: '#22c55e' },
  blue:   { bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.3)', text: '#3b82f6' },
  yellow: { bg: 'rgba(234,179,8,0.1)', border: 'rgba(234,179,8,0.3)', text: '#eab308' },
  red:    { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: '#ef4444' },
}

// y축 nice 눈금 계산: 데이터 범위에 맞는 보기 좋은 간격 자동 결정
function niceAxis(dataMin, dataMax) {
  const dataRange = dataMax - dataMin
  // 최소 패딩: 데이터 범위의 15% 또는 최대값의 2% (평탄 그래프 대비)
  const padding = Math.max(dataRange * 0.15, dataMax * 0.02)
  const lo = dataMin - padding
  const hi = dataMax + padding
  const span = hi - lo

  const rough = span / 4
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(rough, 1))))
  const n = rough / mag
  const step = n <= 1 ? mag : n <= 2 ? 2 * mag : n <= 5 ? 5 * mag : 10 * mag

  const domainMin = Math.floor(lo / step) * step
  const domainMax = Math.ceil(hi / step) * step

  const ticks = []
  for (let v = domainMin; v <= domainMax + step * 0.001; v += step) {
    ticks.push(Math.round(v))
  }
  return { domainMin, domainMax, ticks, step }
}

function fmtTick(won, step) {
  if (step >= 10000) return Math.round(won / 10000) + '만'
  if (step >= 1000 && won >= 10000) return (won / 10000).toFixed(1) + '만'
  return won.toLocaleString()
}

function LineChart({ values, gradId, stroke, yLabels, xLabels, refLines = [], markMinMax = false, changeLabels = [] }) {
  if (!values || values.length < 2) return null
  const W = 600, H = 160, padX = 8, padY = 14
  const maxV = Math.max(...values, 1)
  const minV = Math.min(...values)
  const range = maxV - minV || 1
  const toY = v => padY + (H - padY * 2) * (1 - (v - minV) / range)
  const pts = values.map((v, i) => {
    const x = padX + (i / (values.length - 1)) * (W - padX * 2)
    return [x, toY(v)]
  })
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `${padX},${H - padY} ${line} ${W - padX},${H - padY}`

  const minIdx = values.indexOf(Math.min(...values))
  const maxIdx = values.indexOf(Math.max(...values))

  return (
    <div className={styles.chartWrap}>
      <div className={styles.chartYAxis}>
        {yLabels.map((l, i) => <span key={i}>{l}</span>)}
      </div>
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
          style={{ width: '100%', height: '160px', display: 'block' }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.3" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
            </linearGradient>
          </defs>
          {/* 기준선: 최고/평균/최저 */}
          {refLines.map((rl, i) => (
            <line key={i}
              x1={padX} y1={toY(rl.value).toFixed(1)}
              x2={W - padX} y2={toY(rl.value).toFixed(1)}
              stroke={rl.color} strokeWidth="1" strokeDasharray="4,3"
              strokeOpacity="0.5" vectorEffect="non-scaling-stroke"
            />
          ))}
          <polygon points={area} fill={`url(#${gradId})`} />
          <polyline points={line} fill="none" stroke={stroke} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          {/* 최저가 포인트 */}
          {markMinMax && (
            <circle cx={pts[minIdx][0]} cy={pts[minIdx][1]} r="4"
              fill="#22c55e" vectorEffect="non-scaling-stroke" />
          )}
          {/* 최고가 포인트 */}
          {markMinMax && minIdx !== maxIdx && (
            <circle cx={pts[maxIdx][0]} cy={pts[maxIdx][1]} r="4"
              fill="#ef4444" vectorEffect="non-scaling-stroke" />
          )}
          {/* 현재가 포인트 */}
          <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="4"
            fill={stroke} vectorEffect="non-scaling-stroke" />
        </svg>

        {/* 가격 변동 포인트 레이블 (날짜 + 가격) */}
        {changeLabels.map((cl, i) => {
          const pct = cl.idx / (values.length - 1) * 100
          const yPct = (pts[cl.idx][1] / H) * 100
          const alignRight = pct > 70
          return (
            <div key={i} style={{
              position: 'absolute',
              left: `${pct}%`,
              top: `${yPct}%`,
              transform: `translate(${alignRight ? '-100%' : '8px'}, -130%)`,
              background: 'rgba(20,20,35,0.92)',
              border: `1px solid ${cl.color}44`,
              borderRadius: '5px',
              padding: '3px 7px',
              fontSize: '10px',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              lineHeight: '1.5',
            }}>
              <div style={{ color: 'var(--text-muted)' }}>{cl.date}</div>
              <div style={{ color: cl.color, fontWeight: 700 }}>{cl.price.toLocaleString()}원</div>
            </div>
          )
        })}

        {/* x축 레이블: 절대 위치로 정확한 날짜 표시 */}
        <div style={{ position: 'relative', height: '18px', marginTop: '4px' }}>
          {xLabels.map((item, i) => {
            const isObj = typeof item === 'object' && item !== null
            const label = isObj ? item.label : item
            const pct   = isObj ? item.pct   : (i / Math.max(xLabels.length - 1, 1) * 100)
            return (
              <span key={i} style={{
                position: 'absolute',
                left: `${pct}%`,
                transform: pct < 5 ? 'none' : pct > 95 ? 'translateX(-100%)' : 'translateX(-50%)',
                fontSize: '10px',
                color: 'var(--text-muted)',
                whiteSpace: 'nowrap',
              }}>{label}</span>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function ScoreSparkline({ data, color, curMin }) {
  const dotColor = { green: '#22c55e', blue: '#3b82f6', yellow: '#eab308', red: '#ef4444' }[color] || '#6366f1'
  const prices = data && data.length >= 2 ? data.map(d => d.price) : null

  return (
    <div style={{ padding: '4px 0 6px' }}>
      {/* 현재가 */}
      <div style={{ marginBottom: '10px' }}>
        <span style={{ fontSize: '26px', fontWeight: 900, color: dotColor }}>
          {curMin.toLocaleString()}원
        </span>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>현재가</span>
      </div>

      {/* 스파크라인 */}
      {prices ? (() => {
        const W = 400, H = 72
        const maxV = Math.max(...prices, 1)
        const minV = Math.min(...prices)
        const range = maxV - minV || 1
        const pad = 6
        const pts = prices.map((v, i) => {
          const x = pad + (i / (prices.length - 1)) * (W - pad * 2)
          const y = pad + (H - pad * 2) * (1 - (v - minV) / range)
          return [x, y]
        })
        const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
        const area = `${pad},${H - pad} ${line} ${W - pad},${H - pad}`
        const last = pts[pts.length - 1]
        return (
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
            style={{ width: '100%', height: '72px', display: 'block' }}>
            <defs>
              <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={dotColor} stopOpacity="0.25" />
                <stop offset="100%" stopColor={dotColor} stopOpacity="0.02" />
              </linearGradient>
            </defs>
            <polygon points={area} fill="url(#sparkGrad)" />
            <polyline points={line} fill="none" stroke={dotColor} strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            <circle cx={last[0]} cy={last[1]} r="4" fill={dotColor}
              vectorEffect="non-scaling-stroke" />
          </svg>
        )
      })() : (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
          이력 누적 중 — 재방문 시 그래프 표시
        </div>
      )}
    </div>
  )
}

function PriceLineChart({ gridData, maxP, minP, avgP, launchPrice, xLabels, changeLabels }) {
  const W = 600, H = 160, padX = 8, padY = 14

  const { domainMin, domainMax, ticks, step } = niceAxis(minP, maxP)
  const domainRange = domainMax - domainMin || 1
  const toY = v => padY + (H - padY * 2) * (1 - (v - domainMin) / domainRange)
  const toX = i => padX + (i / (gridData.length - 1)) * (W - padX * 2)

  const dataPts = gridData
    .map((d, i) => d.price != null ? { idx: i, x: toX(i), y: toY(d.price) } : null)
    .filter(Boolean)

  if (!dataPts.length) return null

  const lineStr = dataPts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const areaStr = `${dataPts[0].x.toFixed(1)},${H - padY} ${lineStr} ${dataPts[dataPts.length - 1].x.toFixed(1)},${H - padY}`
  const stroke  = '#818cf8'

  // y축: nice 눈금값 위치 계산
  const yTicks = ticks.map(v => ({
    label: fmtTick(v, step),
    topPct: toY(v) / H * 100,
  }))

  return (
    <div className={styles.chartWrap}>
      <div style={{ width: '38px', flexShrink: 0, position: 'relative' }}>
        {yTicks.map((t, i) => (
          <span key={i} style={{
            position: 'absolute',
            top: `${t.topPct}%`,
            right: '4px',
            transform: 'translateY(-50%)',
            fontSize: '10px',
            color: 'var(--text-muted)',
            whiteSpace: 'nowrap',
            textAlign: 'right',
          }}>{t.label}</span>
        ))}
      </div>
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
          style={{ width: '100%', height: '160px', display: 'block' }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
            </linearGradient>
          </defs>
          {/* nice 눈금 grid lines (subtle) */}
          {ticks.map((v, i) => (
            <line key={i} x1={padX} y1={toY(v).toFixed(1)} x2={W - padX} y2={toY(v).toFixed(1)}
              stroke="rgba(255,255,255,0.05)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          ))}
          {/* 최고/평균/최저 컬러 기준선 */}
          {[{ v: maxP, c: '#ef4444' }, { v: avgP, c: '#eab308' }, { v: minP, c: '#22c55e' }].map((rl, i) => (
            <line key={i} x1={padX} y1={toY(rl.v).toFixed(1)} x2={W - padX} y2={toY(rl.v).toFixed(1)}
              stroke={rl.c} strokeWidth="1" strokeDasharray="4,3" strokeOpacity="0.4"
              vectorEffect="non-scaling-stroke" />
          ))}
          {/* 출시가 기준선 (도메인 내에 있을 때만) */}
          {launchPrice && launchPrice >= domainMin && launchPrice <= domainMax && (
            <line x1={padX} y1={toY(launchPrice).toFixed(1)} x2={W - padX} y2={toY(launchPrice).toFixed(1)}
              stroke="#a78bfa" strokeWidth="1" strokeDasharray="6,3" strokeOpacity="0.7"
              vectorEffect="non-scaling-stroke" />
          )}
          <polygon points={areaStr} fill="url(#priceGrad)" />
          <polyline points={lineStr} fill="none" stroke={stroke} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          {dataPts.map((p, i) => (
            <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="3"
              fill={stroke} vectorEffect="non-scaling-stroke" />
          ))}
        </svg>

        {/* 변동 레이블 */}
        {changeLabels.map((cl, i) => {
          const dp = dataPts.find(p => p.idx === cl.idx)
          if (!dp) return null
          const xPct = dp.idx / (gridData.length - 1) * 100
          const yPct = dp.y / H * 100
          const shiftX = xPct > 65 ? 'calc(-100% - 6px)' : '8px'
          const shiftY = yPct < 25 ? '8px' : '-130%'
          return (
            <div key={i} style={{
              position: 'absolute',
              left: `${xPct}%`,
              top: `${yPct}%`,
              transform: `translate(${shiftX}, ${shiftY})`,
              background: 'rgba(12,12,24,0.93)',
              border: `1px solid ${cl.color}50`,
              borderRadius: '5px',
              padding: '3px 8px',
              fontSize: '10px',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              lineHeight: '1.6',
              zIndex: 10,
            }}>
              <div style={{ color: 'var(--text-muted)' }}>{cl.date}</div>
              <div style={{ color: cl.color, fontWeight: 700 }}>{cl.price.toLocaleString()}원</div>
            </div>
          )
        })}

        <div style={{ position: 'relative', height: '18px', marginTop: '4px' }}>
          {xLabels.map((item, i) => (
            <span key={i} style={{
              position: 'absolute',
              left: `${item.pct}%`,
              transform: item.pct < 5 ? 'none' : item.pct > 95 ? 'translateX(-100%)' : 'translateX(-50%)',
              fontSize: '10px', color: 'var(--text-muted)', whiteSpace: 'nowrap',
            }}>{item.label}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function PriceChart({ data, launchPrice, launchDiscPct }) {
  const actual = (data || []).filter(d => d.price > 0)
  if (actual.length < 2) {
    const curPrice = actual[0]?.price
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        minHeight: '160px', background: 'rgba(255,255,255,0.03)',
        border: '1px dashed rgba(255,255,255,0.08)', borderRadius: '8px',
        flexDirection: 'column', gap: '10px', padding: '28px 20px',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)',
          borderRadius: '999px', padding: '4px 12px',
          fontSize: '11px', fontWeight: 700, color: '#818cf8', letterSpacing: '0.05em',
        }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          최근 등록된 신규 제품
        </div>
        {curPrice && (
          <p style={{ margin: 0, fontSize: '22px', fontWeight: 900, color: 'var(--text)', letterSpacing: '-0.5px' }}>
            {curPrice.toLocaleString()}원
            <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-muted)', marginLeft: '8px' }}>현재가</span>
          </p>
        )}
        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.6 }}>
          가격 이력이 아직 없어요. 재방문하면 추이 그래프가 표시됩니다.
        </p>
      </div>
    )
  }

  // 데이터 첫날 ~ 오늘 기준으로 그리드 생성 (최소 7일, 최대 30일)
  const today = new Date()
  const todayStr = today.toISOString().slice(0, 10)
  const firstDay = actual.reduce((a, b) => a.period < b.period ? a : b).period
  const msPerDay = 86400000
  const diffDays = Math.round((new Date(todayStr) - new Date(firstDay)) / msPerDay)
  const gridDays = Math.min(diffDays + 1, 30)
  const gridStart = new Date(today)
  gridStart.setDate(today.getDate() - (gridDays - 1))

  const grid = Array.from({ length: gridDays }, (_, i) => {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    return d.toISOString().slice(0, 10)
  })
  const priceMap = Object.fromEntries(actual.map(d => [d.period, d.price]))
  const gridData = grid.map(day => ({ day, price: priceMap[day] ?? null }))
  const last = gridDays - 1

  const prices = actual.map(d => d.price)
  const maxP = Math.max(...prices)
  const minP = Math.min(...prices)
  const avgP = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)

  // x축: 7일 간격 + 첫날·마지막날, 너무 가까운 레이블 제거
  const rawXLabels = gridData
    .map((d, i) => (i === 0 || i === last || i % 7 === 0)
      ? { label: d.day.slice(5, 10), pct: i / last * 100 } : null)
    .filter(Boolean)
  const xLabels = rawXLabels.filter((item, i, arr) =>
    i === 0 || item.pct - arr[i - 1].pct >= 8
  )

  // 변동 레이블: 최저·최고 + 전일 대비 3% 이상 변동
  const minGridIdx = gridData.findIndex(d => d.price === minP)
  const maxGridIdx = gridData.findIndex(d => d.price === maxP)
  const changeCandidates = []
  if (minGridIdx >= 0) changeCandidates.push({ idx: minGridIdx, date: gridData[minGridIdx].day.slice(5,10), price: minP, color: '#22c55e' })
  if (maxGridIdx >= 0 && maxGridIdx !== minGridIdx) changeCandidates.push({ idx: maxGridIdx, date: gridData[maxGridIdx].day.slice(5,10), price: maxP, color: '#ef4444' })

  let prev = null
  gridData.forEach((d, i) => {
    if (d.price == null) { prev = null; return }
    if (prev != null && i !== minGridIdx && i !== maxGridIdx) {
      const chg = Math.abs(d.price - prev) / prev
      if (chg >= 0.03)
        changeCandidates.push({ idx: i, date: d.day.slice(5,10), price: d.price, color: d.price < prev ? '#22c55e' : '#ef4444' })
    }
    prev = d.price
  })
  const changeLabels = changeCandidates
    .sort((a, b) => a.idx - b.idx)
    .filter((cl, i, arr) => i === 0 || cl.idx - arr[i - 1].idx > Math.max(2, Math.floor(gridDays / 10)))

  return (
    <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '10px', fontSize: '12px' }}>
        <span><span style={{ color: '#22c55e', marginRight: '4px' }}>●</span>최저 <b style={{ color: '#22c55e' }}>{minP.toLocaleString()}원</b></span>
        <span><span style={{ color: '#eab308', marginRight: '4px' }}>●</span>평균 <b style={{ color: '#eab308' }}>{avgP.toLocaleString()}원</b></span>
        <span><span style={{ color: '#ef4444', marginRight: '4px' }}>●</span>최고 <b style={{ color: '#ef4444' }}>{maxP.toLocaleString()}원</b></span>
        {launchPrice && (
          <span>
            <span style={{ color: '#a78bfa', marginRight: '4px' }}>◆</span>
            출시가 <b style={{ color: '#a78bfa' }}>{launchPrice.toLocaleString()}원</b>
            {launchDiscPct > 0 && (
              <span style={{ color: '#22c55e', marginLeft: '4px', fontWeight: 600 }}>
                -{launchDiscPct}%
              </span>
            )}
          </span>
        )}
      </div>
      <PriceLineChart
        gridData={gridData}
        maxP={maxP} minP={minP} avgP={avgP}
        launchPrice={launchPrice}
        xLabels={xLabels}
        changeLabels={changeLabels}
      />
    </>
  )
}

function SearchChart({ data }) {
  if (!data || data.length < 2) return null
  const ratios = data.map(d => d.ratio)
  const maxR = Math.max(...ratios, 1)
  const step = Math.max(1, Math.ceil(data.length / 7))
  const xLabels = data
    .map((d, i) => {
      if (i === 0 || i === data.length - 1 || i % step === 0)
        return { label: d.period.slice(5, 10), pct: i / (data.length - 1) * 100 }
      return null
    })
    .filter(Boolean)
  return (
    <LineChart
      values={ratios}
      gradId="searchGrad"
      stroke="#22d3ee"
      yLabels={[Math.round(maxR), Math.round(maxR / 2), '0']}
      xLabels={xLabels}
    />
  )
}

const LIST_PAGE_SIZE = 12
const _EXCLUDE_LIST = ['렌탈', '월렌탈', '구독', '리스', '대여', '렌트', '부품', '필터', '액세서리', '케이스', '호환']

export default function Timing() {
  const [searchParams, setSearchParams] = useSearchParams()
  const urlQ   = searchParams.get('q')   || ''
  const urlPid = searchParams.get('pid') || ''

  const [input, setInput] = useState(urlQ)
  const [listResults, setListResults] = useState([])
  const [listPage, setListPage] = useState(1)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 검색창 값을 URL q 파라미터와 동기화
  useEffect(() => { setInput(urlQ) }, [urlQ])

  // q 변경 시 제품 목록 fetch (pid 없을 때만)
  useEffect(() => {
    if (!urlQ || urlPid) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setListPage(1);
    (async () => {
      try {
        const data = await fetch(
          `${API_BASE}/api/naver/products?query=${encodeURIComponent(urlQ)}&display=50&sort=sim`
        ).then(r => r.json())
        if (cancelled) return
        const items = (data.items || []).filter(it =>
          it.price > 0 &&
          !_EXCLUDE_LIST.some(kw => it.title.includes(kw)) &&
          !_EXCLUDE_LIST.some(kw => it.mallName.includes(kw))
        )
        if (!items.length) setError(`"${urlQ}"에 대한 제품을 찾지 못했습니다.`)
        else setListResults(items)
      } catch {
        if (!cancelled) setError('서버에 연결할 수 없습니다')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [urlQ, urlPid])

  // pid 변경 시 타이밍 분석 fetch
  useEffect(() => {
    if (!urlPid) { setResult(null); return }
    let cancelled = false
    setLoading(true)
    setError(null)
    const cached = listResults.find(p => String(p.id) === urlPid)
    const title = cached?.title || urlQ;
    (async () => {
      try {
        const data = await fetch(
          `${API_BASE}/api/timing?category=${encodeURIComponent(title)}&product_id=${encodeURIComponent(urlPid)}`
        ).then(r => r.json())
        if (cancelled) return
        if (!data.analysis) setError(data.error ?? '분석 실패')
        else setResult(data)
      } catch {
        if (!cancelled) setError('서버에 연결할 수 없습니다')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [urlPid])

  function handleSubmit(e) {
    e.preventDefault()
    const term = input.trim()
    if (!term) return
    setSearchParams({ q: term })
  }

  function handleSelectProduct(product) {
    setSearchParams({ q: urlQ, pid: String(product.id) })
  }

  const view = loading ? 'loading' : error ? 'error' : urlPid ? 'detail' : urlQ ? 'list' : 'idle'
  const analysis = result?.analysis
  const col = analysis ? COLOR_MAP[analysis.color] ?? COLOR_MAP.blue : null

  return (
    <div className={styles.page} data-scroll-container>
      <Navbar />
      <div className={styles.container}>

        <div className={styles.header}>
          <span className={styles.badge}>구매 타이밍</span>
          <h1 className={styles.title}>지금 사야 할까요?</h1>
          <p className={styles.subtitle}>
            브랜드나 제품명으로 검색해 원하는 제품을 고르면<br />
            30일 가격 이력으로 지금이 구매 적기인지 알려드려요.
          </p>
        </div>

        {/* 검색창 */}
        {!loading && (
          <form className={styles.searchForm} onSubmit={handleSubmit}>
            <div className={styles.searchWrap}>
              <span className={styles.searchIcon}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <line x1="16.5" y1="16.5" x2="22" y2="22" />
                </svg>
              </span>
              <input
                className={styles.searchInput}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="브랜드나 제품명 입력 (예: 삼성, 아이폰 14)"
                autoFocus
              />
              <button type="submit" className={styles.searchBtn}>검색</button>
            </div>
          </form>
        )}

        {/* 예시 태그 */}
        {view === 'idle' && (
          <div className={styles.examples}>
            {QUICK_EXAMPLES.map(ex => (
              <button key={ex} className={styles.exTag} onClick={() => setSearchParams({ q: ex })}>
                {ex}
              </button>
            ))}
          </div>
        )}

        {/* 로딩 */}
        {loading && (
          <div className={styles.loadingWrap}>
            <div className={styles.spinner} />
            <p>{urlPid ? '가격 데이터 분석 중...' : `"${urlQ}" 제품 검색 중...`}</p>
          </div>
        )}

        {/* 에러 */}
        {view === 'error' && (
          <div className={styles.errorWrap}>
            <p className={styles.errorText}>{error}</p>
            <button className={styles.retryBtn} onClick={() => {
              setError(null)
              if (urlPid) setSearchParams({ q: urlQ })
              else setSearchParams({})
            }}>
              {urlPid ? '← 목록으로' : '다시 검색'}
            </button>
          </div>
        )}

        {/* 제품 목록 */}
        {view === 'list' && (() => {
          const totalPages = Math.ceil(listResults.length / LIST_PAGE_SIZE)
          const paged = listResults.slice((listPage - 1) * LIST_PAGE_SIZE, listPage * LIST_PAGE_SIZE)
          return (
            <div className={styles.resultWrap}>
              <p className={styles.queryLabel}>
                <span className={styles.queryChip}>"{urlQ}"</span> 검색 결과 — 분석할 제품을 선택하세요
                <span style={{ marginLeft: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  {listResults.length}개
                </span>
              </p>
              <div className={styles.productGrid}>
                {paged.map(product => (
                  <button
                    key={product.id}
                    className={styles.productCard}
                    onClick={() => handleSelectProduct(product)}
                  >
                    {product.image && (
                      <img
                        src={product.image}
                        alt={product.title}
                        className={styles.productCardImg}
                      />
                    )}
                    <p className={styles.productCardName}>{product.title}</p>
                    <div>
                      <p className={styles.productCardPrice}>{product.price.toLocaleString()}원</p>
                      <p className={styles.productCardMall}>{product.mallName}</p>
                    </div>
                  </button>
                ))}
              </div>
              {totalPages > 1 && (
                <div className={styles.pagination}>
                  <button
                    className={styles.pageBtn}
                    onClick={() => setListPage(p => Math.max(1, p - 1))}
                    disabled={listPage === 1}
                  >←</button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                    <button
                      key={p}
                      className={`${styles.pageBtn} ${p === listPage ? styles.pageBtnActive : ''}`}
                      onClick={() => setListPage(p)}
                    >{p}</button>
                  ))}
                  <button
                    className={styles.pageBtn}
                    onClick={() => setListPage(p => Math.min(totalPages, p + 1))}
                    disabled={listPage === totalPages}
                  >→</button>
                </div>
              )}
              <button className={styles.resetBtn} onClick={() => setSearchParams({})}>
                ← 다시 검색
              </button>
            </div>
          )
        })()}

        {/* 분석 결과 */}
        {view === 'detail' && analysis && (
          <div className={styles.resultWrap}>

            <p className={styles.queryLabel}>
              <span className={styles.queryChip}>"{urlQ}"</span> 구매 타이밍 분석
            </p>

            {/* 추적 중인 제품 */}
            {result.tracked_product && (
              <a
                href={result.tracked_product.link}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.trackedCard}
              >
                {result.tracked_product.image && (
                  <img
                    src={result.tracked_product.image}
                    alt={result.tracked_product.title}
                    className={styles.trackedImg}
                  />
                )}
                <div className={styles.trackedInfo}>
                  <p className={styles.trackedLabel}>추적 중인 제품</p>
                  <p className={styles.trackedTitle}>{result.tracked_product.title}</p>
                  <p className={styles.trackedPrice}>
                    {result.tracked_product.price?.toLocaleString()}원
                    <span className={styles.trackedMall}> · {result.tracked_product.mallName}</span>
                  </p>
                </div>
              </a>
            )}

            {/* 점수 카드 */}
            <div className={styles.scoreCard}
              style={{ background: col.bg, borderColor: col.border }}>
              <div className={styles.scoreLeft}>
                <div>
                  <p className={styles.scoreLabel}>구매 타이밍</p>
                  <p className={styles.scoreBig} style={{ color: col.text }}>{analysis.score}</p>
                </div>
                <p className={styles.scoreMsg}>{analysis.message}</p>
              </div>
              <div className={styles.scoreRight}>
                <ScoreSparkline
                  data={result.data}
                  color={analysis.color}
                  curMin={analysis.cur_min}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                  <span>평균 대비 <b style={{ color: col.text }}>{analysis.diff_pct > 0 ? '+' : ''}{analysis.diff_pct}%</b></span>
                  <span>가격 추세 <b style={{ color: 'var(--text)' }}>{analysis.trend_dir}</b></span>
                </div>
              </div>
            </div>

            {/* 가격 차트 */}
            <div className={styles.chartCard}>
              <p className={styles.chartTitle}>
                최근 30일 최저가 추이
                {!analysis.has_history && (
                  <span style={{ fontSize: '0.75rem', color: '#6b6b80', marginLeft: '8px' }}>
                    (이력 누적 중 — 재방문 시 더 정확한 분석 제공)
                  </span>
                )}
              </p>
              <PriceChart data={result.data} launchPrice={analysis.launch_price} launchDiscPct={analysis.launch_disc_pct} />
              <p className={styles.chartNote}>
                역대 최저가 기록일: {analysis.low_day} &nbsp;·&nbsp; 현재 최저가: {analysis.cur_min?.toLocaleString()}원
              </p>
            </div>

            {/* 검색량 차트 */}
            {result.search_data?.length >= 7 && (
              <div className={styles.chartCard}>
                <p className={styles.chartTitle}>
                  최근 30일 검색 관심도 추이
                  {analysis.search_summary?.keyword && analysis.search_summary.keyword !== urlQ && (
                    <span style={{ fontSize: '0.75rem', color: '#6b6b80', marginLeft: '8px' }}>
                      (키워드: {analysis.search_summary.keyword})
                    </span>
                  )}
                </p>
                <SearchChart data={result.search_data} />
                {analysis.search_summary && (
                  <p className={styles.chartNote}>
                    현재 관심도: {analysis.search_summary.current}
                    &nbsp;·&nbsp;
                    30일 평균: {analysis.search_summary.avg90}
                    &nbsp;·&nbsp;
                    평균 대비: {analysis.search_summary.diff_pct > 0 ? '+' : ''}{analysis.search_summary.diff_pct}%
                    &nbsp;·&nbsp;
                    최고점: {analysis.search_summary.peak_day}
                  </p>
                )}
              </div>
            )}

            {/* 뒤로가기 — 브라우저 히스토리 기반 */}
            <button className={styles.resetBtn} onClick={() => setSearchParams({ q: urlQ })}>
              ← 목록으로
            </button>

          </div>
        )}

      </div>
    </div>
  )
}
