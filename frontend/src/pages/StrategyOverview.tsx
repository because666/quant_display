/**
 * 策略概览页面
 * 展示项目简介、模型架构图、数据范围、核心算法、技术栈、核心指标仪表盘、数据集划分
 *
 * @author 量化策略系统
 * @version 2.0
 */
import { useNavigate } from 'react-router-dom'
// UI组件已内联实现
import { PieChart } from '../components/Charts'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { useEffect, useState } from 'react'

/**
 * 图表说明组件
 * @param text - 说明文字
 * @returns 图表说明元素
 */
function ChartDescription({ text }: { text: string }) {
  return (
    <p className="text-xs text-gray-400 mt-2 leading-relaxed">{text}</p>
  )
}

/**
 * 策略概览页面组件
 * 应用苹果极简风格设计：
 * - 纯白色背景配合3D Mobius粒子河背景
 * - 毛玻璃卡片效果
 * - 模糊淡入动画
 * - 液态按钮交互
 *
 * @returns 策略概览页面
 */
function StrategyOverview() {
  const navigate = useNavigate()
  const [mounted, setMounted] = useState(false)

  // 页面加载后触发动画
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 100)
    return () => clearTimeout(timer)
  }, [])

  const techStack = [
    { name: 'React 18', category: '前端' },
    { name: 'TypeScript', category: '前端' },
    { name: 'TailwindCSS', category: '前端' },
    { name: 'ECharts', category: '可视化' },
    { name: 'Plotly', category: '可视化' },
    { name: 'FastAPI', category: '后端' },
    { name: 'LightGBM', category: '模型' },
    { name: 'XGBoost', category: '模型' },
    { name: 'Pandas', category: '数据处理' },
    { name: 'DeepSeek', category: 'AI服务' },
    { name: 'SQLite', category: '数据库' },
  ]

  /** 核心指标仪表盘配置 */
  const gaugeOption: EChartsOption = {
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 10,
        itemStyle: {
          color: '#0071E3',
        },
        progress: {
          show: true,
          width: 18,
        },
        pointer: {
          show: false,
        },
        axisLine: {
          lineStyle: {
            width: 18,
            color: [[1, '#E8E8ED']],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: false,
        },
        axisLabel: {
          show: false,
        },
        title: {
          fontSize: 13,
          color: '#86868B',
          offsetCenter: [0, '70%'],
        },
        detail: {
          fontSize: 28,
          fontWeight: 600,
          color: '#1D1D1F',
          offsetCenter: [0, '30%'],
          formatter: '{value}%',
        },
        data: [{ value: 18.5, name: '年化收益率' }],
      },
    ],
  }

  /** 数据集划分饼图数据 */
  const datasetPieData = [
    { name: '训练集 (2014-2019)', value: 60 },
    { name: '验证集 (2020-2021)', value: 20 },
    { name: '测试集 (2022-2024)', value: 20 },
  ]

  /** 因子类别分布饼图数据 */
  const factorCategoryPieData = [
    { name: '动量因子', value: 6 },
    { name: '波动因子', value: 4 },
    { name: '流动性因子', value: 3 },
    { name: '技术指标', value: 5 },
    { name: '估值因子', value: 2 },
  ]

  // 动画样式
  const fadeInStyle = (delay: number): React.CSSProperties => ({
    opacity: mounted ? 1 : 0,
    transform: mounted ? 'translateY(0)' : 'translateY(30px)',
    filter: mounted ? 'blur(0)' : 'blur(10px)',
    transition: `all 0.8s cubic-bezier(0.25, 0.1, 0.25, 1) ${delay}ms`,
  })

  // 毛玻璃卡片样式
  const glassCardStyle: React.CSSProperties = {
    background: 'rgba(255, 255, 255, 0.85)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    borderRadius: '24px',
    border: '1px solid rgba(255, 255, 255, 0.5)',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.03), 0 6px 12px rgba(0, 0, 0, 0.02)',
    transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '60px 24px 80px' }}>
      {/* Hero区域 */}
      <div style={{ textAlign: 'center', padding: '80px 0 60px', ...fadeInStyle(0) }}>
        {/* 标签徽章 */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 20px',
            background: 'rgba(0, 113, 227, 0.08)',
            color: '#0071E3',
            borderRadius: '980px',
            fontSize: '13px',
            fontWeight: 500,
            marginBottom: '28px',
            letterSpacing: '-0.01em',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
          }}
        >
          <span style={{ fontSize: '14px' }}>Learning to Rank 驱动</span>
        </div>

        {/* 主标题 */}
        <h1
          style={{
            fontSize: '64px',
            fontWeight: 600,
            lineHeight: 1.08,
            color: '#1D1D1F',
            letterSpacing: '-0.02em',
            marginBottom: '24px',
            maxWidth: '720px',
            marginLeft: 'auto',
            marginRight: 'auto',
          }}
        >
          基于排序学习的
          <br />
          <span style={{ color: '#0071E3' }}>量化投资选股策略</span>
        </h1>

        {/* 副标题 */}
        <p
          style={{
            fontSize: '21px',
            color: '#86868B',
            maxWidth: '580px',
            margin: '0 auto 40px',
            lineHeight: 1.5,
            fontWeight: 400,
          }}
        >
          运用机器学习排序算法，构建A股市场智能选股系统
        </p>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/ai')}
            style={{
              background: '#0071E3',
              color: '#FFFFFF',
              borderRadius: '980px',
              padding: '16px 32px',
              fontSize: '15px',
              fontWeight: 500,
              letterSpacing: '-0.01em',
              transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
              boxShadow: '0 4px 20px rgba(0, 113, 227, 0.3)',
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.02)'
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 113, 227, 0.4)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 113, 227, 0.3)'
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = 'scale(0.98)'
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = 'scale(1.02)'
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            开始使用
          </button>
          <button
            onClick={() => navigate('/backtest')}
            style={{
              background: 'rgba(255, 255, 255, 0.8)',
              color: '#0071E3',
              borderRadius: '980px',
              padding: '16px 32px',
              fontSize: '15px',
              fontWeight: 500,
              letterSpacing: '-0.01em',
              transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
              border: '1px solid rgba(0, 113, 227, 0.2)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backdropFilter: 'blur(10px)',
              WebkitBackdropFilter: 'blur(10px)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(0, 113, 227, 0.08)'
              e.currentTarget.style.borderColor = 'rgba(0, 113, 227, 0.4)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
              e.currentTarget.style.borderColor = 'rgba(0, 113, 227, 0.2)'
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 13L8 8L13 13L21 5M21 11V19H3V5"/>
            </svg>
            查看回测
          </button>
        </div>
      </div>

      {/* 核心指标卡片 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '20px',
          marginBottom: '80px',
          ...fadeInStyle(100),
        }}
      >
        {[
          { icon: '📅', value: '10', unit: '年+', label: '数据时间范围', sub: '2014 - 2024' },
          { icon: '📊', value: '2,258', unit: '只', label: '股票池规模', sub: '存续A股' },
          { icon: '⏱️', value: '周频', unit: '', label: '调仓频率', sub: '每周调仓' },
          { icon: '🤖', value: '双模型', unit: '', label: '预测模型', sub: 'LightGBM + XGBoost' },
        ].map((stat, index) => (
          <div
            key={index}
            style={{
              ...glassCardStyle,
              padding: '28px 32px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
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
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: 'rgba(0, 113, 227, 0.08)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '22px',
                flexShrink: 0,
              }}
            >
              {stat.icon}
            </div>
            <div>
              <p style={{ fontSize: '32px', fontWeight: 600, color: '#1D1D1F', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
                {stat.value}
                {stat.unit && <span style={{ fontSize: '18px', fontWeight: 400, opacity: 0.8 }}>{stat.unit}</span>}
              </p>
              <p style={{ fontSize: '14px', color: '#86868B', marginTop: '6px', fontWeight: 400 }}>{stat.label}</p>
              <p style={{ fontSize: '13px', color: '#A1A1A6', marginTop: '4px' }}>{stat.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* 核心指标仪表盘 + 数据集划分 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '24px',
          marginBottom: '32px',
          ...fadeInStyle(200),
        }}
      >
        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            核心策略指标
          </div>
          <div style={{ padding: '32px' }}>
            <ReactECharts
              option={gaugeOption}
              style={{ width: '100%', height: '280px' }}
              opts={{ renderer: 'canvas' }}
            />
            <ChartDescription text="仪表盘展示策略的核心年化收益率指标。该指标反映策略在回测期间的年均复合增长率，是衡量策略盈利能力的首要指标。" />
          </div>
        </div>

        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            数据集划分
          </div>
          <div style={{ padding: '32px' }}>
            <PieChart
              data={datasetPieData}
              donut
              centerLabel="数据占比"
              centerValue="10年"
              height="280px"
              showLegend
              showLabel
            />
            <ChartDescription text="数据集按时间划分为训练集（2014-2019）、验证集（2020-2021）和测试集（2022-2024）。训练集用于模型学习，验证集用于超参调优，测试集用于最终评估，确保无未来信息泄露。" />
          </div>
        </div>
      </div>

      {/* 模型架构图 */}
      <div style={{ ...fadeInStyle(300) }}>
        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0071E3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
              <path d="M9 9h6v6H9z"/>
            </svg>
            模型架构
          </div>
          <div
            style={{
              padding: '48px 32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
              overflowX: 'auto',
              flexWrap: 'wrap',
            }}
          >
            <ArchNode emoji="📊" label="数据层" color="blue" desc={['AKShare数据源', '日线行情数据']} />
            <ArrowIcon />
            <ArchNode emoji="⚙️" label="特征工程" color="green" desc={['因子计算', '周频截面']} />
            <ArrowIcon />
            <ArchNode emoji="🤖" label="模型层" color="purple" desc={['LightGBM', 'XGBoost']} />
            <ArrowIcon />
            <ArchNode emoji="📈" label="策略层" color="orange" desc={['TopN选股', '回测评估']} />
            <ArrowIcon />
            <ArchNode emoji="💡" label="应用层" color="pink" desc={['AI推荐', '影子账户']} />
          </div>
        </div>
      </div>

      {/* 核心算法介绍 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '24px',
          marginTop: '32px',
          ...fadeInStyle(400),
        }}
      >
        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#6366f1' }}></span>
            LightGBM LambdaRank
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <p style={{ fontSize: '14px', lineHeight: 1.7, color: '#86868B' }}>
                LightGBM是一种高效的梯度提升决策树算法，LambdaRank是一种专门用于排序任务的损失函数。
              </p>
            </div>
            <div
              style={{
                padding: '20px 24px',
                borderRadius: '16px',
                background: 'rgba(0, 0, 0, 0.02)',
                marginBottom: '16px',
              }}
            >
              <h4 style={{ fontWeight: 600, marginBottom: '10px', fontSize: '14px', color: '#1D1D1F' }}>核心优势</h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {['训练速度快，内存占用低', '直接优化NDCG排序指标', '支持类别特征，无需独热编码', '叶子生长策略，精度更高'].map((item, i) => (
                  <li
                    key={i}
                    style={{
                      position: 'relative',
                      paddingLeft: '24px',
                      marginBottom: '8px',
                      fontSize: '14px',
                      color: '#86868B',
                      lineHeight: 1.6,
                    }}
                  >
                    <span style={{ position: 'absolute', left: 0, color: '#0071E3', fontWeight: 600, fontSize: '13px' }}>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div
              style={{
                padding: '20px 24px',
                borderRadius: '16px',
                borderLeft: '3px solid #0071E3',
                background: 'rgba(0, 113, 227, 0.04)',
              }}
            >
              <h4 style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: '#0071E3' }}>模型配置</h4>
              <pre style={{ margin: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#86868B' }}>
{`objective: lambdarank
num_leaves: 31
learning_rate: 0.05`}
              </pre>
            </div>
          </div>
        </div>

        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}></span>
            XGBoost rank:ndcg
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ marginBottom: '24px' }}>
              <p style={{ fontSize: '14px', lineHeight: 1.7, color: '#86868B' }}>
                XGBoost是另一种流行的梯度提升框架，rank:ndcg目标函数专门用于学习排序任务。
              </p>
            </div>
            <div
              style={{
                padding: '20px 24px',
                borderRadius: '16px',
                background: 'rgba(0, 0, 0, 0.02)',
                marginBottom: '16px',
              }}
            >
              <h4 style={{ fontWeight: 600, marginBottom: '10px', fontSize: '14px', color: '#1D1D1F' }}>核心优势</h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {['正则化防止过拟合', '支持并行计算', '内置处理缺失值', '丰富的调参选项'].map((item, i) => (
                  <li
                    key={i}
                    style={{
                      position: 'relative',
                      paddingLeft: '24px',
                      marginBottom: '8px',
                      fontSize: '14px',
                      color: '#86868B',
                      lineHeight: 1.6,
                    }}
                  >
                    <span style={{ position: 'absolute', left: 0, color: '#34C759', fontWeight: 600, fontSize: '13px' }}>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div
              style={{
                padding: '20px 24px',
                borderRadius: '16px',
                borderLeft: '3px solid #34C759',
                background: 'rgba(52, 199, 89, 0.04)',
              }}
            >
              <h4 style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: '#34C759' }}>模型配置</h4>
              <pre style={{ margin: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#86868B' }}>
{`objective: rank:ndcg
max_depth: 6
learning_rate: 0.05`}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* 因子类别分布 + 数据范围 + 回测框架 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '24px',
          marginTop: '32px',
          ...fadeInStyle(500),
        }}
      >
        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            因子类别分布
          </div>
          <div style={{ padding: '32px' }}>
            <PieChart
              data={factorCategoryPieData}
              donut
              centerLabel="因子总数"
              centerValue="20个"
              height="280px"
              showLegend
              showLabel
            />
            <ChartDescription text="饼图展示各类因子在总因子池中的数量占比。动量因子和技术指标因子占比较大，反映了策略对价格趋势和技术形态的重视。" />
          </div>
        </div>

        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            数据范围
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {[
                { label: '时间跨度', value: '2014-01 ~ 2024-12' },
                { label: '股票池', value: '2,258只存续A股' },
                { label: '数据频率', value: '周频截面' },
                { label: '训练集', value: '2014-2019' },
                { label: '验证集', value: '2020-2021' },
                { label: '测试集', value: '2022-2024' },
              ].map((item, index) => (
                <div
                  key={item.label}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '16px 0',
                    borderBottom: index < 5 ? '1px solid rgba(0, 0, 0, 0.05)' : 'none',
                  }}
                >
                  <span style={{ fontSize: '14px', color: '#86868B' }}>{item.label}</span>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: '#1D1D1F' }}>{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            回测框架
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {[
                { icon: '📅', title: 'T+1交易规则', desc: '当日买入，次日方可卖出' },
                { icon: '💰', title: '交易成本', desc: '印花税0.05% + 佣金0.03%' },
                { icon: '📊', title: '滑点设置', desc: '双边0.1%' },
                { icon: '🚫', title: '涨跌停限制', desc: '涨停无法买入，跌停无法卖出' },
              ].map((item) => (
                <div
                  key={item.title}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '14px',
                    padding: '16px 20px',
                    background: 'rgba(0, 0, 0, 0.02)',
                    borderRadius: '16px',
                    transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 113, 227, 0.06)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 0, 0, 0.02)'
                  }}
                >
                  <span style={{ fontSize: '24px', flexShrink: 0 }}>{item.icon}</span>
                  <div>
                    <p style={{ fontSize: '14px', fontWeight: 600, color: '#1D1D1F', marginBottom: '2px', letterSpacing: '-0.01em' }}>
                      {item.title}
                    </p>
                    <p style={{ fontSize: '12px', color: '#86868B' }}>{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 技术栈 */}
      <div style={{ marginTop: '32px', ...fadeInStyle(600) }}>
        <div style={glassCardStyle}>
          <div
            style={{
              padding: '24px 32px',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
              fontWeight: 600,
              fontSize: '17px',
              color: '#1D1D1F',
              letterSpacing: '-0.01em',
            }}
          >
            技术栈
          </div>
          <div style={{ padding: '32px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {techStack.map((tech) => (
                <span
                  key={tech.name}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 20px',
                    background: 'rgba(0, 0, 0, 0.02)',
                    borderRadius: '980px',
                    fontSize: '13px',
                    fontWeight: 400,
                    color: '#86868B',
                    transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
                    cursor: 'default',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 113, 227, 0.08)'
                    e.currentTarget.style.color = '#0071E3'
                    e.currentTarget.style.transform = 'scale(1.02)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(0, 0, 0, 0.02)'
                    e.currentTarget.style.color = '#86868B'
                    e.currentTarget.style.transform = 'scale(1)'
                  }}
                >
                  {tech.name}
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 400,
                      color: '#A1A1A6',
                      padding: '2px 8px',
                      background: 'rgba(255, 255, 255, 0.8)',
                      borderRadius: '980px',
                    }}
                  >
                    {tech.category}
                  </span>
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 快速开始 */}
      <div
        style={{
          position: 'relative',
          borderRadius: '24px',
          padding: '80px 48px',
          textAlign: 'center',
          overflow: 'hidden',
          background: 'linear-gradient(135deg, #1D1D1F 0%, #2C2C2E 100%)',
          color: '#FFFFFF',
          marginTop: '32px',
          ...fadeInStyle(700),
        }}
      >
        <div style={{ position: 'relative', zIndex: 1 }}>
          <h2
            style={{
              fontSize: '40px',
              fontWeight: 600,
              marginBottom: '16px',
              letterSpacing: '-0.02em',
              color: '#FFFFFF',
            }}
          >
            准备好开始了吗？
          </h2>
          <p
            style={{
              fontSize: '17px',
              color: 'rgba(255, 255, 255, 0.6)',
              marginBottom: '36px',
              lineHeight: 1.5,
            }}
          >
            查看AI智能推荐，获取最新投资建议
          </p>
          <button
            onClick={() => navigate('/ai')}
            style={{
              background: '#0071E3',
              color: '#FFFFFF',
              borderRadius: '980px',
              padding: '16px 32px',
              fontSize: '15px',
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
              boxShadow: '0 4px 20px rgba(0, 113, 227, 0.4)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.02)'
              e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 113, 227, 0.5)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 113, 227, 0.4)'
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            立即开始
          </button>
        </div>
        {/* 背景装饰 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `
              radial-gradient(circle at 20% 50%, rgba(0, 113, 227, 0.15) 0%, transparent 50%),
              radial-gradient(circle at 80% 50%, rgba(0, 113, 227, 0.1) 0%, transparent 50%)
            `,
            pointerEvents: 'none',
          }}
        />
      </div>
    </div>
  )
}

/**
 * 架构节点组件
 * @param emoji - 图标表情
 * @param label - 标签文字
 * @param color - 颜色主题
 * @param desc - 描述文字数组
 * @returns 架构节点元素
 */
function ArchNode({ emoji, label, color, desc }: { emoji: string; label: string; color: string; desc: string[] }) {
  const colors: Record<string, string> = {
    blue: 'rgba(0, 113, 227, 0.08)',
    green: 'rgba(52, 199, 89, 0.08)',
    purple: 'rgba(175, 82, 222, 0.08)',
    orange: 'rgba(255, 149, 0, 0.08)',
    pink: 'rgba(255, 55, 95, 0.08)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', minWidth: '110px' }}>
      <div
        style={{
          width: '96px',
          height: '96px',
          borderRadius: '24px',
          background: colors[color],
          border: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.04)',
          cursor: 'default',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.05)'
          e.currentTarget.style.boxShadow = '0 12px 32px rgba(0, 0, 0, 0.08)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.04)'
        }}
      >
        <span style={{ fontSize: '28px' }}>{emoji}</span>
        <span style={{ fontWeight: 600, fontSize: '13px', color: '#1D1D1F', letterSpacing: '-0.01em' }}>{label}</span>
      </div>
      <div style={{ marginTop: '12px', fontSize: '11px', color: '#86868B', lineHeight: 1.5 }}>
        {desc.map((d, i) => <p key={i}>{d}</p>)}
      </div>
    </div>
  )
}

/**
 * 箭头图标组件
 * @returns 箭头SVG元素
 */
function ArrowIcon() {
  return (
    <svg
      style={{ flexShrink: 0, opacity: 0.3 }}
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#86868B"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="5" y1="12" x2="19" y2="12"/>
      <polyline points="12 5 19 12 12 19"/>
    </svg>
  )
}

export default StrategyOverview
