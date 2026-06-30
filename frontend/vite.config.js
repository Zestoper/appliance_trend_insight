import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // build.cssTarget이 비어있으면 lightningcss minifier가 빈 targets({})로
    // 동작해 `@media (max-width:800px)`를 최신 range 문법(`width<=800px`)으로
    // 바꿔버린다. 이 문법은 iOS 16.4 미만 Safari에서 인식되지 않아 @media 블록
    // 전체가 무시되며 모바일 반응형이 통째로 깨진다. 구형 Safari를 명시해
    // range 문법으로의 변환을 막는다.
    cssTarget: ['safari12', 'ios12'],
  },
  server: {
    host: true,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
