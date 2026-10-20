import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ShieldAlert } from 'lucide-react';
import styles from '../styles/Login.module.css';
import { API_BASE } from '../config';

// 메일로 받은 링크(/reset-password?token=...)로 들어와 새 비밀번호를 정하는 화면
export default function ResetPassword() {
    const [params] = useSearchParams();
    const token = params.get('token') || '';
    const [valid, setValid] = useState(null);
    const [pw, setPw] = useState('');
    const [pw2, setPw2] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        if (!token) { setValid(false); return; }
        fetch(`${API_BASE}/api/auth/password-reset/check?token=${encodeURIComponent(token)}`)
            .then((r) => r.json())
            .then((d) => setValid(!!d.valid))
            .catch(() => setValid(false));
    }, [token]);

    const mismatch = pw2.length > 0 && pw !== pw2;

    async function handleSubmit(e) {
        e.preventDefault();
        if (pw !== pw2) { setError('새 비밀번호가 서로 다릅니다'); return; }
        setLoading(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/api/auth/password-reset/confirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_password: pw, new_password_confirm: pw2 }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || '변경에 실패했습니다');
            navigate('/login', { state: { message: '비밀번호를 바꿨어요. 새 비밀번호로 로그인해 주세요.' } });
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

                <h1 className={styles.title}>비밀번호 재설정</h1>
                <p className={styles.sub}>새 비밀번호를 8자 이상으로 입력해 주세요</p>

                {valid === null && <p className={styles.sub}>링크를 확인하는 중이에요...</p>}

                {valid === false && (
                    <div className={styles.sentBox}>
                        <ShieldAlert size={34} strokeWidth={1.6} />
                        <p>링크가 만료됐거나 이미 사용됐어요.</p>
                        <Link to="/find-password" className={styles.signupLink}>비밀번호 찾기 다시 요청</Link>
                    </div>
                )}

                {valid && (
                    <form className={styles.form} onSubmit={handleSubmit}>
                        <div className={styles.field}>
                            <input id="new_pw" type="password" className={styles.input} placeholder=" "
                                value={pw} minLength={8} onChange={(e) => setPw(e.target.value)}
                                disabled={loading} autoComplete="new-password" />
                            <label htmlFor="new_pw" className={styles.floatLabel}>새 비밀번호</label>
                        </div>
                        <div className={styles.field}>
                            <input id="new_pw2" type="password" className={styles.input} placeholder=" "
                                value={pw2} minLength={8} onChange={(e) => setPw2(e.target.value)}
                                disabled={loading} autoComplete="new-password" />
                            <label htmlFor="new_pw2" className={styles.floatLabel}>새 비밀번호 확인</label>
                        </div>
                        {(error || mismatch) && <p className={styles.errorMsg}>{error || '비밀번호가 서로 달라요'}</p>}
                        <button type="submit" className={styles.submitBtn} disabled={loading || mismatch || pw.length < 8}>
                            {loading ? <span className={styles.spinner} /> : '비밀번호 바꾸기'}
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
