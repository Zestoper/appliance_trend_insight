import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from '../styles/B2CDashboard.module.css';

import B2CDashboardMain from '../components/dashboard/b2c/B2CDashboardMain';
import B2CTrendAnalysis from '../components/dashboard/b2c/B2CTrendAnalysis';
import B2CProductCompare from '../components/dashboard/b2c/B2CProductCompare';
import B2CPurchaseTiming from '../components/dashboard/b2c/B2CPurchaseTiming';
import B2CAIRecommend from '../components/dashboard/b2c/B2CAIRecommend';
import B2CSentimentAnalysis from '../components/dashboard/b2c/B2CSentimentAnalysis';
import B2CPriceAlert from '../components/dashboard/b2c/B2CPriceAlert';

export default function B2CDashboard() {
    const navigate = useNavigate();
    const [activeMenu, setActiveMenu] = useState('dashboard');

    return (
        <div className={styles.page}>
            <aside className={styles.sidebar}>
                <div className={styles.logo} onClick={() => navigate('/')}>
                    <span className={styles.logoIcon}>A</span>
                    <span>APPLENS</span>
                </div>

                <nav className={styles.menu}>
                    <button
                        className={activeMenu === 'dashboard' ? styles.active : ''}
                        onClick={() => setActiveMenu('dashboard')}
                    >
                        대시보드
                    </button>

                    <button
                        className={activeMenu === 'trend' ? styles.active : ''}
                        onClick={() => setActiveMenu('trend')}
                    >
                        트렌드 분석
                    </button>

                    <button
                        className={activeMenu === 'compare' ? styles.active : ''}
                        onClick={() => setActiveMenu('compare')}
                    >
                        제품 비교
                    </button>

                    <button
                        className={activeMenu === 'timing' ? styles.active : ''}
                        onClick={() => setActiveMenu('timing')}
                    >
                        구매 타이밍
                    </button>

                    <button
                        className={activeMenu === 'recommend' ? styles.active : ''}
                        onClick={() => setActiveMenu('recommend')}
                    >
                        AI 추천
                    </button>

                    <button
                        className={activeMenu === 'sentiment' ? styles.active : ''}
                        onClick={() => setActiveMenu('sentiment')}
                    >
                        감성 분석
                    </button>
                    
                    <button
                        className={activeMenu === 'alert' ? styles.active : ''}
                        onClick={() => setActiveMenu('alert')}
                    >
                        가격 알림
                    </button>
                </nav>
            </aside>

            <main className={styles.main}>
                {activeMenu === 'dashboard' && <B2CDashboardMain />}
                {activeMenu === 'trend' && <B2CTrendAnalysis />}
                {activeMenu === 'compare' && <B2CProductCompare />}
                {activeMenu === 'timing' && <B2CPurchaseTiming />}
                {activeMenu === 'recommend' && <B2CAIRecommend />}
                {activeMenu === 'sentiment' && <B2CSentimentAnalysis />}
                {activeMenu === 'alert' && <B2CPriceAlert />}
            </main>
        </div>
    );
}
