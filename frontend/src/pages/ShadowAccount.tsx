/**
 * 影子账户页面
 * 管理影子账户、持仓、时间范围设置
 * 
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useEffect, useCallback } from 'react'
import { useAppStore } from '../store/useAppStore'
import { accountService } from '../services/account'
import { ScrollReveal, RippleButton } from '../components/motion'

/**
 * 毛玻璃卡片样式
 */
const glassCardStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.85)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: '24px',
  border: '1px solid rgba(255, 255, 255, 0.5)',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.03), 0 6px 12px rgba(0, 0, 0, 0.02)',
  transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
}

/**
 * 按钮样式
 */
const buttonStyle = (variant: 'primary' | 'secondary' | 'danger' = 'primary'): React.CSSProperties => ({
  padding: '10px 20px',
  borderRadius: '980px',
  fontSize: '14px',
  fontWeight: 500,
  border: 'none',
  cursor: 'pointer',
  transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
  background: variant === 'primary' ? '#0071E3' : variant === 'danger' ? 'rgba(255, 59, 48, 0.1)' : 'rgba(0, 0, 0, 0.04)',
  color: variant === 'primary' ? '#FFFFFF' : variant === 'danger' ? '#FF3B30' : '#86868B',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
})

interface Position {
  code: string
  quantity: number
  cost_price: number
  current_price?: number
}

function ShadowAccount() {
  const { accountName, setAccountName } = useAppStore()
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newAccountName, setNewAccountName] = useState('')
  const [showAddPositionModal, setShowAddPositionModal] = useState(false)
  const [newPosition, setNewPosition] = useState({ code: '', quantity: 0, cost_price: 0, current_price: 0 })
  const [backtestRange, setBacktestRange] = useState({ start: '2020-01-01', end: '2024-12-31' })
  const [predictionRange, setPredictionRange] = useState({ start: '2025-01-01', end: '2025-03-31' })
  const [aiAdviceHistory] = useState<Array<{ timestamp: string; content: string }>>([])

  const loadAccountInfo = useCallback(async () => {
    if (!accountName) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      // 从本地存储加载
      const saved = localStorage.getItem(`shadow_account_${accountName}`)
      if (saved) {
        const data = JSON.parse(saved)
        setPositions(data.positions || [])
        setBacktestRange(data.backtestRange || { start: '2020-01-01', end: '2024-12-31' })
        setPredictionRange(data.predictionRange || { start: '2025-01-01', end: '2025-03-31' })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载账户信息失败')
    } finally {
      setLoading(false)
    }
  }, [accountName])

  useEffect(() => {
    loadAccountInfo()
  }, [loadAccountInfo])

  const handleCreateAccount = async () => {
    if (!newAccountName.trim()) return
    try {
      await accountService.createAccount(newAccountName.trim())
      setAccountName(newAccountName.trim())
      setShowCreateModal(false)
      setNewAccountName('')
      // 初始化本地存储
      localStorage.setItem(`shadow_account_${newAccountName.trim()}`, JSON.stringify({
        positions: [],
        backtestRange: { start: '2020-01-01', end: '2024-12-31' },
        predictionRange: { start: '2025-01-01', end: '2025-03-31' },
      }))
      setPositions([])
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建账户失败')
    }
  }

  const handleAddPosition = async () => {
    if (!accountName || !newPosition.code) return
    const updatedPositions = [...positions, { ...newPosition }]
    setPositions(updatedPositions)
    // 保存到本地存储
    const saved = localStorage.getItem(`shadow_account_${accountName}`)
    const data = saved ? JSON.parse(saved) : {}
    localStorage.setItem(`shadow_account_${accountName}`, JSON.stringify({
      ...data,
      positions: updatedPositions,
    }))
    setShowAddPositionModal(false)
    setNewPosition({ code: '', quantity: 0, cost_price: 0, current_price: 0 })
  }

  const handleRemovePosition = async (code: string) => {
    if (!accountName) return
    const updatedPositions = positions.filter(p => p.code !== code)
    setPositions(updatedPositions)
    // 保存到本地存储
    const saved = localStorage.getItem(`shadow_account_${accountName}`)
    const data = saved ? JSON.parse(saved) : {}
    localStorage.setItem(`shadow_account_${accountName}`, JSON.stringify({
      ...data,
      positions: updatedPositions,
    }))
  }

  const handleSaveSettings = async () => {
    if (!accountName) return
    // 保存到本地存储
    const saved = localStorage.getItem(`shadow_account_${accountName}`)
    const data = saved ? JSON.parse(saved) : {}
    localStorage.setItem(`shadow_account_${accountName}`, JSON.stringify({
      ...data,
      backtestRange,
      predictionRange,
    }))
    alert('设置已保存')
  }

  const calculateTotalValue = () => {
    return positions.reduce((sum, pos) => sum + pos.quantity * pos.cost_price, 0)
  }

  const calculateProfit = () => {
    return positions.reduce((sum, pos) => sum + (pos.current_price ? pos.quantity * (pos.current_price - pos.cost_price) : 0), 0)
  }

  const calculateReturn = () => {
    const totalCost = positions.reduce((sum, pos) => sum + pos.quantity * pos.cost_price, 0)
    const profit = calculateProfit()
    return totalCost > 0 ? (profit / totalCost) * 100 : 0
  }

  if (!accountName) {
    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '60px 24px 80px' }}>
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontSize: '40px', fontWeight: 600, color: '#1D1D1F', marginBottom: '8px', letterSpacing: '-0.02em' }}>
            影子账户
          </h1>
          <p style={{ fontSize: '15px', color: '#86868B' }}>
            管理您的虚拟投资组合
          </p>
        </div>

        <div style={{ maxWidth: '640px' }}>
          <div style={{ ...glassCardStyle, padding: '32px', textAlign: 'center' }}>
            <div style={{ width: '80px', height: '80px', borderRadius: '24px', background: 'rgba(0, 113, 227, 0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#0071E3" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h3 style={{ fontSize: '20px', fontWeight: 600, color: '#1D1D1F', marginBottom: '12px' }}>
              创建您的影子账户
            </h3>
            <p style={{ fontSize: '14px', color: '#86868B', lineHeight: 1.7, marginBottom: '24px' }}>
              影子账户让您可以模拟真实交易，测试策略效果，而无需承担实际资金风险
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              style={{
                ...buttonStyle('primary'),
                boxShadow: '0 4px 20px rgba(0, 113, 227, 0.3)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.02)'
                e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 113, 227, 0.4)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)'
                e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 113, 227, 0.3)'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              创建账户
            </button>
          </div>
        </div>

        {showCreateModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
            <div style={{ ...glassCardStyle, padding: '32px', width: '100%', maxWidth: '400px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#1D1D1F', marginBottom: '20px' }}>创建新账户</h3>
              <input
                type="text"
                value={newAccountName}
                onChange={(e) => setNewAccountName(e.target.value)}
                placeholder="输入账户名称"
                style={{
                  width: '100%',
                  border: '1px solid #E8E8ED',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  fontSize: '14px',
                  marginBottom: '20px',
                  outline: 'none',
                }}
              />
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => setShowCreateModal(false)}
                  style={buttonStyle('secondary')}
                >
                  取消
                </button>
                <button
                  onClick={handleCreateAccount}
                  style={buttonStyle('primary')}
                >
                  创建
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="page-container">
      <ScrollReveal index={0}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
        <div>
          <h1 className="page-title">影子账户</h1>
          <p style={{ fontSize: '15px', color: 'var(--color-text-subtle)' }}>
            当前账户：<span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>{accountName}</span>
          </p>
        </div>
        <RippleButton variant="secondary" onClick={() => setShowCreateModal(true)}>
          切换账户
        </RippleButton>
      </div>
      </ScrollReveal>

      {error && (
        <div style={{ ...glassCardStyle, padding: '16px 20px', marginBottom: '24px', background: 'rgba(255, 59, 48, 0.08)' }}>
          <p style={{ fontSize: '14px', color: '#FF3B30' }}>{error}</p>
        </div>
      )}

      {/* 账户概览卡片 */}
      <div style={{ ...glassCardStyle, marginBottom: '24px' }}>
        <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
          账户概览
        </div>
        <div style={{ padding: '32px' }}>
          {loading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} style={{ padding: '20px', background: '#F5F5F7', borderRadius: '12px' }}>
                  <div style={{ height: '12px', width: '60px', background: '#E8E8ED', borderRadius: '4px', marginBottom: '8px' }}></div>
                  <div style={{ height: '28px', width: '100px', background: '#E8E8ED', borderRadius: '4px' }}></div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <MetricCard label="总资产" value={`¥${(calculateTotalValue() + calculateProfit()).toLocaleString()}`} color="#1D1D1F" />
              <MetricCard label="持仓市值" value={`¥${calculateTotalValue().toLocaleString()}`} color="#0071E3" />
              <MetricCard label="总盈亏" value={`${calculateProfit() >= 0 ? '+' : ''}¥${calculateProfit().toLocaleString()}`} color={calculateProfit() >= 0 ? '#34C759' : '#FF3B30'} />
              <MetricCard label="收益率" value={`${calculateReturn() >= 0 ? '+' : ''}${calculateReturn().toFixed(2)}%`} color={calculateReturn() >= 0 ? '#34C759' : '#FF3B30'} />
            </div>
          )}
        </div>
      </div>

      {/* 持仓管理 */}
      <div style={{ ...glassCardStyle, marginBottom: '24px' }}>
        <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>持仓管理</span>
          <button
            onClick={() => setShowAddPositionModal(true)}
            style={buttonStyle('primary')}
            onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.02)' }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            添加持仓
          </button>
        </div>
        <div style={{ padding: '32px' }}>
          {positions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0', color: '#86868B' }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginBottom: '16px', opacity: 0.3 }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <p>暂无持仓，点击"添加持仓"开始</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #E8E8ED' }}>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>股票代码</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>数量</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>成本价</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>当前价</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>盈亏</th>
                    <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => {
                    const profit = pos.current_price ? (pos.current_price - pos.cost_price) * pos.quantity : 0
                    const profitPercent = pos.cost_price > 0 ? ((pos.current_price || pos.cost_price) - pos.cost_price) / pos.cost_price * 100 : 0
                    return (
                      <tr key={pos.code} style={{ borderBottom: '1px solid #F5F5F7' }}>
                        <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontSize: '14px', color: '#1D1D1F' }}>{pos.code}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px' }}>{pos.quantity}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px' }}>¥{pos.cost_price.toFixed(2)}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px' }}>{pos.current_price ? `¥${pos.current_price.toFixed(2)}` : '-'}</td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px', color: profit >= 0 ? '#34C759' : '#FF3B30' }}>
                          {profit >= 0 ? '+' : ''}{profit.toFixed(2)} ({profitPercent >= 0 ? '+' : ''}{profitPercent.toFixed(2)}%)
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemovePosition(pos.code)}
                            style={{ ...buttonStyle('danger'), padding: '6px 12px', fontSize: '12px' }}
                          >
                            删除
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* 时间范围设置 */}
      <div style={{ ...glassCardStyle, marginBottom: '24px' }}>
        <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
          时间范围设置
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
            <div>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#1D1D1F', marginBottom: '16px' }}>回测时间范围</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>起始日期</label>
                  <input
                    type="date"
                    value={backtestRange.start}
                    onChange={(e) => setBacktestRange({ ...backtestRange, start: e.target.value })}
                    style={{
                      width: '100%',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      padding: '10px 14px',
                      fontSize: '14px',
                      outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>结束日期</label>
                  <input
                    type="date"
                    value={backtestRange.end}
                    onChange={(e) => setBacktestRange({ ...backtestRange, end: e.target.value })}
                    style={{
                      width: '100%',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      padding: '10px 14px',
                      fontSize: '14px',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>
            </div>
            <div>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#1D1D1F', marginBottom: '16px' }}>预测时间范围</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>起始日期</label>
                  <input
                    type="date"
                    value={predictionRange.start}
                    onChange={(e) => setPredictionRange({ ...predictionRange, start: e.target.value })}
                    style={{
                      width: '100%',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      padding: '10px 14px',
                      fontSize: '14px',
                      outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>结束日期</label>
                  <input
                    type="date"
                    value={predictionRange.end}
                    onChange={(e) => setPredictionRange({ ...predictionRange, end: e.target.value })}
                    style={{
                      width: '100%',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      padding: '10px 14px',
                      fontSize: '14px',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
          <div style={{ marginTop: '24px' }}>
            <button
              onClick={handleSaveSettings}
              style={buttonStyle('primary')}
              onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.02)' }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
            >
              保存更改
            </button>
          </div>
        </div>
      </div>

      {/* 历史AI建议 */}
      <div style={{ ...glassCardStyle, marginBottom: '24px' }}>
        <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
          历史AI建议
        </div>
        <div style={{ padding: '32px' }}>
          {aiAdviceHistory.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 0', color: '#86868B' }}>
              暂无历史建议
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {aiAdviceHistory.slice(0, 5).map((advice, index) => (
                <div key={index} style={{ padding: '16px', background: '#F5F5F7', borderRadius: '12px' }}>
                  <div style={{ fontSize: '12px', color: '#86868B', marginBottom: '8px' }}>
                    {new Date(advice.timestamp).toLocaleString('zh-CN')}
                  </div>
                  <div style={{ fontSize: '14px', color: '#1D1D1F', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {advice.content.slice(0, 100)}...
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 操作说明 */}
      <div style={glassCardStyle}>
        <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
          操作说明
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '14px', color: '#86868B' }}>
            {[
              '添加持仓：输入股票代码、数量和成本价',
              '设置回测时间范围用于策略回测',
              '设置预测时间范围用于AI推荐',
              '点击"保存更改"同步到服务器',
            ].map((text, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <span style={{ color: '#0071E3', fontWeight: 600, flexShrink: 0 }}>{i + 1}.</span>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 添加持仓弹窗 */}
      {showAddPositionModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ ...glassCardStyle, padding: '32px', width: '100%', maxWidth: '400px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#1D1D1F', marginBottom: '20px' }}>添加持仓</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>股票代码</label>
                <input
                  type="text"
                  value={newPosition.code}
                  onChange={(e) => setNewPosition({ ...newPosition, code: e.target.value })}
                  placeholder="如：000001"
                  style={{
                    width: '100%',
                    border: '1px solid #E8E8ED',
                    borderRadius: '12px',
                    padding: '12px 16px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>数量</label>
                <input
                  type="number"
                  value={newPosition.quantity}
                  onChange={(e) => setNewPosition({ ...newPosition, quantity: Number(e.target.value) })}
                  style={{
                    width: '100%',
                    border: '1px solid #E8E8ED',
                    borderRadius: '12px',
                    padding: '12px 16px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>成本价</label>
                <input
                  type="number"
                  step="0.01"
                  value={newPosition.cost_price}
                  onChange={(e) => setNewPosition({ ...newPosition, cost_price: Number(e.target.value) })}
                  style={{
                    width: '100%',
                    border: '1px solid #E8E8ED',
                    borderRadius: '12px',
                    padding: '12px 16px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', color: '#86868B', marginBottom: '6px' }}>当前价（可选）</label>
                <input
                  type="number"
                  step="0.01"
                  value={newPosition.current_price || ''}
                  placeholder="留空则使用成本价"
                  onChange={(e) => setNewPosition({ ...newPosition, current_price: Number(e.target.value) || 0 })}
                  style={{
                    width: '100%',
                    border: '1px solid #E8E8ED',
                    borderRadius: '12px',
                    padding: '12px 16px',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowAddPositionModal(false)}
                style={buttonStyle('secondary')}
              >
                取消
              </button>
              <button
                onClick={handleAddPosition}
                style={buttonStyle('primary')}
              >
                添加
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div 
      style={{ 
        padding: '20px 24px', 
        background: 'rgba(0, 0, 0, 0.02)', 
        borderRadius: '16px',
        transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)' }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0, 0, 0, 0.02)' }}
    >
      <p style={{ fontSize: '12px', color: '#86868B', marginBottom: '4px' }}>{label}</p>
      <p style={{ fontSize: '24px', fontWeight: 600, color, letterSpacing: '-0.02em' }}>{value}</p>
    </div>
  )
}

export default ShadowAccount
