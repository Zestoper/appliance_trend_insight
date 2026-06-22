export const MOCK_PRODUCTS = {
  냉장고: [
    { id: 'rf85c9141ap', name: '비스포크 냉장고 RF85C9141AP', brand: 'Samsung', price: 1897000, rating: 4.6, reviewCount: 12847, interest: 82, sentiment: { pos: 74, neg: 26 } },
    { id: 'grb247jwaf',  name: 'DIOS 오브제컬렉션 M874GBB041', brand: 'LG', price: 2150000, rating: 4.7, reviewCount: 8932, interest: 78, sentiment: { pos: 80, neg: 20 } },
    { id: 'rt53cb6a5b2', name: '삼성 일반형 냉장고 RT53CB6A5B2', brand: 'Samsung', price: 749000, rating: 4.3, reviewCount: 5421, interest: 61, sentiment: { pos: 68, neg: 32 } },
    { id: 'gbb72nsugn',  name: '보쉬 프리스탠딩 냉장고 GBB72NSUGN', brand: 'Bosch', price: 1320000, rating: 4.5, reviewCount: 2104, interest: 55, sentiment: { pos: 77, neg: 23 } },
    { id: 'arbd184d3a',  name: '딤채 스탠드형 김치냉장고 ARBD184D3A', brand: 'Winia', price: 980000, rating: 4.4, reviewCount: 9871, interest: 70, sentiment: { pos: 72, neg: 28 } },
    { id: 'z790ngw',     name: '위니아 4도어 냉장고 WWRN580GBBW', brand: 'Winia', price: 1190000, rating: 4.2, reviewCount: 3204, interest: 49, sentiment: { pos: 65, neg: 35 } },
  ],
  세탁기: [
    { id: 'wf25b5500kw', name: '비스포크 그랑데AI WF25B5500KW', brand: 'Samsung', price: 1290000, rating: 4.7, reviewCount: 18423, interest: 88, sentiment: { pos: 83, neg: 17 } },
    { id: 'f21vd_5rt',   name: 'DIOS 오브제컬렉션 F21VD_5RT', brand: 'LG', price: 1450000, rating: 4.8, reviewCount: 14201, interest: 91, sentiment: { pos: 86, neg: 14 } },
    { id: 'wm710a0g',    name: 'LG 트롬 세탁기 WM710A0G', brand: 'LG', price: 690000, rating: 4.4, reviewCount: 6832, interest: 63, sentiment: { pos: 71, neg: 29 } },
    { id: 'wf21t6500kw', name: '삼성 세탁기 WF21T6500KW', brand: 'Samsung', price: 780000, rating: 4.3, reviewCount: 7201, interest: 58, sentiment: { pos: 69, neg: 31 } },
  ],
  건조기: [
    { id: 'dv16t8520bv', name: '그랑데AI 건조기 DV16T8520BV', brand: 'Samsung', price: 1050000, rating: 4.6, reviewCount: 9201, interest: 79, sentiment: { pos: 78, neg: 22 } },
    { id: 'rc16v_5ru0w', name: 'DIOS 건조기 RC16V_5RU0W', brand: 'LG', price: 1120000, rating: 4.7, reviewCount: 8104, interest: 82, sentiment: { pos: 81, neg: 19 } },
  ],
  에어컨: [
    { id: 'ar18cy4aatwk', name: '비스포크 무풍갤러리 AR18CY4AATWK', brand: 'Samsung', price: 1590000, rating: 4.6, reviewCount: 11023, interest: 85, sentiment: { pos: 79, neg: 21 } },
    { id: 'fu18hdca2a',   name: 'DIOS 에어컨 FU18HDCA2A', brand: 'LG', price: 1720000, rating: 4.7, reviewCount: 9847, interest: 87, sentiment: { pos: 82, neg: 18 } },
    { id: 'msz-gf50vad',  name: '미쓰비시 에어컨 MSZ-GF50VAD', brand: 'Mitsubishi', price: 2100000, rating: 4.5, reviewCount: 1823, interest: 52, sentiment: { pos: 75, neg: 25 } },
    { id: 'apu09gjaba',   name: '캐리어 인버터 에어컨 APU09GJABA', brand: 'Carrier', price: 890000, rating: 4.2, reviewCount: 4201, interest: 61, sentiment: { pos: 66, neg: 34 } },
  ],
  공기청정기: [
    { id: 'ax90t9420wwd', name: '삼성 블루스카이 AX90T9420WWD', brand: 'Samsung', price: 590000, rating: 4.5, reviewCount: 14302, interest: 76, sentiment: { pos: 77, neg: 23 } },
    { id: 'as95ul5550w0', name: 'LG 퓨리케어 360° AS95UL5550W0', brand: 'LG', price: 720000, rating: 4.6, reviewCount: 11021, interest: 80, sentiment: { pos: 80, neg: 20 } },
    { id: 'blueair-211+', name: 'Blueair Blue Pure 211+', brand: 'Blueair', price: 480000, rating: 4.4, reviewCount: 3820, interest: 64, sentiment: { pos: 74, neg: 26 } },
  ],
  로봇청소기: [
    { id: 'vr50t95735w', name: '삼성 제트봇AI VR50T95735W', brand: 'Samsung', price: 890000, rating: 4.4, reviewCount: 7832, interest: 83, sentiment: { pos: 72, neg: 28 } },
    { id: 'roj9-max-s',  name: '로보락 S8 MaxV Ultra', brand: 'Roborock', price: 1290000, rating: 4.7, reviewCount: 5201, interest: 88, sentiment: { pos: 85, neg: 15 } },
    { id: 'irobot-i7',   name: '아이로봇 룸바 i7+', brand: 'iRobot', price: 790000, rating: 4.3, reviewCount: 6401, interest: 70, sentiment: { pos: 71, neg: 29 } },
  ],
  에어프라이어: [
    { id: 'af-xl2050',   name: '필립스 에어프라이어 HD9270/91', brand: 'Philips', price: 179000, rating: 4.6, reviewCount: 28401, interest: 91, sentiment: { pos: 84, neg: 16 } },
    { id: 'cp-ca250',    name: '코스모스 에어프라이어 CA-250A', brand: 'Cosmos', price: 89000, rating: 4.3, reviewCount: 15802, interest: 77, sentiment: { pos: 73, neg: 27 } },
    { id: 'ninja-4q',    name: '닌자 포디어 듀얼존 AF400EU', brand: 'Ninja', price: 289000, rating: 4.7, reviewCount: 8201, interest: 86, sentiment: { pos: 87, neg: 13 } },
  ],
  전기밥솥: [
    { id: 'crp-jhtr10',  name: '쿠쿠 트윈 프레셔 CRP-JHTR10', brand: 'Cuckoo', price: 390000, rating: 4.7, reviewCount: 31200, interest: 82, sentiment: { pos: 85, neg: 15 } },
    { id: 'np-nvc18',    name: '조지루시 IH압력밥솥 NP-NVC18', brand: 'Zojirushi', price: 520000, rating: 4.8, reviewCount: 9201, interest: 74, sentiment: { pos: 89, neg: 11 } },
  ],
  TV: [
    { id: 'qa65qn900c',  name: '삼성 Neo QLED 8K QA65QN900C', brand: 'Samsung', price: 4890000, rating: 4.7, reviewCount: 4201, interest: 74, sentiment: { pos: 81, neg: 19 } },
    { id: 'oled65c2',    name: 'LG OLED65C2 evo', brand: 'LG', price: 2990000, rating: 4.8, reviewCount: 8301, interest: 88, sentiment: { pos: 88, neg: 12 } },
    { id: 'xr65a80l',    name: 'Sony Bravia XR XR65A80L', brand: 'Sony', price: 3200000, rating: 4.6, reviewCount: 3102, interest: 69, sentiment: { pos: 82, neg: 18 } },
  ],
  가습기: [
    { id: 'dc-cjkn15',   name: '다이슨 가습기 AM10', brand: 'Dyson', price: 890000, rating: 4.4, reviewCount: 5201, interest: 72, sentiment: { pos: 75, neg: 25 } },
    { id: 'wh-h3000s',   name: '웰퍼스 가습기 H3000S', brand: 'Welpers', price: 129000, rating: 4.3, reviewCount: 9801, interest: 64, sentiment: { pos: 70, neg: 30 } },
  ],
  헤어드라이어: [
    { id: 'hd08-bk',     name: '다이슨 슈퍼소닉 HD08', brand: 'Dyson', price: 680000, rating: 4.7, reviewCount: 24100, interest: 90, sentiment: { pos: 86, neg: 14 } },
    { id: 'ep-na98',     name: '파나소닉 나노케어 EH-NA98', brand: 'Panasonic', price: 280000, rating: 4.6, reviewCount: 12401, interest: 81, sentiment: { pos: 83, neg: 17 } },
    { id: 'refe-2100',   name: '레페리 드라이어 RE-FE2100', brand: 'Referi', price: 159000, rating: 4.4, reviewCount: 8201, interest: 73, sentiment: { pos: 77, neg: 23 } },
  ],
}

export function getProductById(id) {
  for (const products of Object.values(MOCK_PRODUCTS)) {
    const found = products.find(p => p.id === id)
    if (found) return found
  }
  return null
}

export function getCategoryByProductId(id) {
  for (const [cat, products] of Object.entries(MOCK_PRODUCTS)) {
    if (products.find(p => p.id === id)) return cat
  }
  return null
}
