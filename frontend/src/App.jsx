import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import Home from './pages/Home'
import Login from './pages/Login'
import Signup from './pages/SignUp'
import SignupPending from './pages/SignupPending'
import ProductList from './pages/ProductList'
import ProductReport from './pages/ProductReport'
import Compare from './pages/Compare'
import Timing from './pages/Timing'
import Recommend from './pages/Recommend'
import Trend from './pages/Trend'
import Admin from './pages/Admin'
import MyPage from './pages/MyPage'
import B2BHome from './pages/B2BHome'
import B2BAnalysis from './pages/B2BAnalysis'
import B2BPricing from './pages/B2BPricing'
import PaymentSuccess from './pages/PaymentSuccess'
import PaymentFail from './pages/PaymentFail'
import Chat from './pages/Chat'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/"                  element={<Home />} />
            <Route path="/home"              element={<Home />} />
            <Route path="/login"             element={<Login />} />
            <Route path="/signup"            element={<Signup />} />
            <Route path="/signup/pending"   element={<SignupPending />} />
            <Route path="/products/:category" element={<ProductList />} />
            <Route path="/report/:productId" element={<ProductReport />} />
            <Route path="/compare"           element={<Compare />} />
            <Route path="/timing"            element={<Timing />} />
            <Route path="/recommend"         element={<Recommend />} />
            <Route path="/trend"             element={<Trend />} />
            <Route path="/admin"             element={<Admin />} />
            <Route path="/mypage"            element={<MyPage />} />
            <Route path="/b2b"               element={<B2BHome />} />
            <Route path="/b2b/analysis"      element={<B2BAnalysis />} />
            <Route path="/b2b/pricing"       element={<B2BPricing />} />
            <Route path="/b2b/payments/success" element={<PaymentSuccess />} />
            <Route path="/b2b/payments/fail"     element={<PaymentFail />} />
            <Route path="/chat"              element={<Chat />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
