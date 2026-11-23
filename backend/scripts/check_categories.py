"""품목 인식 점검 — 상품명 목록을 실제 다나와와 함께 돌려 어떤 품목으로 잡히는지 본다.
사용: cd backend && python3 -m scripts.check_categories"""
import asyncio
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault("JWT_SECRET", "check-script-only")   # 로그인 기능을 안 쓰는 점검용 (서버 import에 필요할 뿐)

NAMES = """삼성 비스포크 제트 AI 무선청소기 VS28C973DRG
LG 코드제로 A9S 오브제컬렉션 AO9571
삼성 비스포크 제트봇 AI VR7MD97716G
로보락 S8 MaxV Ultra
에코백스 디봇 X2 옴니
다이슨 V15 디텍트 컴플리트
삼성 비스포크 그랑데 AI WF24B9600KE
LG 퓨리케어 오브제컬렉션 360 AS353NS3A
삼성 블루스카이 5500 AX060CG500G
LG 퓨리케어 정수기 WD523ACB
SK매직 인덕션 IHR-B310E
LG 디오스 BEI3GQUO
삼성 비스포크 큐커 MO22A7797CW
LG 디오스 광파오븐 MLJ32ERW
삼성 네오 QLED KQ65QND90AFXKR
LG 올레드 evo OLED65C4KNA
LG 스탠바이미2 32LX6BPGA
LG 슈드레서 SH3BS
LG전자 오브제컬렉션 뉴 스타일러 SC5MBR5ES
쿠쿠 트윈프레셔 CRP-RT1010FD
LG 디오스 오브제컬렉션 노크온 S834BW12
LG 퓨리케어 하이드로타워 HY703RWLA
드롱기 데디카 EC685
아이폰 16 프로""".splitlines()


async def main():
    from app.routers.b2b_search_analysis import detect_category, product_key_for
    for n in NAMES:
        model, _ = product_key_for(n)
        try:
            cat = await detect_category(n, "", model)
        except Exception as e:
            cat = f"오류 {type(e).__name__}"
        print(f"{str(cat):10} | {n}")
        await asyncio.sleep(0.5)

asyncio.run(main())
