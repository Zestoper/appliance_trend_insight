import { useState } from 'react'
import styles from '../../../styles/dashboard/b2c/B2CTrendAnalysis.module.css'

const trendData = {
  monthly: {
    label: '월간',
    description: '최근 6개월 기준 · 0~100 지수',
    cards: [
      {
        category: '에어컨',
        growth: '+38.5%',
        status: '급상승',
        reason: '여름철 수요 증가와 전기요금 절감형 제품 관심 증가',
      },
      {
        category: '로봇청소기',
        growth: '+31.2%',
        status: '상승',
        reason: 'AI 장애물 인식, 자동 먼지 비움 기능 관련 언급 증가',
      },
      {
        category: '냉장고',
        growth: '+18.7%',
        status: '보합',
        reason: '비스포크·오브제 등 인테리어형 대형가전 검색 유지',
      },
    ],
    chart: [
      { label: '1월', aircon: 32, robot: 42, fridge: 58 },
      { label: '2월', aircon: 38, robot: 46, fridge: 55 },
      { label: '3월', aircon: 52, robot: 55, fridge: 60 },
      { label: '4월', aircon: 67, robot: 64, fridge: 61 },
      { label: '5월', aircon: 82, robot: 72, fridge: 63 },
      { label: '6월', aircon: 94, robot: 80, fridge: 66 },
    ],
    insightTitle: '에어컨과 로봇청소기의 관심도가 동시에 상승하고 있습니다.',
    insightText:
      '에어컨은 계절 수요와 전기요금 이슈의 영향을 받고 있으며, 로봇청소기는 AI 기능과 자동화 편의성에 대한 소비자 관심이 증가하고 있습니다.',
    keywords: ['무풍 에어컨', 'AI 로봇청소기', '비스포크 냉장고', '전기요금 절감', '자동 먼지 비움', '1등급 가전'],
  },

  weekly: {
    label: '주간',
    description: '최근 6주 기준 · 0~100 지수',
    cards: [
      {
        category: '로봇청소기',
        growth: '+14.8%',
        status: '급상승',
        reason: '자동 먼지 비움과 물걸레 기능 비교 검색 증가',
      },
      {
        category: '식기세척기',
        growth: '+11.6%',
        status: '상승',
        reason: '맞벌이 가구 중심으로 설치형 제품 관심 증가',
      },
      {
        category: '에어컨',
        growth: '+9.4%',
        status: '상승',
        reason: '초여름 할인 행사와 전기요금 절감 키워드 증가',
      },
    ],
    chart: [
      { label: '1주', aircon: 45, robot: 52, fridge: 34 },
      { label: '2주', aircon: 48, robot: 58, fridge: 38 },
      { label: '3주', aircon: 51, robot: 63, fridge: 41 },
      { label: '4주', aircon: 57, robot: 70, fridge: 43 },
      { label: '5주', aircon: 61, robot: 78, fridge: 46 },
      { label: '6주', aircon: 66, robot: 86, fridge: 49 },
    ],
    insightTitle: '이번 주간 데이터에서는 로봇청소기 관심도가 가장 빠르게 증가했습니다.',
    insightText:
      '자동 먼지 비움, 물걸레 세척, AI 장애물 회피 기능이 반복적으로 언급되며 구매 비교형 검색이 늘고 있습니다.',
    keywords: ['물걸레 로봇청소기', '자동 먼지 비움', '식기세척기 추천', '에어컨 할인', 'AI 장애물 회피', '설치비 비교'],
  },

  daily: {
    label: '일간',
    description: '최근 7일 기준 · 0~100 지수',
    cards: [
      {
        category: '에어컨',
        growth: '+6.9%',
        status: '급상승',
        reason: '기온 상승과 당일 배송 상품 검색 증가',
      },
      {
        category: '제습기',
        growth: '+5.7%',
        status: '상승',
        reason: '장마철 습도 관리 관련 검색 증가',
      },
      {
        category: '선풍기',
        growth: '+4.2%',
        status: '상승',
        reason: '저소음·BLDC 제품 관심 증가',
      },
    ],
    chart: [
      { label: '월', aircon: 55, robot: 38, fridge: 42 },
      { label: '화', aircon: 58, robot: 40, fridge: 43 },
      { label: '수', aircon: 63, robot: 42, fridge: 44 },
      { label: '목', aircon: 69, robot: 45, fridge: 45 },
      { label: '금', aircon: 74, robot: 47, fridge: 47 },
      { label: '토', aircon: 82, robot: 51, fridge: 49 },
      { label: '일', aircon: 88, robot: 54, fridge: 50 },
    ],
    insightTitle: '일간 기준으로는 에어컨과 제습기 검색 반응이 빠르게 올라오고 있습니다.',
    insightText:
      '기온 상승과 습도 이슈가 겹치면서 냉방·제습 제품의 단기 검색량이 증가하고 있습니다.',
    keywords: ['에어컨 당일배송', '제습기 추천', 'BLDC 선풍기', '냉방비 절약', '저소음 선풍기', '장마 가전'],
  },
}

export default function B2CTrendAnalysis() {
  const [period, setPeriod] = useState('monthly')
  const currentData = trendData[period]

  return (
    <>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>TREND ANALYSIS</p>
          <h1>가전 트렌드 분석</h1>
          <p>검색량, 쇼핑 순위, 리뷰 언급량을 기반으로 현재 관심도가 높은 가전 카테고리를 분석합니다.</p>
        </div>

        <div className={styles.filterBox}>
          <button
            className={period === 'monthly' ? styles.active : ''}
            onClick={() => setPeriod('monthly')}
          >
            월간
          </button>
          <button
            className={period === 'weekly' ? styles.active : ''}
            onClick={() => setPeriod('weekly')}
          >
            주간
          </button>
          <button
            className={period === 'daily' ? styles.active : ''}
            onClick={() => setPeriod('daily')}
          >
            일간
          </button>
        </div>
      </header>

      <section className={styles.summaryGrid}>
        {currentData.cards.map(item => (
          <div className={styles.summaryCard} key={item.category}>
            <div>
              <p>{item.status}</p>
              <h2>{item.category}</h2>
            </div>
            <strong>{item.growth}</strong>
            <span>{item.reason}</span>
          </div>
        ))}
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.panelLarge}>
          <div className={styles.panelHeader}>
            <div>
              <h3>카테고리별 검색 관심도 추이</h3>
              <p>{currentData.description}</p>
            </div>
            <span>Search Trend</span>
          </div>

          <div className={styles.lineChart}>
            {currentData.chart.map(item => (
              <div className={styles.monthGroup} key={item.label}>
                <div className={styles.bars}>
                  <span className={styles.aircon} style={{ height: `${item.aircon}%` }} />
                  <span className={styles.robot} style={{ height: `${item.robot}%` }} />
                  <span className={styles.fridge} style={{ height: `${item.fridge}%` }} />
                </div>
                <p>{item.label}</p>
              </div>
            ))}
          </div>

          <div className={styles.legend}>
            <span><i className={styles.airconDot} />에어컨</span>
            <span><i className={styles.robotDot} />로봇청소기</span>
            <span><i className={styles.fridgeDot} />냉장고</span>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>AI 분석 요약</h3>
              <p>현재 트렌드 상승 원인</p>
            </div>
          </div>

          <div className={styles.aiInsight}>
            <b>{currentData.insightTitle}</b>
            <p>{currentData.insightText}</p>
            <strong>추천 확인 포인트: 가격 변동, 신제품 출시, 리뷰 내 불만 키워드</strong>
          </div>
        </div>
      </section>

      <section className={styles.bottomGrid}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>급상승 키워드</h3>
              <p>검색·리뷰·뉴스에서 반복 등장</p>
            </div>
          </div>

          <div className={styles.keywordBox}>
            {currentData.keywords.map(keyword => (
              <span key={keyword}>{keyword}</span>
            ))}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div>
              <h3>소비자 반응 변화</h3>
              <p>커뮤니티·리뷰 요약</p>
            </div>
          </div>

          <div className={styles.reactionList}>
            <div>
              <b>긍정 증가</b>
              <p>저소음, 자동화, 에너지 효율 관련 만족도가 높게 나타납니다.</p>
            </div>
            <div>
              <b>부정 증가</b>
              <p>설치비, 필터 교체 비용, 배송 지연에 대한 불만이 일부 증가했습니다.</p>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}