import { useState, useEffect } from 'react'
import { API_BASE } from '../config'

const cache = {}

export function useProductImage(query) {
  // 캐시에 이미 있으면 바로 그 값으로 시작, 없으면 null
  const [image, setImage] = useState(cache[query] ?? null)
  // 캐시에 없으면 로딩 중(true), 있으면 이미 가져온 것(false)
  const [loading, setLoading] = useState(!cache[query])

  useEffect(() => {
    // 이미 캐시에 저장된 값이 있으면 API 재호출 없이 바로 종료
    if (cache[query] !== undefined) {
      setImage(cache[query])
      setLoading(false)
      return
    }

    // 컴포넌트가 사라졌는지 추적하는 플래그
    // (API 응답이 느릴 때 이미 사라진 컴포넌트에 setState 하는 걸 막기 위해)
    let cancelled = false
    setLoading(true)

    fetch(`${API_BASE}/api/naver/product-image?query=${encodeURIComponent(query)}`)
      // 1단계: HTTP 응답 → JSON으로 파싱 ({ image: "https://..." })
      .then(r => r.json())
      // 2단계: 파싱된 data 처리
      .then(data => {
        // 사용자가 페이지를 떠나서 컴포넌트가 이미 사라진 경우 → 아무것도 안 함
        if (cancelled) return
        // 결과를 캐시에 저장 (다음번엔 API 안 부름)
        cache[query] = data.image ?? null
        // 이미지 상태 업데이트 → 카드에 이미지 표시됨
        setImage(cache[query])
        setLoading(false)
      })
      // API 실패해도 로딩만 끄고 이미지 없는 상태로 처리 (앱 안 터지게)
      .catch(() => {
        if (!cancelled) {
          cache[query] = null
          setLoading(false)
        }
      })

    // 클린업 함수: 컴포넌트가 언마운트될 때 자동 실행됨
    // cancelled = true 로 바꿔서 위의 .then() 이 실행돼도 setState 못 하게 차단
    return () => { cancelled = true }
  }, [query])

  return { image, loading }
}
