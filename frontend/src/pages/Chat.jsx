import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/common/Navbar'
import styles from '../styles/Chat.module.css'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../config'

function renderMarkdown(text) {
  const lines = text.split('\n')
  const elements = []
  let key = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('### ')) {
      elements.push(<h3 key={key++} className={styles.mdH3}>{line.slice(4)}</h3>)
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={key++} className={styles.mdH2}>{line.slice(3)}</h2>)
    } else if (line.startsWith('# ')) {
      elements.push(<h2 key={key++} className={styles.mdH2}>{line.slice(2)}</h2>)
    } else if (/^\d+\.\s/.test(line)) {
      const content = line.replace(/^\d+\.\s/, '')
      elements.push(<div key={key++} className={styles.mdOrderedItem}>{content}</div>)
    } else if (line.startsWith('- ')) {
      elements.push(<div key={key++} className={styles.mdItem}>{line.slice(2)}</div>)
    } else if (line.trim() === '') {
      elements.push(<div key={key++} className={styles.mdSpacer} />)
    } else {
      elements.push(<p key={key++} className={styles.mdP}>{line}</p>)
    }
  }

  return elements
}

function TypingDots() {
  return (
    <div className={styles.typingDots}>
      <span /><span /><span />
    </div>
  )
}

export default function Chat() {
  const navigate = useNavigate()
  const { isLoggedIn, user } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const isB2B = user?.user_type === 'b2b' || user?.role === 'admin'
  const [target, setTarget] = useState(() =>
    (user?.user_type === 'b2b' || user?.role === 'admin') ? 'b2b' : 'b2c'
  )
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send() {
    const query = input.trim()
    if (!query || loading) return

    setMessages(prev => [...prev.slice(-39), { role: 'user', content: query }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/api/insights/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, target, top_k: 8 }),
      })
      const data = await res.json()

      setMessages(prev => [...prev, {
        role: 'ai',
        content: data.report ?? '분석 결과를 가져올 수 없습니다.',
        sources: data.sources ?? [],
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'ai',
        content: '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.',
        sources: [],
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  function handleKeyDown(e) {
    if (e.nativeEvent.isComposing) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className={styles.page}>
      <Navbar />

      <div className={styles.layout}>
        {/* 헤더 */}
        <div className={styles.header}>
          <span className={styles.badge}>AI INSIGHT</span>
          <h1 className={styles.title}>가전 트렌드 AI 분석</h1>
          <p className={styles.subtitle}>제품명이나 카테고리를 입력하면 RAG 기반 리포트를 생성합니다</p>

          <div className={styles.targetToggle}>
            <button
              className={`${styles.targetBtn} ${target === 'b2c' ? styles.targetBtnActive : ''}`}
              onClick={() => setTarget('b2c')}
            >
              소비자 리포트
            </button>
            {isB2B && (
              <button
                className={`${styles.targetBtn} ${target === 'b2b' ? styles.targetBtnActive : ''}`}
                onClick={() => setTarget('b2b')}
              >
                시장 분석 리포트
              </button>
            )}
          </div>
        </div>

        {/* 메시지 영역 */}
        <div className={styles.messages}>
          {messages.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <p className={styles.emptyTitle}>무엇이든 물어보세요</p>
              <p className={styles.emptyDesc}>제품명, 카테고리, 트렌드 키워드를 입력해보세요</p>
              <div className={styles.suggestions}>
                {(target === 'b2c'
                ? ['로봇청소기 실제 후기', '에어컨 여름 구매 타이밍', '비스포크 냉장고 장단점', '공기청정기 어떤 거 살까']
                : ['에어컨 시장 성장 동향', '로봇청소기 소비자 페인포인트', '건조기 신규 진입 기회', '가전 트렌드 타겟 세그먼트']
              ).map(s => (
                  <button key={s} className={styles.suggBtn} onClick={() => setInput(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`${styles.msgRow} ${msg.role === 'user' ? styles.msgRowUser : ''}`}>
              {msg.role === 'ai' && (
                <div className={styles.avatar}>AI</div>
              )}
              <div className={`${styles.bubble} ${msg.role === 'user' ? styles.bubbleUser : styles.bubbleAi}`}>
                {msg.role === 'ai'
                  ? <div className={styles.markdownBody}>{renderMarkdown(msg.content)}</div>
                  : <span>{msg.content}</span>
                }
                {msg.role === 'ai' && msg.sources?.length > 0 && (
                  <details className={styles.sources}>
                    <summary className={styles.sourcesSummary}>참고 문서 {msg.sources.length}개</summary>
                    <ul className={styles.sourcesList}>
                      {msg.sources.map(s => (
                        <li key={s.rank} className={styles.sourceItem}>
                          <span className={styles.sourceRank}>[{s.rank}]</span> {s.text.slice(0, 120)}…
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className={styles.msgRow}>
              <div className={styles.avatar}>AI</div>
              <div className={`${styles.bubble} ${styles.bubbleAi}`}>
                <TypingDots />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* 입력창 */}
        <div className={styles.inputBar}>
          {!isLoggedIn ? (
            <div className={styles.loginGate}>
              <span>로그인 후 AI 분석을 이용할 수 있어요</span>
              <button className={styles.loginBtn} onClick={() => navigate('/login')}>
                로그인하기 →
              </button>
            </div>
          ) : (
            <div className={styles.inputWrap}>
              <textarea
                ref={inputRef}
                className={styles.input}
                placeholder="예: 비스포크 냉장고 장단점, 로봇청소기 인기 브랜드..."
                value={input}
                rows={1}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button
                className={styles.sendBtn}
                onClick={send}
                disabled={!input.trim() || loading}
                aria-label="전송"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
