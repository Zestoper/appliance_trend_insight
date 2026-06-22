import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from '../styles/Login.module.css';
import { API_BASE } from '../config';

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
    const [error, setError] = useState('');

    const { login } = useAuth();
    const navigate = useNavigate();

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
            });
            navigate(data.role === 'admin' ? '/admin' : '/');
        } catch {
            setError('서버에 연결할 수 없습니다');
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

                    {error && <p className={styles.errorMsg}>{error}</p>}

                    <button type="submit" className={styles.submitBtn} disabled={loading || !email || !password}>
                        {loading ? <span className={styles.spinner} /> : '로그인'}
                    </button>
                </form>

                <p className={styles.signupRow}>
                    계정이 없으신가요?&nbsp;
                    <Link to="/signup" className={styles.signupLink}>
                        회원가입
                    </Link>
                </p>

                <button type="button" className={styles.ctaBtn} onClick={() => navigate('/')}>
                    뒤로가기 →
                </button>
            </div>
        </div>
    );
}
