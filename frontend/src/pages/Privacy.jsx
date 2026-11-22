import { Link } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import s from '../styles/Legal.module.css'
import { LEGAL } from '../legal/legalInfo'

// 개인정보처리방침 — 웹과 안드로이드 앱이 같은 주소(/privacy)를 쓴다 (스토어 등록용 URL)
// 실제로 저장하는 항목은 backend 코드(users · user_b2c_profiles · user_b2b_profiles · price_alert · payments ·
// user_social_accounts · password_resets 테이블) 기준으로 적었다. 저장 항목이 바뀌면 여기도 고친다.
export default function Privacy() {
  const { service, operator, privacyOfficer, privacyManager, contactEmail, effectiveDate } = LEGAL
  return (
    <div className={s.page}>
      <Navbar />
      <div className={s.inner}>
        <h1 className={s.title}>개인정보처리방침</h1>
        <p className={s.meta}>시행일 {effectiveDate}</p>

        <p>
          {operator}(이하 '운영자')는 {service} 웹사이트와 안드로이드 앱(이하 '서비스')을 이용하는 분의
          개인정보를 「개인정보 보호법」에 따라 보호하고 관련 문의를 신속하게 처리하기 위해 다음과 같이
          개인정보처리방침을 둡니다.
        </p>

        <h2>1. 수집하는 개인정보 항목과 목적</h2>
        <table className={s.table}>
          <thead>
            <tr><th>구분</th><th>항목</th><th>목적</th></tr>
          </thead>
          <tbody>
            <tr>
              <td>이메일 회원가입 (필수)</td>
              <td>이메일 · 비밀번호(암호화 저장) · 닉네임</td>
              <td>회원 식별 · 로그인 · 비밀번호 재설정</td>
            </tr>
            <tr>
              <td>기업(B2B) 회원가입 (필수)</td>
              <td>이메일 · 비밀번호(암호화 저장) · 회사명 · 업종 · 담당자 연락처</td>
              <td>기업 회원 확인 · 승인 · 서비스 안내</td>
            </tr>
            <tr>
              <td>카카오 · 구글 로그인</td>
              <td>소셜 서비스 회원 번호 · 이메일(동의한 경우) · 닉네임</td>
              <td>소셜 계정으로 로그인 · 회원 식별</td>
            </tr>
            <tr>
              <td>가격 알림 (선택)</td>
              <td>알림을 받을 제품명 · 목표 가격</td>
              <td>목표 가격 도달 시 알림 제공</td>
            </tr>
            <tr>
              <td>유료 구독 결제 (선택)</td>
              <td>주문 번호 · 구독 등급 · 결제 금액 · 결제 상태</td>
              <td>결제 처리 · 구독 관리 · 환불</td>
            </tr>
            <tr>
              <td>자동 수집</td>
              <td>접속 기록(서버 로그) · 기기의 화면 설정(다크모드 등)</td>
              <td>오류 확인 · 보안 · 서비스 개선</td>
            </tr>
          </tbody>
        </table>
        <p>
          카드 번호 등 결제 수단 정보는 결제대행사(토스페이먼츠)가 직접 처리하며 운영자는 저장하지 않습니다.
          앱에서 제품 라벨 사진의 글자를 읽는 기능은 기기 안에서만 처리되며 사진은 서버로 전송되거나 저장되지 않습니다.
        </p>

        <h2>2. 보유 및 이용 기간</h2>
        <p>
          회원 탈퇴 시 개인정보를 지체 없이 삭제합니다. 탈퇴는 웹 마이페이지 또는 앱 설정에서 직접 할 수 있습니다.
          다만 관계 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다.
        </p>
        <ul>
          <li>대금 결제 및 재화 등의 공급에 관한 기록: 5년 (전자상거래 등에서의 소비자보호에 관한 법률) — 탈퇴 시 회원 정보와 연결을 끊고 결제 내역만 보관</li>
          <li>서비스 접속 기록: 3개월 (통신비밀보호법)</li>
          <li>비밀번호 재설정 링크: 발급 후 만료 시까지 (사용하거나 만료되면 삭제)</li>
        </ul>

        <h2>3. 개인정보의 제3자 제공</h2>
        <p>운영자는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 법령에 특별한 규정이 있는 경우는 예외로 합니다.</p>

        <h2>4. 개인정보 처리 위탁 및 국외 이전</h2>
        <p>서비스 운영을 위해 다음 업체에 개인정보 처리를 맡기고 있습니다.</p>
        <table className={s.table}>
          <thead>
            <tr><th>업체</th><th>위탁 업무</th><th>처리 위치</th></tr>
          </thead>
          <tbody>
            <tr><td>Supabase</td><td>회원 정보 데이터베이스 보관</td><td>대한민국(서울 리전)</td></tr>
            <tr><td>Render</td><td>서버 운영 · 접속 기록</td><td>미국</td></tr>
            <tr><td>Vercel</td><td>웹사이트 제공</td><td>미국 등</td></tr>
            <tr><td>토스페이먼츠</td><td>결제 처리</td><td>대한민국</td></tr>
            <tr><td>이메일 발송 서비스(Google 또는 Resend)</td><td>인증코드 · 비밀번호 재설정 메일 발송</td><td>미국</td></tr>
            <tr><td>Groq · Google(Gemini)</td><td>AI 분석 · 상담 답변 생성 (입력한 질문 내용만 전달하며 저장하지 않음)</td><td>미국</td></tr>
          </tbody>
        </table>
        <p>
          국외 업체로는 서비스 이용 시 네트워크를 통해 전송되며 각 업체의 보안 기준에 따라 보호됩니다.
          AI 상담에는 이름 · 연락처 같은 개인정보를 입력하지 않도록 안내합니다.
        </p>

        <h2>5. 이용자의 권리</h2>
        <p>
          이용자는 언제든지 자신의 개인정보를 조회 · 수정 · 삭제하거나 처리 정지를 요청할 수 있습니다.
          마이페이지에서 직접 하거나 아래 연락처로 요청하면 지체 없이 처리합니다.
        </p>

        <h2>6. 개인정보의 파기</h2>
        <p>
          보유 기간이 끝나거나 목적이 달성된 개인정보는 데이터베이스에서 복구할 수 없는 방법으로 삭제합니다.
        </p>

        <h2>7. 안전성 확보 조치</h2>
        <ul>
          <li>비밀번호는 bcrypt로 암호화해 저장하며 운영자도 원래 비밀번호를 알 수 없습니다.</li>
          <li>모든 통신은 HTTPS로 암호화됩니다.</li>
          <li>데이터베이스 접근 권한은 운영자로 제한합니다.</li>
        </ul>

        <h2>8. 쿠키 등 자동 수집 장치</h2>
        <p>
          웹사이트는 로그인 상태와 화면 설정을 기억하기 위해 브라우저 저장소(localStorage)를 사용하며
          광고 목적의 쿠키나 추적 도구는 사용하지 않습니다. 브라우저 설정에서 언제든 지울 수 있습니다.
        </p>

        <h2>9. 만 14세 미만 아동</h2>
        <p>서비스는 만 14세 미만 아동의 회원가입을 받지 않습니다.</p>

        <h2>10. 개인정보 보호책임자 및 담당자</h2>
        <ul>
          <li>책임자: {privacyOfficer}</li>
          {privacyManager && <li>담당자: {privacyManager}</li>}
          <li>연락처: <a href={`mailto:${contactEmail}`}>{contactEmail}</a></li>
        </ul>
        <p>
          개인정보 침해에 대한 신고나 상담은 개인정보침해신고센터(privacy.kisa.or.kr · 국번 없이 118)
          개인정보분쟁조정위원회(www.kopico.go.kr · 1833-6972)에 문의할 수 있습니다.
        </p>

        <h2>11. 방침의 변경</h2>
        <p>이 방침이 바뀌면 시행 7일 전부터 서비스 공지로 알립니다.</p>

        <p className={s.links}>
          <Link to="/terms">이용약관</Link>
          <Link to="/">홈으로</Link>
        </p>
      </div>
    </div>
  )
}
