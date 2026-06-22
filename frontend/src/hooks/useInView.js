import { useEffect, useRef, useState } from 'react'

// 요소가 뷰포트에 들어오면 true를 반환하는 훅
// threshold: 요소가 몇 % 보여야 트리거할지 (0.15 = 15%)
// once: true면 한 번만 트리거 (스크롤 올려도 다시 안 사라짐)
export function useInView(options = {}) {
  const { threshold = 0.15, once = false } = options
  const ref = useRef(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) observer.disconnect()
        } else if (!once) {
          setInView(false)
        }
      },
      { threshold }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold, once])

  return { ref, inView }
}
