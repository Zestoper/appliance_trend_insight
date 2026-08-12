// 네이버 API 점검 모드일 때 백엔드가 내려주는 503 응답 형태를 프론트 전역에서 동일하게 감지한다.
// 백엔드는 HTTPException(status_code=503, detail={"maintenance": true, "message": "..."})를 던지므로
// FastAPI가 감싼 최종 JSON 바디는 { detail: { maintenance: true, message: "..." } } 형태가 된다.
export const DEFAULT_MAINTENANCE_MESSAGE =
  '네이버 정책 변경으로 상품 데이터 연동이 일시 점검 중입니다. 빠르게 정상화하겠습니다.'

export function isNaverMaintenance(data) {
  return !!(data && data.detail && data.detail.maintenance)
}

export function naverMaintenanceMessage(data) {
  return data?.detail?.message || DEFAULT_MAINTENANCE_MESSAGE
}
