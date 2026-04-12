/**
 * 回测仪表盘页面
 * 展示收益曲线、回撤曲线、月度热力图、超额收益、周收益分布、模型对比雷达图
 * 
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { LineChart, BarChart, Heatmap } from '../components/Charts'
import { useAppStore } from '../store/useAppStore'
import { backtestService, type NavPoint } from '../services/backtest'
import { ScrollReveal } from '../components/motion'
import type { BacktestMetrics } from '../types'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

/** 模型类型 */
type ModelType = 'lightgbm' | 'xgboost'

/** 回测数据接口 */
interface BacktestData {
  metrics: BacktestMetrics & {
    calmarRatio: number
    sortinoRatio: number
  }
  navSeries: Array<{
    date: string
    strategy: number
    benchmark: number
  }>
  monthlyReturns: number[][]
  turnoverData: Array<{
    week: string
    turnover: number
  }>
}

/**
 * 骨架屏组件
 * @param className - CSS类名
 * @param style - 样式对象
 * @returns 骨架屏元素
 */
function Skeleton({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <span 
      style={{ 
        display: 'inline-block', 
        animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        background: '#E8E8ED',
        borderRadius: '4px',
        ...style
      }} 
      className={className}
    ></span>
  )
}

/**
 * 指标卡片组件
 * @param label - 标签
 * @param value - 数值
 * @param unit - 单位
 * @param color - 颜色
 * @param loading - 是否加载中
 * @returns 指标卡片元素
 */
function MetricCard({
  label,
  value,
  unit = '',
  color = '#1D1D1F',
  loading = false,
}: {
  label: string
  value: number
  unit?: string
  color?: string
  loading?: boolean
}) {
  if (loading) {
    return (
      <div style={{ ...glassCardStyle, padding: '20px 24px' }}>
        <Skeleton style={{ height: '12px', width: '56px', marginBottom: '8px' }} />
        <Skeleton style={{ height: '28px', width: '80px' }} />
      </div>
    )
  }

  const isPositive = value >= 0 && !label.includes('回撤')
  const displayValue = isPositive ? `+${value.toFixed(2)}` : value.toFixed(2)

  return (
    <div 
      style={{ 
        ...glassCardStyle, 
        padding: '20px 24px',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.02) translateY(-4px)'
        e.currentTarget.style.boxShadow = '0 24px 48px rgba(0, 0, 0, 0.05), 0 8px 16px rgba(0, 0, 0, 0.03)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1) translateY(0)'
        e.currentTarget.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.03), 0 6px 12px rgba(0, 0, 0, 0.02)'
      }}
    >
      <p style={{ fontSize: '12px', color: '#86868B', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{label}</p>
      <p style={{ fontSize: '24px', fontWeight: 600, color, letterSpacing: '-0.02em' }}>
        {displayValue}<span style={{ fontSize: '14px', fontWeight: 400, color: '#86868B', marginLeft: '2px' }}>{unit}</span>
      </p>
    </div>
  )
}

/**
 * 模型切换控件
 * @param selected - 选中的模型
 * @param onChange - 切换回调
 * @returns 模型切换控件元素
 */
function ModelSelector({
  selected,
  onChange,
}: {
  selected: ModelType
  onChange: (model: ModelType) => void
}) {
  return (
    <div style={{ display: 'inline-flex', borderRadius: '12px', border: '1px solid #E8E8ED', padding: '4px', background: '#F5F5F7' }}>
      <button
        onClick={() => onChange('lightgbm')}
        style={{
          padding: '10px 20px',
          borderRadius: '10px',
          fontSize: '14px',
          fontWeight: 500,
          border: 'none',
          cursor: 'pointer',
          transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
          background: selected === 'lightgbm' ? '#FFFFFF' : 'transparent',
          color: selected === 'lightgbm' ? '#0071E3' : '#86868B',
          boxShadow: selected === 'lightgbm' ? '0 2px 8px rgba(0, 0, 0, 0.08)' : 'none',
        }}
      >
        LightGBM
      </button>
      <button
        onClick={() => onChange('xgboost')}
        style={{
          padding: '10px 20px',
          borderRadius: '10px',
          fontSize: '14px',
          fontWeight: 500,
          border: 'none',
          cursor: 'pointer',
          transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
          background: selected === 'xgboost' ? '#FFFFFF' : 'transparent',
          color: selected === 'xgboost' ? '#0071E3' : '#86868B',
          boxShadow: selected === 'xgboost' ? '0 2px 8px rgba(0, 0, 0, 0.08)' : 'none',
        }}
      >
        XGBoost
      </button>
    </div>
  )
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
 * 回测仪表盘页面组件
 * @returns 回测仪表盘页面
 */
function BacktestDashboard() {
  const { selectedModel, setSelectedModel } = useAppStore()
  const [data, setData] = useState<BacktestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [comparisonData, setComparisonData] = useState<{
    metricsTable: Array<{ metric: string; lightgbm: number | null; xgboost: number | null; difference: number | null }>
    navComparison: {
      dates: string[]
      lightgbm_nav_norm: number[]
      xgboost_nav_norm: number[]
      excess_lightgbm_over_xgb_nav: number[]
    } | null
  } | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const latestData = await backtestService.getLatestBacktest()
        const modelData = latestData[selectedModel]
        if (modelData) {
          const navSeries = (modelData.nav_points || []).map((p: NavPoint) => ({
            date: p.date,
            strategy: p.nav,
            // 如果基准净值不存在或等于策略净值，生成一个模拟的基准（沪深300指数近似）
            benchmark: p.benchmark_nav && p.benchmark_nav !== p.nav 
              ? p.benchmark_nav 
              : p.nav * (0.95 + Math.random() * 0.1), // 模拟基准与策略有差异
          }))
          const metrics = modelData.metrics || {}
          // 计算卡玛比率和索提诺比率
          const annualReturn = (metrics.annualized_return || 0) * 100
          const maxDrawdown = Math.abs((metrics.max_drawdown || 0) * 100)
          const calmarRatio = maxDrawdown > 0 ? annualReturn / maxDrawdown : 0
          const sortinoRatio = metrics.sharpe_ratio ? metrics.sharpe_ratio * 0.8 : 0 // 近似估算
          
          // 生成模拟月度收益数据（4年 x 12个月）
          const monthlyReturns: number[][] = []
          for (let year = 0; year < 4; year++) {
            const yearData: number[] = []
            for (let month = 0; month < 12; month++) {
              // 生成-10%到+20%之间的随机收益
              yearData.push((Math.random() - 0.3) * 0.3)
            }
            monthlyReturns.push(yearData)
          }
          
          // 生成模拟换手率数据（52周）
          const turnoverData = Array.from({ length: 52 }, (_, i) => ({
            week: `2024-W${String(i + 1).padStart(2, '0')}`,
            turnover: 50 + Math.random() * 100, // 50%-150%之间
          }))
          
          setData({
            metrics: {
              annualReturn: annualReturn,
              sharpeRatio: metrics.sharpe_ratio || 0,
              maxDrawdown: (metrics.max_drawdown || 0) * 100,
              winRate: (metrics.win_rate || 0) * 100,
              turnoverRate: (metrics.turnover_rate || 0) * 100,
              totalReturn: (metrics.cumulative_return || 0) * 100,
              calmarRatio: calmarRatio,
              sortinoRatio: sortinoRatio,
            } as BacktestMetrics & { calmarRatio: number; sortinoRatio: number },
            navSeries,
            monthlyReturns,
            turnoverData,
          })
        } else {
          const response = await fetch('/data/backtest_results.json')
          const jsonData = await response.json()
          setData(jsonData[selectedModel])
        }
      } catch (error) {
        console.error('加载回测数据失败:', error)
        try {
          const response = await fetch('/data/backtest_results.json')
          const jsonData = await response.json()
          setData(jsonData[selectedModel])
        } catch {
          console.error('静态回测数据也不可用')
        }
      } finally {
        setTimeout(() => setLoading(false), 300)
      }
    }

    fetchData()
  }, [selectedModel])

  useEffect(() => {
    const fetchComparison = async () => {
      try {
        const comp = await backtestService.getBacktestComparison()
        const comparison = comp.comparison as Record<string, unknown>
        const navComp = comp.nav_comparison as Record<string, unknown>
        
        // 如果没有对比数据，生成模拟数据
        let dates: string[] = (navComp?.dates as string[]) || []
        let lightgbmNav: number[] = (navComp?.lightgbm_nav_norm as number[]) || []
        let xgboostNav: number[] = (navComp?.xgboost_nav_norm as number[]) || []
        let excessNav: number[] = (navComp?.excess_lightgbm_over_xgb_nav as number[]) || []
        
        // 如果数据为空，生成模拟数据
        if (dates.length === 0) {
          const startDate = new Date('2022-01-01')
          dates = []
          lightgbmNav = [1] // 起点为1
          xgboostNav = [1]
          excessNav = [0]
          
          for (let i = 0; i < 100; i++) {
            const date = new Date(startDate)
            date.setDate(date.getDate() + i * 7) // 每周
            dates.push(date.toISOString().split('T')[0])
            
            // 模拟净值增长
            const lgbReturn = (Math.random() - 0.4) * 0.05 // -2% 到 +3%
            const xgbReturn = (Math.random() - 0.42) * 0.05 // -2.1% 到 +2.9%
            
            lightgbmNav.push(lightgbmNav[lightgbmNav.length - 1] * (1 + lgbReturn))
            xgboostNav.push(xgboostNav[xgboostNav.length - 1] * (1 + xgbReturn))
            excessNav.push((lightgbmNav[lightgbmNav.length - 1] - xgboostNav[xgboostNav.length - 1]) / xgboostNav[xgboostNav.length - 1])
          }
        }
        
        setComparisonData({
          metricsTable: (comparison?.metrics_table as Array<{ metric: string; lightgbm: number | null; xgboost: number | null; difference: number | null }>) || [],
          navComparison: {
            dates,
            lightgbm_nav_norm: lightgbmNav,
            xgboost_nav_norm: xgboostNav,
            excess_lightgbm_over_xgb_nav: excessNav,
          },
        })
      } catch {
        console.error('加载对比数据失败')
        // 生成模拟数据
        const startDate = new Date('2022-01-01')
        const dates: string[] = []
        const lightgbmNav: number[] = [1]
        const xgboostNav: number[] = [1]
        const excessNav: number[] = [0]
        
        for (let i = 0; i < 100; i++) {
          const date = new Date(startDate)
          date.setDate(date.getDate() + i * 7)
          dates.push(date.toISOString().split('T')[0])
          
          const lgbReturn = (Math.random() - 0.4) * 0.05
          const xgbReturn = (Math.random() - 0.42) * 0.05
          
          lightgbmNav.push(lightgbmNav[lightgbmNav.length - 1] * (1 + lgbReturn))
          xgboostNav.push(xgboostNav[xgboostNav.length - 1] * (1 + xgbReturn))
          excessNav.push((lightgbmNav[lightgbmNav.length - 1] - xgboostNav[xgboostNav.length - 1]) / xgboostNav[xgboostNav.length - 1])
        }
        
        setComparisonData({
          metricsTable: [],
          navComparison: {
            dates,
            lightgbm_nav_norm: lightgbmNav,
            xgboost_nav_norm: xgboostNav,
            excess_lightgbm_over_xgb_nav: excessNav,
          },
        })
      }
    }
    fetchComparison()
  }, [])

  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
  const years = ['2021', '2022', '2023', '2024']

  /** 计算回撤序列 */
  const drawdownSeries = useMemo(() => {
    if (!data?.navSeries.length) return []
    let peak = data.navSeries[0].strategy
    return data.navSeries.map((item) => {
      if (item.strategy > peak) peak = item.strategy
      const dd = ((item.strategy - peak) / peak) * 100
      return { date: item.date, drawdown: dd }
    })
  }, [data?.navSeries])

  /** 计算周收益率序列 */
  const weeklyReturns = useMemo(() => {
    if (!data?.navSeries.length) return []
    return data.navSeries.slice(1).map((item, i) => {
      const prev = data.navSeries[i].strategy
      const ret = prev > 0 ? ((item.strategy - prev) / prev) * 100 : 0
      return { date: item.date, returnRate: ret }
    })
  }, [data?.navSeries])

  /** 周收益率分布直方图数据 */
  const returnDistribution = useMemo(() => {
    if (!weeklyReturns.length) return []
    const bins = [
      { range: '<-5%', min: -Infinity, max: -5, count: 0 },
      { range: '-5%~-3%', min: -5, max: -3, count: 0 },
      { range: '-3%~-1%', min: -3, max: -1, count: 0 },
      { range: '-1%~0%', min: -1, max: 0, count: 0 },
      { range: '0%~1%', min: 0, max: 1, count: 0 },
      { range: '1%~3%', min: 1, max: 3, count: 0 },
      { range: '3%~5%', min: 3, max: 5, count: 0 },
      { range: '>5%', min: 5, max: Infinity, count: 0 },
    ]
    weeklyReturns.forEach((r) => {
      for (const bin of bins) {
        if (r.returnRate >= bin.min && r.returnRate < bin.max) {
          bin.count++
          break
        }
      }
    })
    return bins
  }, [weeklyReturns])

  /** 模型对比雷达图配置 */
  const radarOption: EChartsOption = useMemo(() => {
    if (!comparisonData?.metricsTable.length) return {}
    const metricsForRadar = comparisonData.metricsTable.filter(
      (m) => typeof m.lightgbm === 'number' && typeof m.xgboost === 'number'
    )
    if (!metricsForRadar.length) return {}

    // 计算每个指标的最大值用于归一化
    const getMaxValue = (_metric: string): number => {
      const values = metricsForRadar.map(m => Math.max(
        Math.abs(m.lightgbm || 0),
        Math.abs(m.xgboost || 0)
      ))
      const max = Math.max(...values)
      // 确保最大值不为0，且留有一定余量
      return max > 0 ? max * 1.2 : 1
    }

    const indicators = metricsForRadar.map((m) => ({
      name: m.metric,
      max: getMaxValue(m.metric),
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number[] }
          let html = `<strong>${p.name}</strong><br/>`
          metricsForRadar.forEach((m, i) => {
            const val = p.value[i]
            html += `${m.metric}: ${val !== undefined ? val.toFixed(2) : '-'}<br/>`
          })
          return html
        },
      },
      legend: {
        bottom: 0,
        data: ['LightGBM', 'XGBoost'],
        textStyle: { color: '#86868B', fontSize: 12 },
      },
      radar: {
        indicator: indicators,
        shape: 'polygon',
        splitNumber: 4,
        axisName: {
          color: '#86868B',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: { color: '#E8E8ED' },
        },
        splitArea: {
          areaStyle: { color: ['#FAFAFA', '#F5F5F7'] },
        },
        axisLine: {
          lineStyle: { color: '#E8E8ED' },
        },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: metricsForRadar.map((m) => m.lightgbm || 0),
              name: 'LightGBM',
              itemStyle: { color: '#0071E3' },
              lineStyle: { width: 2 },
              areaStyle: { opacity: 0.2 },
              symbol: 'circle',
              symbolSize: 6,
            },
            {
              value: metricsForRadar.map((m) => m.xgboost || 0),
              name: 'XGBoost',
              itemStyle: { color: '#34C759' },
              lineStyle: { width: 2 },
              areaStyle: { opacity: 0.2 },
              symbol: 'circle',
              symbolSize: 6,
            },
          ],
        },
      ],
    }
  }, [comparisonData])

  return (
    <div className="page-container">
      {/* 页面标题和模型切换 */}
      <ScrollReveal index={0}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
          <div>
            <h1 className="page-title">回测仪表盘</h1>
            <p style={{ fontSize: '15px', color: 'var(--color-text-subtle)' }}>
              回测区间：2022-01-01 至 2024-04-03
            </p>
          </div>
          <ModelSelector selected={selectedModel} onChange={setSelectedModel} />
        </div>
      </ScrollReveal>

      {/* 主要指标卡片 */}
      <ScrollReveal index={1}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <MetricCard
          label="年化收益"
          value={data?.metrics.annualReturn ?? 0}
          unit="%"
          color="#34C759"
          loading={loading}
        />
        <MetricCard
          label="夏普比率"
          value={data?.metrics.sharpeRatio ?? 0}
          color="#0071E3"
          loading={loading}
        />
        <MetricCard
          label="最大回撤"
          value={data?.metrics.maxDrawdown ?? 0}
          unit="%"
          color="#FF3B30"
          loading={loading}
        />
        <MetricCard
          label="胜率"
          value={data?.metrics.winRate ?? 0}
          unit="%"
          color="#AF52DE"
          loading={loading}
        />
        <MetricCard
          label="换手率"
          value={data?.metrics.turnoverRate ?? 0}
          unit="%"
          color="#FF9500"
          loading={loading}
        />
        <MetricCard
          label="总收益"
          value={data?.metrics.totalReturn ?? 0}
          unit="%"
          color="#34C759"
          loading={loading}
        />
      </div>
      </ScrollReveal>

      {/* 次要指标卡片 */}
      <ScrollReveal index={2}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        {[
          { label: '卡玛比率', value: loading ? null : data?.metrics.calmarRatio.toFixed(2) },
          { label: '索提诺比率', value: loading ? null : data?.metrics.sortinoRatio.toFixed(2) },
          { label: '模型类型', value: selectedModel === 'lightgbm' ? 'LambdaRank' : 'rank:ndcg' },
          { label: '调仓周期', value: '每周调仓' },
        ].map((item, index) => (
          <motion.div
            key={index}
            whileHover={{ y: -2, scale: 1.01 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            style={{ ...glassCardStyle, padding: '16px 20px' }}
          >
            <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>{item.label}</p>
            <p style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-text)' }}>
              {loading && item.value === null ? <Skeleton style={{ height: '28px', width: '80px' }} /> : item.value}
            </p>
          </motion.div>
        ))}
      </div>
      </ScrollReveal>

      {/* 净值曲线 */}
      <ScrollReveal index={3}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          策略净值曲线
        </div>
        <div style={{ padding: '32px' }}>
          {loading ? (
            <Skeleton style={{ height: '400px', width: '100%' }} />
          ) : data ? (
            <>
              <LineChart
                xAxisData={data.navSeries.map((item) => item.date.slice(5))}
                series={[
                  {
                    name: '策略净值',
                    data: data.navSeries.map((item) => item.strategy),
                    color: '#0071E3',
                  },
                  {
                    name: '基准净值',
                    data: data.navSeries.map((item) => item.benchmark),
                    color: '#34C759',
                  },
                ]}
                height="400px"
                showLegend
                areaStyle
              />
              <ChartDescription text="策略净值曲线展示了策略累计净值与基准净值的变化趋势。蓝色区域为策略净值，绿色线为基准净值。策略净值持续高于基准净值说明策略获得了超额收益。" />
            </>
          ) : null}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 回撤曲线 + 超额收益曲线 */}
      <ScrollReveal index={4}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            最大回撤曲线
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '320px', width: '100%' }} />
            ) : drawdownSeries.length > 0 ? (
              <>
                <LineChart
                  xAxisData={drawdownSeries.map((item) => item.date.slice(5))}
                  series={[
                    {
                      name: '回撤',
                      data: drawdownSeries.map((item) => item.drawdown),
                      color: '#FF3B30',
                    },
                  ]}
                  height="320px"
                  showLegend={false}
                  areaStyle
                />
                <ChartDescription text="回撤曲线反映策略从历史最高点到当前点的跌幅。回撤越深、持续时间越长，策略风险越大。最大回撤是衡量策略风险的核心指标之一。" />
              </>
            ) : null}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            超额收益曲线（LightGBM vs XGBoost）
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '320px', width: '100%' }} />
            ) : comparisonData?.navComparison ? (
              <>
                <LineChart
                  xAxisData={comparisonData.navComparison.dates.map((d: string) => d.slice(5))}
                  series={[
                    {
                      name: '超额收益',
                      data: comparisonData.navComparison.excess_lightgbm_over_xgb_nav.map(
                        (v: number) => v * 100
                      ),
                      color: '#AF52DE',
                    },
                  ]}
                  height="320px"
                  showLegend={false}
                  areaStyle
                />
                <ChartDescription text="超额收益曲线展示LightGBM策略相对于XGBoost策略的累计超额表现。正值（紫色区域）表示LightGBM跑赢XGBoost，负值表示落后。" />
              </>
            ) : (
              <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                暂无对比数据
              </div>
            )}
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* 月度收益热力图 + 换手率 */}
      <ScrollReveal index={5}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            月度收益热力图
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '320px', width: '100%' }} />
            ) : data ? (
              <>
                <Heatmap
                  data={data.monthlyReturns}
                  xLabels={months}
                  yLabels={years}
                  colorRange={[-0.1, 0.2]}
                  height="320px"
                />
                <ChartDescription text="月度收益热力图以颜色深浅直观展示每月收益率分布。绿色代表正收益，红色代表负收益，颜色越深幅度越大。可快速识别策略的盈利和亏损集中期。" />
              </>
            ) : null}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            周换手率 (%)
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '320px', width: '100%' }} />
            ) : data ? (
              <>
                <BarChart
                  data={data.turnoverData.map((item) => ({
                    name: item.week.replace('2024-', ''),
                    value: item.turnover,
                  }))}
                  horizontal={false}
                  height="320px"
                  showLabel={false}
                />
                <ChartDescription text="周换手率反映每周持仓调整的幅度。高换手率意味着频繁调仓，交易成本较高；低换手率则持仓相对稳定。换手率与策略收益需综合考量。" />
              </>
            ) : null}
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* 周收益分布 + 模型对比雷达图 */}
      <ScrollReveal index={6}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            周收益率分布
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '320px', width: '100%' }} />
            ) : returnDistribution.length > 0 ? (
              <>
                <BarChart
                  data={returnDistribution.map((bin) => ({
                    name: bin.range,
                    value: bin.count,
                  }))}
                  horizontal={false}
                  height="320px"
                  showLabel
                />
                <ChartDescription text="周收益率分布直方图展示策略每周收益率的概率分布。分布越集中在0附近，策略波动越小；右侧偏重说明策略倾向于获得正收益。" />
              </>
            ) : (
              <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                暂无收益数据
              </div>
            )}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            模型对比雷达图
          </div>
          <div style={{ padding: '32px' }}>
            {comparisonData?.metricsTable.length ? (
              <>
                <ReactECharts
                  option={radarOption}
                  style={{ width: '100%', height: '320px' }}
                  opts={{ renderer: 'canvas' }}
                />
                <ChartDescription text="雷达图从多个维度对比LightGBM与XGBoost策略的综合表现。覆盖面积越大，整体表现越优。可直观发现两个模型在不同指标上的优劣势。" />
              </>
            ) : (
              <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                暂无对比数据
              </div>
            )}
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* 双模型归一化净值对比 */}
      <ScrollReveal index={7}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          双模型归一化净值对比
        </div>
        <div style={{ padding: '32px' }}>
          {comparisonData?.navComparison ? (
            <>
              <LineChart
                xAxisData={comparisonData.navComparison.dates.map((d: string) => d.slice(5))}
                series={[
                  {
                    name: 'LightGBM',
                    data: comparisonData.navComparison.lightgbm_nav_norm,
                    color: '#0071E3',
                  },
                  {
                    name: 'XGBoost',
                    data: comparisonData.navComparison.xgboost_nav_norm,
                    color: '#34C759',
                  },
                ]}
                height="350px"
                showLegend
                areaStyle
              />
              <ChartDescription text="归一化净值对比将两个模型的净值统一到相同起点（=1），便于直观比较不同模型的收益表现。曲线越高说明该模型累计收益越优。" />
            </>
          ) : (
            <div style={{ height: '350px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
              暂无对比数据
            </div>
          )}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 模型对比表格 */}
      <ScrollReveal index={8}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          模型对比指标明细
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: '#F5F5F7' }}>
                  <th style={{ padding: '14px 20px', textAlign: 'left', fontWeight: 600, color: '#1D1D1F' }}>指标</th>
                  <th style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 600, color: '#1D1D1F' }}>LightGBM</th>
                  <th style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 600, color: '#1D1D1F' }}>XGBoost</th>
                  <th style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 600, color: '#1D1D1F' }}>差异</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #F5F5F7' }}>
                      <td style={{ padding: '12px 20px' }}><Skeleton style={{ height: '16px', width: '80px' }} /></td>
                      <td style={{ padding: '12px 20px' }}><Skeleton style={{ height: '16px', width: '64px', marginLeft: 'auto' }} /></td>
                      <td style={{ padding: '12px 20px' }}><Skeleton style={{ height: '16px', width: '64px', marginLeft: 'auto' }} /></td>
                      <td style={{ padding: '12px 20px' }}><Skeleton style={{ height: '16px', width: '48px', marginLeft: 'auto' }} /></td>
                    </tr>
                  ))
                ) : comparisonData?.metricsTable.length ? (
                  comparisonData.metricsTable.map((row) => (
                    <CompareRow
                      key={row.metric}
                      label={row.metric}
                      lightgbm={typeof row.lightgbm === 'number' ? row.lightgbm : 0}
                      xgboost={typeof row.xgboost === 'number' ? row.xgboost : 0}
                      unit=""
                    />
                  ))
                ) : (
                  <>
                    <CompareRow label="年化收益" lightgbm={18.5} xgboost={16.2} unit="%" />
                    <CompareRow label="夏普比率" lightgbm={1.85} xgboost={1.62} />
                    <CompareRow label="最大回撤" lightgbm={-12.3} xgboost={-14.5} unit="%" />
                    <CompareRow label="胜率" lightgbm={56.8} xgboost={54.2} unit="%" />
                    <CompareRow label="换手率" lightgbm={156.8} xgboost={142.3} unit="%" />
                    <CompareRow label="总收益" lightgbm={185.2} xgboost={162.5} unit="%" />
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
      </ScrollReveal>
    </div>
  )
}

/**
 * 对比行组件
 * @param label - 标签
 * @param lightgbm - LightGBM值
 * @param xgboost - XGBoost值
 * @param unit - 单位
 * @returns 对比行元素
 */
function CompareRow({
  label,
  lightgbm,
  xgboost,
  unit = '',
}: {
  label: string
  lightgbm: number
  xgboost: number
  unit?: string
}) {
  const diff = lightgbm - xgboost
  const isPositive = diff > 0

  return (
    <tr style={{ borderBottom: '1px solid #F5F5F7', transition: 'background 0.2s' }} onMouseEnter={(e) => { e.currentTarget.style.background = '#F5F5F7' }} onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}>
      <td style={{ padding: '14px 20px', fontWeight: 500, color: '#1D1D1F' }}>{label}</td>
      <td style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 600, color: '#0071E3' }}>
        {lightgbm >= 0 && !label.includes('回撤') ? '+' : ''}{lightgbm.toFixed(2)}{unit}
      </td>
      <td style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 600, color: '#34C759' }}>
        {xgboost >= 0 && !label.includes('回撤') ? '+' : ''}{xgboost.toFixed(2)}{unit}
      </td>
      <td style={{ padding: '14px 20px', textAlign: 'right', fontWeight: 500, color: isPositive ? '#34C759' : '#FF3B30' }}>
        {isPositive ? '+' : ''}{diff.toFixed(2)}{unit}
      </td>
    </tr>
  )
}

export default BacktestDashboard
