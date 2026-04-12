/**
 * 选股池页面
 * 展示3000+股票池、模型排序推荐、自定义股票池、截面日期选择
 * 新增：得分分布直方图、特征重要性ECharts柱状图
 * 
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  stockPoolService,
  type RankResponse,
  type StockListResponse,
} from '../services/stockPool'
import { BarChart } from '../components/Charts'
import { ScrollReveal } from '../components/motion'

/** 模型类型 */
type ModelType = 'lightgbm' | 'xgboost'

/**
 * 图表说明组件
 * @param text - 说明文字
 * @returns 图表说明元素
 */
function ChartDescription({ text }: { text: string }) {
  return (
    <p style={{ fontSize: '12px', color: '#86868B', marginTop: '8px', lineHeight: 1.6 }}>{text}</p>
  )
}

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
 * 选股池页面组件
 * @returns 选股池页面
 */
function StockPool() {
  const [modelType, setModelType] = useState<ModelType>('xgboost')
  const [topN, setTopN] = useState(50)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [rankData, setRankData] = useState<RankResponse | null>(null)

  const [stockList, setStockList] = useState<StockListResponse | null>(null)
  const [stockPage, setStockPage] = useState(1)
  const [stockKeyword, setStockKeyword] = useState('')
  const [stockLoading, setStockLoading] = useState(false)

  const [customCodes, setCustomCodes] = useState('')
  const [useCustom, setUseCustom] = useState(false)

  const [activeTab, setActiveTab] = useState<'rank' | 'pool'>('rank')

  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<string>('')

  useEffect(() => {
    stockPoolService.getAvailableDates().then((res) => {
      setAvailableDates(res.dates || [])
      if (res.latest) setSelectedDate(res.latest)
    }).catch(() => {})
  }, [])

  const loadRankData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let codes: string[] | undefined
      if (useCustom && customCodes.trim()) {
        codes = customCodes
          .split(/[\n,;，；\s]+/)
          .map((s) => s.trim())
          .filter((s) => /^\d{6}$/.test(s))
        if (codes.length === 0) {
          setError('自定义股票池中没有有效的6位股票代码')
          setLoading(false)
          return
        }
      }
      const data = await stockPoolService.rankStocks(
        topN, modelType, codes, selectedDate || undefined
      )
      setRankData(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : '加载排序数据失败'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [modelType, topN, useCustom, customCodes, selectedDate])

  const loadStockList = useCallback(async () => {
    setStockLoading(true)
    try {
      const data = await stockPoolService.getStockList(stockPage, 100, stockKeyword || undefined)
      setStockList(data)
    } catch {
      setStockList(null)
    } finally {
      setStockLoading(false)
    }
  }, [stockPage, stockKeyword])

  useEffect(() => {
    loadRankData()
  }, [loadRankData])

  useEffect(() => {
    if (activeTab === 'pool') {
      loadStockList()
    }
  }, [activeTab, loadStockList])

  /** 得分分布直方图数据 */
  const scoreDistribution = useMemo(() => {
    if (!rankData?.ranked_stocks.length) return []
    const scores = rankData.ranked_stocks.map((s) => s.score)
    const minScore = Math.min(...scores)
    const maxScore = Math.max(...scores)
    const range = maxScore - minScore
    if (range === 0) return [{ name: '同一得分', value: scores.length }]
    const binCount = 8
    const binWidth = range / binCount
    const bins = Array.from({ length: binCount }, (_, i) => ({
      rangeMin: minScore + i * binWidth,
      rangeMax: minScore + (i + 1) * binWidth,
      label: `${(minScore + i * binWidth).toFixed(2)}~${(minScore + (i + 1) * binWidth).toFixed(2)}`,
      count: 0,
    }))
    scores.forEach((score) => {
      const binIndex = Math.min(Math.floor((score - minScore) / binWidth), binCount - 1)
      bins[binIndex].count++
    })
    return bins.map((b) => ({ name: b.label, value: b.count }))
  }, [rankData])

  /** 特征重要性ECharts柱状图数据 */
  const featureBarData = useMemo(() => {
    if (!rankData?.feature_importance_top20.length) return []
    return rankData.feature_importance_top20
      .slice(0, 15)
      .map((fi) => ({ name: fi.feature, value: Number(fi.importance.toFixed(1)) }))
  }, [rankData])

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <ScrollReveal index={0}>
      <div style={{ marginBottom: '32px' }}>
        <h1 className="page-title">选股池</h1>
        <p style={{ fontSize: '15px', color: 'var(--color-text-subtle)' }}>
          基于排序学习模型对股票池进行排序推荐，支持自定义股票池和截面日期选择
        </p>
      </div>
      </ScrollReveal>

      {/* 控制面板卡片 */}
      <ScrollReveal index={1}>
      <motion.div className="card" style={{ padding: '24px 32px', marginBottom: '24px' }} whileHover={{ y: -1 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', color: '#86868B' }}>模型:</span>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value as ModelType)}
              style={{
                border: '1px solid #E8E8ED',
                borderRadius: '12px',
                padding: '8px 16px',
                fontSize: '14px',
                background: '#FFFFFF',
                color: '#1D1D1F',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="xgboost">XGBoost (推荐)</option>
              <option value="lightgbm">LightGBM</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', color: '#86868B' }}>截面日期:</span>
            <select
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{
                border: '1px solid #E8E8ED',
                borderRadius: '12px',
                padding: '8px 16px',
                fontSize: '14px',
                background: '#FFFFFF',
                color: '#1D1D1F',
                outline: 'none',
                cursor: 'pointer',
                maxWidth: '180px',
              }}
            >
              {availableDates.length > 0 ? (
                availableDates.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))
              ) : (
                <option value="">加载中...</option>
              )}
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', color: '#86868B' }}>Top N:</span>
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              style={{
                border: '1px solid #E8E8ED',
                borderRadius: '12px',
                padding: '8px 16px',
                fontSize: '14px',
                background: '#FFFFFF',
                color: '#1D1D1F',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={useCustom}
                onChange={(e) => setUseCustom(e.target.checked)}
                style={{ width: '16px', height: '16px', borderRadius: '4px' }}
              />
              <span style={{ fontSize: '14px', color: '#86868B' }}>自定义股票池</span>
            </label>
          </div>
          {rankData && (
            <div style={{ fontSize: '14px', color: '#86868B', marginLeft: 'auto' }}>
              股票池: <span style={{ fontWeight: 600, color: '#1D1D1F' }}>{rankData.total_pool_size}</span> 只
            </div>
          )}
        </div>
        {useCustom && (
          <div style={{ marginTop: '16px' }}>
            <textarea
              value={customCodes}
              onChange={(e) => setCustomCodes(e.target.value)}
              placeholder="输入股票代码，多个代码用逗号、换行或空格分隔（如：000001, 600519, 000858）"
              style={{
                width: '100%',
                border: '1px solid #E8E8ED',
                borderRadius: '12px',
                padding: '12px 16px',
                fontSize: '14px',
                background: '#FFFFFF',
                color: '#1D1D1F',
                outline: 'none',
                resize: 'vertical',
                minHeight: '80px',
              }}
              rows={3}
            />
          </div>
        )}
      </motion.div>
      </ScrollReveal>

      {/* 排序说明卡片 */}
      {rankData && (
        <div style={{ ...glassCardStyle, padding: '20px 24px', marginBottom: '24px', background: 'rgba(0, 113, 227, 0.06)' }}>
          <p style={{ fontSize: '14px', color: '#1D1D1F', lineHeight: 1.7 }}>
            <strong style={{ color: '#0071E3' }}>排序说明：</strong>
            模型对 <strong>{rankData.total_pool_size}</strong> 只股票进行排序，
            截面日期为 <strong>{rankData.timestamp}</strong>，
            使用 <strong>{rankData.model_type === 'xgboost' ? 'XGBoost rank:ndcg' : 'LightGBM LambdaRank'}</strong> 模型。
            <strong>预测得分</strong>越高，模型认为该股票未来一周收益率排名越靠前。
            得分反映的是股票间的<strong>相对排序关系</strong>，而非绝对收益率预测值。
            排名前3的股票以绿色标记，前10以蓝色标记。
          </p>
        </div>
      )}

      {/* Tab切换 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveTab('rank')}
          style={{
            padding: '12px 24px',
            borderRadius: '12px',
            fontSize: '14px',
            fontWeight: 500,
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            background: activeTab === 'rank' ? '#0071E3' : 'rgba(0, 0, 0, 0.04)',
            color: activeTab === 'rank' ? '#FFFFFF' : '#86868B',
          }}
        >
          模型排序结果
        </button>
        <button
          onClick={() => setActiveTab('pool')}
          style={{
            padding: '12px 24px',
            borderRadius: '12px',
            fontSize: '14px',
            fontWeight: 500,
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            background: activeTab === 'pool' ? '#0071E3' : 'rgba(0, 0, 0, 0.04)',
            color: activeTab === 'pool' ? '#FFFFFF' : '#86868B',
          }}
        >
          股票池浏览
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div style={{ ...glassCardStyle, padding: '16px 24px', marginBottom: '24px', background: 'rgba(255, 59, 48, 0.08)' }}>
          <p style={{ fontSize: '14px', color: '#FF3B30' }}>{error}</p>
        </div>
      )}

      {activeTab === 'rank' && (
        <>
          {/* 得分分布 + 特征重要性图表 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
            <div style={glassCardStyle}>
              <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
                模型得分分布
              </div>
              <div style={{ padding: '32px' }}>
                {scoreDistribution.length > 0 ? (
                  <>
                    <BarChart
                      data={scoreDistribution}
                      horizontal={false}
                      height="300px"
                      showLabel
                    />
                    <ChartDescription text="得分分布直方图展示模型对Top N股票的预测得分分布情况。分布越集中说明模型对Top股票的区分度越低，分布越分散则区分度越高。" />
                  </>
                ) : (
                  <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                    暂无排序数据
                  </div>
                )}
              </div>
            </div>

            <div style={glassCardStyle}>
              <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
                特征重要性 Top 15
              </div>
              <div style={{ padding: '32px' }}>
                {featureBarData.length > 0 ? (
                  <>
                    <BarChart
                      data={featureBarData}
                      horizontal
                      height="300px"
                      showLabel
                      sort="desc"
                    />
                    <ChartDescription text="特征重要性（Gain）反映各因子对模型排序决策的贡献度。值越大说明该因子在模型中越重要，对选股结果的影响越显著。" />
                  </>
                ) : (
                  <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                    暂无特征重要性数据
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 推荐股票列表 */}
          <div style={glassCardStyle}>
            <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
              推荐股票 Top {topN}
            </div>
            <div style={{ padding: '32px' }}>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '48px 0' }}>
                  <div style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid #E8E8ED', borderTopColor: '#0071E3', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '16px' }}></div>
                  <p style={{ color: '#86868B', fontSize: '14px' }}>模型排序中，请稍候...</p>
                </div>
              ) : rankData && rankData.ranked_stocks.length > 0 ? (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #E8E8ED' }}>
                        <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B', textTransform: 'uppercase' }}>排名</th>
                        <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B', textTransform: 'uppercase' }}>股票代码</th>
                        <th style={{ textAlign: 'right', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B', textTransform: 'uppercase' }}>预测得分</th>
                        <th style={{ textAlign: 'right', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B', textTransform: 'uppercase' }}>得分百分位</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rankData.ranked_stocks.map((stock, index) => {
                        const maxScore = rankData.ranked_stocks[0]?.score || 1
                        const minScore = rankData.ranked_stocks[rankData.ranked_stocks.length - 1]?.score || 0
                        const pct = maxScore !== minScore
                          ? ((stock.score - minScore) / (maxScore - minScore)) * 100
                          : 50
                        return (
                          <tr
                            key={stock.code}
                            style={{
                              borderBottom: '1px solid #F5F5F7',
                              background: index < 3 ? 'rgba(52, 199, 89, 0.04)' : index < 10 ? 'rgba(0, 113, 227, 0.04)' : 'transparent',
                            }}
                          >
                            <td style={{ padding: '12px 16px' }}>
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  width: '28px',
                                  height: '28px',
                                  borderRadius: '50%',
                                  fontSize: '12px',
                                  fontWeight: 600,
                                  background: index < 3 ? '#34C759' : index < 10 ? 'rgba(0, 113, 227, 0.1)' : '#F5F5F7',
                                  color: index < 3 ? '#FFFFFF' : index < 10 ? '#0071E3' : '#86868B',
                                }}
                              >
                                {stock.rank}
                              </span>
                            </td>
                            <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontSize: '14px', color: '#1D1D1F' }}>{stock.code}</td>
                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                              <span style={{ fontWeight: 600, color: '#34C759' }}>
                                {stock.score.toFixed(6)}
                              </span>
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                                <div style={{ width: '64px', height: '6px', background: '#F5F5F7', borderRadius: '3px', overflow: 'hidden' }}>
                                  <div
                                    style={{
                                      height: '100%',
                                      background: 'linear-gradient(90deg, #0071E3, #34C759)',
                                      borderRadius: '3px',
                                      width: `${pct}%`,
                                    }}
                                  />
                                </div>
                                <span style={{ fontSize: '12px', color: '#86868B' }}>{pct.toFixed(0)}%</span>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '32px 0', color: '#86868B' }}>暂无数据</div>
              )}
            </div>
          </div>
        </>
      )}

      {activeTab === 'pool' && (
        <div style={glassCardStyle}>
          <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
            股票池浏览
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <input
                type="text"
                value={stockKeyword}
                onChange={(e) => {
                  setStockKeyword(e.target.value)
                  setStockPage(1)
                }}
                placeholder="搜索股票代码或名称..."
                style={{
                  border: '1px solid #E8E8ED',
                  borderRadius: '12px',
                  padding: '10px 16px',
                  fontSize: '14px',
                  background: '#FFFFFF',
                  color: '#1D1D1F',
                  outline: 'none',
                  width: '256px',
                }}
              />
              {stockList && (
                <span style={{ fontSize: '14px', color: '#86868B' }}>
                  共 {stockList.total} 只股票
                </span>
              )}
            </div>

            {stockLoading ? (
              <div style={{ textAlign: 'center', padding: '32px 0', color: '#86868B' }}>加载中...</div>
            ) : stockList && stockList.stocks.length > 0 ? (
              <>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #E8E8ED' }}>
                        <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>#</th>
                        <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>股票代码</th>
                        <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>名称</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stockList.stocks.map((stock, i) => (
                        <tr key={stock.code} style={{ borderBottom: '1px solid #F5F5F7' }}>
                          <td style={{ padding: '10px 16px', fontSize: '12px', color: '#86868B' }}>
                            {(stockPage - 1) * 100 + i + 1}
                          </td>
                          <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontSize: '14px', color: '#1D1D1F' }}>{stock.code}</td>
                          <td style={{ padding: '10px 16px', fontSize: '14px', color: '#86868B' }}>{stock.name || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '24px', paddingTop: '24px', borderTop: '1px solid #E8E8ED' }}>
                  <button
                    onClick={() => setStockPage((p) => Math.max(1, p - 1))}
                    disabled={stockPage <= 1}
                    style={{
                      padding: '10px 20px',
                      fontSize: '14px',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      background: '#FFFFFF',
                      color: stockPage <= 1 ? '#A1A1A6' : '#1D1D1F',
                      cursor: stockPage <= 1 ? 'not-allowed' : 'pointer',
                      opacity: stockPage <= 1 ? 0.5 : 1,
                    }}
                  >
                    上一页
                  </button>
                  <span style={{ fontSize: '14px', color: '#86868B' }}>
                    第 {stockPage} / {Math.ceil((stockList.total || 1) / 100)} 页
                  </span>
                  <button
                    onClick={() => setStockPage((p) => p + 1)}
                    disabled={stockPage >= Math.ceil((stockList.total || 1) / 100)}
                    style={{
                      padding: '10px 20px',
                      fontSize: '14px',
                      border: '1px solid #E8E8ED',
                      borderRadius: '12px',
                      background: '#FFFFFF',
                      color: stockPage >= Math.ceil((stockList.total || 1) / 100) ? '#A1A1A6' : '#1D1D1F',
                      cursor: stockPage >= Math.ceil((stockList.total || 1) / 100) ? 'not-allowed' : 'pointer',
                      opacity: stockPage >= Math.ceil((stockList.total || 1) / 100) ? 0.5 : 1,
                    }}
                  >
                    下一页
                  </button>
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '32px 0', color: '#86868B' }}>暂无股票数据</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default StockPool
