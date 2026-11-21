import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from '../styles/Login.module.css';
import { API_BASE } from '../config';
import { ArrowRight } from 'lucide-react';

function EyeIcon({ hidden }) {
    return (
        <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            {hidden ? (
                <>
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 2 12 2 12a20.29 20.29 0 0 1 5.06-5.94" />
                    <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 10 8 10 8a20.78 20.78 0 0 1-2.16 3.19" />
                    <path d="M14.12 14.12A3 3 0 0 1 9.88 9.88" />
                    <path d="M1 1l22 22" />
                </>
            ) : (
                <>
                    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
                    <circle cx="12" cy="12" r="3" />
                </>
            )}
        </svg>
    );
}

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [loading, setLoading] = useState(false);

    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const notice = location.state?.message || '';
    // 소셜 로그인이 실패하면 백엔드가 /login?oauth_error=... 로, 콜백 페이지가 state.error 로 알려준다
    const [error, setError] = useState(
        new URLSearchParams(location.search).get('oauth_error') || location.state?.error || ''
    );

    async function handleSubmit(e) {
        e.preventDefault();
        if (!email || !password) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
                // 서버가 재시작·배포 중이면 응답이 안 와서 버튼이 끝없이 돌았다 → 30초 뒤 오류 안내
                signal: AbortSignal.timeout(30000),
            });
            const data = await res.json();
            if (!res.ok) {
                if (data.detail === 'PENDING') {
                    setError('관리자 승인 대기 중입니다. 승인 후 로그인이 가능합니다.');
                } else {
                    setError(data.detail || '로그인에 실패했습니다');
                }
                return;
            }
            login(data.token, {
                user_type: data.user_type,
                nickname: data.nickname || '',
                company_name: data.company_name || '',
                email,
                role: data.role || 'user',
                status: data.status || 'active',
                tier: data.tier || 'free',
                tier_expires_at: data.tier_expires_at || null,
            });
            navigate(data.role === 'admin' ? '/admin' : '/');
        } catch {
            setError('서버에 연결할 수 없습니다. 서버가 깨어나는 중일 수 있으니 잠시 후 다시 시도해주세요.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className={styles.page}>
            <div className={styles.blobWrap}>
                <div className={`${styles.blob} ${styles.blobIndigo}`} />
                <div className={`${styles.blob} ${styles.blobPurple}`} />
            </div>

            <div className={styles.card}>
                <div className={styles.logo} onClick={() => navigate('/')}>
                    <div className={styles.logoIcon}>A</div>
                    <span className={styles.logoText}>가전무쌍</span>
                </div>

                <h1 className={styles.title}>로그인</h1>
                <p className={styles.sub}>가전 트렌드 인사이트를 확인하세요</p>

                <form className={styles.form} onSubmit={handleSubmit}>
                    <div className={styles.field}>
                        <input
                            id="email"
                            type="email"
                            className={styles.input}
                            placeholder=" "
                            value={email}
                            onChange={(e) => {
                                setEmail(e.target.value);
                                setError('');
                            }}
                            disabled={loading}
                        />
                        <label htmlFor="email" className={styles.floatLabel}>
                            이메일
                        </label>
                    </div>

                    <div className={styles.field}>
                        <input
                            id="password"
                            type={showPw ? 'text' : 'password'}
                            className={styles.input}
                            placeholder=" "
                            value={password}
                            onChange={(e) => {
                                setPassword(e.target.value);
                                setError('');
                            }}
                            style={{ paddingRight: '44px' }}
                            disabled={loading}
                        />
                        <label htmlFor="password" className={styles.floatLabel}>
                            비밀번호
                        </label>
                        <button type="button" className={styles.eyeBtn} onClick={() => setShowPw((v) => !v)}>
                            <EyeIcon hidden={!showPw} />
                        </button>
                    </div>

                    <p className={styles.findRow}>
                        <Link to="/find-password" className={styles.findLink}>비밀번호를 잊으셨나요?</Link>
                    </p>

                    {notice && !error && <p className={styles.successMsg}>{notice}</p>}
                    {error && <p className={styles.errorMsg}>{error}</p>}

                    <button type="submit" className={styles.submitBtn} disabled={loading || !email || !password}>
                        {loading ? <span className={styles.spinner} /> : '로그인'}
                    </button>
                </form>

                <div className={styles.socialDivider}><span>또는</span></div>

                <div className={styles.socialRow}>
                    <a href={`${API_BASE}/api/auth/kakao/login`} className={`${styles.socialBtn} ${styles.kakaoBtn}`}>
                        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
                            <path fill="currentColor" d="M12 3C6.48 3 2 6.58 2 11c0 2.85 1.86 5.35 4.66 6.77l-.95 3.48c-.08.3.26.54.52.37l4.16-2.75c.53.07 1.06.11 1.61.11 5.52 0 10-3.58 10-8S17.52 3 12 3z" />
                        </svg>
                        카카오로 시작하기
                    </a>
                    <a href={`${API_BASE}/api/auth/google/login`} className={`${styles.socialBtn} ${styles.googleBtn}`}>
                        <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                        </svg>
                        Google로 시작하기
                    </a>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', margin: '10px 0 0', lineHeight: 1.6 }}>
                    카카오 · Google로 처음 시작하면 <Link to="/terms" target="_blank">이용약관</Link>과{' '}
                    <Link to="/privacy" target="_blank">개인정보 수집 · 이용</Link>에 동의하는 것으로 봅니다
                </p>

                <p className={styles.signupRow}>
                    계정이 없으신가요?&nbsp;
                    <Link to="/signup" className={styles.signupLink}>
                        회원가입
                    </Link>
                </p>

                <button type="button" className={styles.ctaBtn} onClick={() => navigate('/')}>
                   뒤로가기 <ArrowRight size="1em" />
                </button>
            </div>
        </div>
    );
}
