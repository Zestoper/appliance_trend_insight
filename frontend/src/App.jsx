import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import Home from './pages/Home'
import Login from './pages/Login'
import Signup from './pages/Signup'
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
import B2BDashboard from './pages/B2BDashboard'
import B2BPrice from './pages/B2BPrice'
import B2BReport from './pages/B2BReport'
import B2BForecast from './pages/B2BForecast'
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
            <Route path="/b2b/dashboard"     element={<B2BDashboard />} />
            <Route path="/b2b/price"         element={<B2BPrice />} />
            <Route path="/b2b/report"        element={<B2BReport />} />
            <Route path="/b2b/forecast"      element={<B2BForecast />} />
            <Route path="/chat"              element={<Chat />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
