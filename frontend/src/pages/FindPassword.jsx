import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, MailCheck } from 'lucide-react';
import styles from '../styles/Login.module.css';
import { API_BASE } from '../config';

// 비밀번호 찾기 — 가입 이메일로 30분·1회용 재설정 링크를 보낸다 (가입 여부는 화면에 드러내지 않음)
export default function FindPassword() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    async function handleSubmit(e) {
        e.preventDefault();
        if (!email) return;
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/api/auth/password-reset/request`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '요청에 실패했습니다');
            setSent(data.message);
        } catch (err) {
            setError(err.message === 'Failed to fetch' ? '서버에 연결할 수 없습니다' : err.message);
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

                <h1 className={styles.title}>비밀번호 찾기</h1>
                <p className={styles.sub}>가입한 이메일로 재설정 링크를 보내 드려요</p>

                {sent ? (
                    <div className={styles.sentBox}>
                        <MailCheck size={34} strokeWidth={1.6} />
                        <p>{sent}</p>
                        <p className={styles.sentSub}>링크는 30분 동안 한 번만 쓸 수 있어요.</p>
                    </div>
                ) : (
                    <form className={styles.form} onSubmit={handleSubmit}>
                        <div className={styles.field}>
                            <input
                                id="email"
                                type="email"
                                className={styles.input}
                                placeholder=" "
                                value={email}
                                onChange={(e) => { setEmail(e.target.value); setError(''); }}
                                disabled={loading}
                                autoComplete="email"
                            />
                            <label htmlFor="email" className={styles.floatLabel}>가입 이메일</label>
                        </div>
                        {error && <p className={styles.errorMsg}>{error}</p>}
                        <button type="submit" className={styles.submitBtn} disabled={loading || !email}>
                            {loading ? <span className={styles.spinner} /> : '재설정 링크 받기'}
                        </button>
                    </form>
                )}

                <p className={styles.signupRow}>
                    <Link to="/login" className={styles.signupLink} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
                        <ArrowLeft size={16} /> 로그인으로 돌아가기
                    </Link>
                </p>
            </div>
        </div>
    );
}
