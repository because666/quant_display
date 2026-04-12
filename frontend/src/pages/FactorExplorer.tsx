/**
 * 因子探索页面
 * 展示因子分布散点图、收益相关性、因子IC值、因子说明
 *
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { BarChart } from '../components/Charts'
import { ScrollReveal } from '../components/motion'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

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
 * 图表说明组件
 * @param text - 说明文字
 * @returns 图表说明元素
 */
function ChartDescription({ text }: { text: string }) {
  return (
    <p style={{ fontSize: '12px', color: '#86868B', marginTop: '8px', lineHeight: 1.6 }}>{text}</p>
  )
}

function FactorExplorer() {
  const [selectedFactor, setSelectedFactor] = useState<string>('动量_5日')
  const [loading] = useState(false)

  // 模拟数据
  const correlations = [
    { factor_name: '动量_5日', correlation: 0.085 },
    { factor_name: '波动率_20日', correlation: -0.062 },
    { factor_name: '换手率', correlation: -0.048 },
    { factor_name: 'RSI_14', correlation: 0.032 },
    { factor_name: 'ATR_14', correlation: -0.055 },
    { factor_name: 'MACD', correlation: 0.028 },
    { factor_name: '布林带位置', correlation: 0.042 },
    { factor_name: '成交额', correlation: -0.038 },
  ]

  const icData = [
    { factor_name: '动量_5日', ic_value: 0.045 },
    { factor_name: '波动率_20日', ic_value: -0.032 },
    { factor_name: '换手率', ic_value: -0.028 },
    { factor_name: 'RSI_14', ic_value: 0.018 },
    { factor_name: 'ATR_14', ic_value: -0.035 },
    { factor_name: 'MACD', ic_value: 0.015 },
    { factor_name: '布林带位置', ic_value: 0.025 },
    { factor_name: '成交额', ic_value: -0.022 },
  ]

  /** IC值柱状图数据 */
  const icBarData = useMemo(() => {
    return icData.map(ic => ({
      name: ic.factor_name,
      value: ic.ic_value,
    }))
  }, [icData])

  /** 生成散点图模拟数据 */
  const scatterData = useMemo(() => {
    // 根据选中的因子生成模拟散点数据
    const selectedCorr = correlations.find(c => c.factor_name === selectedFactor)?.correlation || 0
    const data: Array<[number, number]> = []
    
    // 生成100个随机点，根据相关系数调整分布
    for (let i = 0; i < 100; i++) {
      const factorValue = (Math.random() - 0.5) * 4 // -2 到 2
      const noise = (Math.random() - 0.5) * 0.3
      const returnValue = factorValue * selectedCorr * 3 + noise
      data.push([factorValue, returnValue])
    }
    return data
  }, [selectedFactor, correlations])

  /** 散点图配置 */
  const scatterOption: EChartsOption = useMemo(() => {
    return {
      grid: {
        top: 40,
        right: 40,
        bottom: 60,
        left: 60,
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: unknown) => {
          const p = params as { data: [number, number] }
          return `因子值: ${p.data[0].toFixed(3)}<br/>收益率: ${(p.data[1] * 100).toFixed(2)}%`
        },
      },
      xAxis: {
        name: `${selectedFactor} 值`,
        nameLocation: 'middle',
        nameGap: 30,
        type: 'value',
        splitLine: { lineStyle: { color: '#E8E8ED', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#86868B' } },
        axisLabel: { color: '#86868B' },
      },
      yAxis: {
        name: '未来一周收益率',
        nameLocation: 'middle',
        nameGap: 40,
        type: 'value',
        axisLabel: {
          color: '#86868B',
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
        splitLine: { lineStyle: { color: '#E8E8ED', type: 'dashed' } },
        axisLine: { lineStyle: { color: '#86868B' } },
      },
      series: [
        {
          type: 'scatter',
          data: scatterData,
          symbolSize: 8,
          itemStyle: {
            color: '#0071E3',
            opacity: 0.6,
          },
          emphasis: {
            itemStyle: {
              color: '#0071E3',
              opacity: 1,
              borderColor: '#FFFFFF',
              borderWidth: 2,
            },
          },
        },
      ],
    }
  }, [scatterData, selectedFactor])

  const factorCategories = [
    {
      name: '动量因子',
      description: '过去N日收益率，反映价格趋势',
      factors: ['动量_5日', '动量_10日'],
    },
    {
      name: '波动因子',
      description: '收益率标准差，衡量风险水平',
      factors: ['波动率_20日', 'ATR_14'],
    },
    {
      name: '流动性因子',
      description: '换手率、成交额，反映交易活跃度',
      factors: ['换手率', '成交额'],
    },
    {
      name: '技术指标',
      description: 'RSI、MACD、布林带等技术分析指标',
      factors: ['RSI_14', 'MACD', '布林带位置'],
    },
  ]

  return (
    <div className="page-container">
      {/* 页面标题 */}
      <ScrollReveal index={0}>
      <div style={{ marginBottom: '32px' }}>
        <h1 className="page-title">因子探索</h1>
        <p style={{ fontSize: '15px', color: 'var(--color-text-subtle)' }}>
          深入分析各因子与未来收益的相关性
        </p>
      </div>
      </ScrollReveal>

      {/* 因子选择器 */}
      <ScrollReveal index={1}>
      <motion.div className="card" style={{ padding: '24px 32px', marginBottom: '24px' }} whileHover={{ y: -1 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>选择因子：</span>
          {loading ? (
            <span style={{ color: 'var(--color-text-muted)' }}>加载中...</span>
          ) : (
            <select
              value={selectedFactor}
              onChange={(e) => setSelectedFactor(e.target.value)}
              className="input"
              style={{ minWidth: '200px' }}
            >
              {correlations.map(c => (
                <option key={c.factor_name} value={c.factor_name}>{c.factor_name}</option>
              ))}
            </select>
          )}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 因子分布散点图 + IC值 */}
      <ScrollReveal index={2}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            因子分布散点图
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B' }}>
                加载中...
              </div>
            ) : (
              <>
                <ReactECharts
                  option={scatterOption}
                  style={{ width: '100%', height: '400px' }}
                  opts={{ renderer: 'canvas' }}
                />
                <ChartDescription text="散点图展示因子值与未来一周收益率的关系。点的分布趋势反映因子与收益的相关性：右上倾斜表示正相关，右下倾斜表示负相关。" />
              </>
            )}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            因子IC值排名
          </div>
          <div style={{ padding: '32px' }}>
            <BarChart
              data={icBarData}
              horizontal
              height="400px"
              showLabel
            />
            <ChartDescription text="IC值（信息系数）衡量因子与收益的线性相关程度，绝对值越大说明因子预测能力越强。正值表示因子越大收益越高，负值表示因子越大收益越低。" />
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* 因子与未来收益相关性明细 */}
      <ScrollReveal index={3}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          因子与未来收益相关性明细
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E8E8ED' }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>因子名称</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>相关系数</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>IC值</th>
                  <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: '12px', fontWeight: 600, color: '#86868B' }}>信号强度</th>
                </tr>
              </thead>
              <tbody>
                {correlations.map((corr) => {
                  const ic = icData.find(i => i.factor_name === corr.factor_name)
                  const signalStrength = Math.abs(ic?.ic_value || 0)
                  let strengthText = '弱'
                  let strengthColor = '#86868B'
                  if (signalStrength > 0.05) {
                    strengthText = '中'
                    strengthColor = '#0071E3'
                  }
                  if (signalStrength > 0.1) {
                    strengthText = '强'
                    strengthColor = '#34C759'
                  }
                  return (
                    <tr key={corr.factor_name} style={{ borderBottom: '1px solid #F5F5F7' }}>
                      <td style={{ padding: '12px 16px', fontSize: '14px', color: '#1D1D1F' }}>{corr.factor_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px', color: corr.correlation >= 0 ? '#34C759' : '#FF3B30' }}>
                        {corr.correlation >= 0 ? '+' : ''}{corr.correlation.toFixed(4)}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontSize: '14px', color: (ic?.ic_value || 0) >= 0 ? '#34C759' : '#FF3B30' }}>
                        {(ic?.ic_value || 0) >= 0 ? '+' : ''}{(ic?.ic_value || 0).toFixed(4)}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '4px 12px',
                          borderRadius: '980px',
                          fontSize: '12px',
                          fontWeight: 500,
                          background: `${strengthColor}15`,
                          color: strengthColor,
                        }}>
                          {strengthText}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 因子说明 */}
      <ScrollReveal index={4}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          因子说明
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
            {factorCategories.map((category) => (
              <motion.div
                key={category.name}
                whileHover={{ y: -3, backgroundColor: 'rgba(0, 113, 227, 0.06)' }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                style={{
                  padding: '24px',
                  background: 'var(--color-bg-subtle)',
                  borderRadius: '16px',
                  cursor: 'default',
                }}
              >
                <h4 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text)', marginBottom: '8px' }}>
                  {category.name}
                </h4>
                <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '12px' }}>
                  {category.description}
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {category.factors.map((factor) => (
                    <span
                      key={factor}
                      style={{
                        fontSize: '12px',
                        color: 'var(--color-primary)',
                        background: 'var(--color-primary-soft)',
                        padding: '4px 10px',
                        borderRadius: '6px',
                      }}
                    >
                      {factor}
                    </span>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
      </ScrollReveal>
    </div>
  )
}

export default FactorExplorer
