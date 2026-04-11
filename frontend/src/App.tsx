/**
 * 主应用组件
 * 配置React Router路由和全局布局
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import StrategyOverview from './pages/StrategyOverview'
import BacktestDashboard from './pages/BacktestDashboard'
import ModelAnalysis from './pages/ModelAnalysis'
import FactorExplorer from './pages/FactorExplorer'
import AIRecommendation from './pages/AIRecommendation'
import ShadowAccount from './pages/ShadowAccount'
import StockPool from './pages/StockPool'
import './index.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/strategy" replace />} />
          <Route path="strategy" element={<StrategyOverview />} />
          <Route path="backtest" element={<BacktestDashboard />} />
          <Route path="model" element={<ModelAnalysis />} />
          <Route path="factors" element={<FactorExplorer />} />
          <Route path="stockpool" element={<StockPool />} />
          <Route path="ai" element={<AIRecommendation />} />
          <Route path="account" element={<ShadowAccount />} />
          <Route path="*" element={<Navigate to="/strategy" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
