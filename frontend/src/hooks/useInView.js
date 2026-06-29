import { useCallback, useEffect, useRef, useState } from 'react'

export function useInView(options = {}) {
  const { threshold = 0.15, once = false } = options
  const [node, setNode] = useState(null)
  const [inView, setInView] = useState(false)
  const observerRef = useRef(null)

  const ref = useCallback(el => setNode(el), [])

  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect()
    if (!node) return

    observerRef.current = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) observerRef.current?.disconnect()
        } else if (!once) {
          setInView(false)
        }
      },
      { threshold }
    )

    observerRef.current.observe(node)
    return () => observerRef.current?.disconnect()
  }, [node, threshold, once])

  return { ref, inView }
}
