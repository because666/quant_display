/**
 * 策略概览页面
 * 融合 Anti-AI 美学 + Purposeful Motion 设计理念
 * Space Grotesk 字体 / 滚动揭示动画 / 弹簧物理交互 / 大气数据深度感
 *
 * @author 量化策略系统
 * @version 2.0
 */
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { PieChart } from '../components/Charts'
import { ScrollReveal, RippleButton } from '../components/motion'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

/**
 * 图表说明组件
 * @param text - 说明文字
 */
function ChartDescription({ text }: { text: string }) {
  return (
    <p style={{ fontSize: '12px', color: '#86868B', marginTop: '10px', lineHeight: '1.6' }}>{text}</p>
  )
}

function StrategyOverview() {
  const navigate = useNavigate()

  const techStack = [
    { name: 'React 18', category: '前端' },
    { name: 'TypeScript', category: '前端' },
    { name: 'TailwindCSS', category: '前端' },
    { name: 'ECharts', category: '可视化' },
    { name: 'FastAPI', category: '后端' },
    { name: 'LightGBM', category: '模型' },
    { name: 'XGBoost', category: '模型' },
    { name: 'Pandas', category: '数据处理' },
    { name: 'DeepSeek', category: 'AI服务' },
    { name: 'SQLite', category: '数据库' },
  ]

  const gaugeOption: EChartsOption = {
    series: [{
      type: 'gauge',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: 100,
      splitNumber: 10,
      itemStyle: { color: '#0071E3' },
      progress: { show: true, width: 18 },
      pointer: { show: false },
      axisLine: { lineStyle: { width: 18, color: [[1, '#E8E8ED']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      title: { fontSize: 13, color: '#86868B', offsetCenter: [0, '70%'] },
      detail: { fontSize: 28, fontWeight: 600, color: '#1D1D1F', offsetCenter: [0, '30%'], formatter: '{value}%' },
      data: [{ value: 18.5, name: '年化收益率' }],
    }],
  }

  const datasetPieData = [
    { name: '训练集 (2014-2019)', value: 60 },
    { name: '验证集 (2020-2021)', value: 20 },
    { name: '测试集 (2022-2024)', value: 20 },
  ]

  const factorCategoryPieData = [
    { name: '动量因子', value: 6 },
    { name: '波动因子', value: 4 },
    { name: '流动性因子', value: 3 },
    { name: '技术指标', value: 5 },
    { name: '估值因子', value: 2 },
  ]

  const statsData = [
    { icon: '📅', value: '10', unit: '年+', label: '数据时间范围', sub: '2014 - 2024' },
    { icon: '📊', value: '2,258', unit: '只', label: '股票池规模', sub: '存续A股' },
    { icon: '⏱️', value: '周频', unit: '', label: '调仓频率', sub: '每周调仓' },
    { icon: '🤖', value: '双模型', unit: '', label: '预测模型', sub: 'LightGBM + XGBoost' },
  ]

  const frameworkItems = [
    { icon: '📅', title: 'T+1交易规则', desc: '当日买入，次日方可卖出' },
    { icon: '💰', title: '交易成本', desc: '印花税0.05% + 佣金0.03%' },
    { icon: '📊', title: '滑点设置', desc: '双边0.1%' },
    { icon: '🚫', title: '涨跌停限制', desc: '涨停无法买入，跌停无法卖出' },
  ]

  return (
    <div className="page-container">
      {/* Hero区域 */}
      <section className="hero-section">
        <ScrollReveal index={0}>
          <div className="hero-badge">
            <span style={{ fontSize: '14px' }}>Learning to Rank 驱动</span>
          </div>
        </ScrollReveal>

        <ScrollReveal index={1}>
          <h1 className="hero-title">
            基于排序学习的
            <br />
            <span style={{ color: 'var(--color-primary)' }}>量化投资选股策略</span>
          </h1>
        </ScrollReveal>

        <ScrollReveal index={2}>
          <p className="hero-desc">
            运用机器学习排序算法，构建A股市场智能选股系统
          </p>
        </ScrollReveal>

        <ScrollReveal index={3}>
          <div className="hero-actions">
            <RippleButton variant="primary" size="lg" onClick={() => navigate('/ai')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              开始使用
            </RippleButton>
            <RippleButton variant="outline" size="lg" onClick={() => navigate('/backtest')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 13L8 8L13 13L21 5M21 11V19H3V5"/>
              </svg>
              查看回测
            </RippleButton>
          </div>
        </ScrollReveal>
      </section>

      {/* 核心指标卡片 */}
      <ScrollReveal index={4}>
        <div className="stats-grid">
          {statsData.map((stat) => (
            <motion.div
              key={stat.label}
              className="stat-card"
              whileHover={{ y: -3, scale: 1.01 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            >
              <motion.div
                className="stat-card-icon"
                whileHover={{ scale: 1.08, rotate: -3 }}
                transition={{ type: 'spring', stiffness: 500, damping: 20 }}
              >
                {stat.icon}
              </motion.div>
              <div>
                <p className="stat-value">
                  {stat.value}
                  {stat.unit && <span style={{ fontSize: '18px', fontWeight: 500, opacity: 0.7 }}>{stat.unit}</span>}
                </p>
                <p className="stat-label">{stat.label}</p>
                <p className="stat-sub">{stat.sub}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </ScrollReveal>

      {/* 核心指标仪表盘 + 数据集划分 */}
      <ScrollReveal index={5}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '32px' }}>
          <div className="card">
            <div className="card-header">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0071E3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/>
              </svg>
              核心策略指标
            </div>
            <div className="card-body">
              <ReactECharts option={gaugeOption} style={{ width: '100%', height: '280px' }} opts={{ renderer: 'canvas' }} />
              <ChartDescription text="仪表盘展示策略的核心年化收益率指标。该指标反映策略在回测期间的年均复合增长率，是衡量策略盈利能力的首要指标。" />
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0071E3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.21 15.89A10 10 0 118 2.83"/>
                <path d="M22 12A10 10 0 0012 2v10z"/>
              </svg>
              数据集划分
            </div>
            <div className="card-body">
              <PieChart data={datasetPieData} donut centerLabel="数据占比" centerValue="10年" height="280px" showLegend showLabel />
              <ChartDescription text="数据集按时间划分为训练集、验证集和测试集。训练集用于模型学习，验证集用于超参调优，测试集用于最终评估，确保无未来信息泄露。" />
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* 模型架构图 */}
      <ScrollReveal index={6}>
        <div className="card" style={{ marginBottom: '32px' }}>
          <div className="card-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0071E3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
              <path d="M9 9h6v6H9z"/>
            </svg>
            模型架构
          </div>
          <div style={{ padding: '48px 32px' }} className="architecture-flow">
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
      </ScrollReveal>

      {/* 核心算法介绍 */}
      <ScrollReveal index={7}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '32px' }}>
          <div className="card">
            <div className="card-header">
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0071E3' }}></span>
              LightGBM LambdaRank
            </div>
            <div className="card-body">
              <p style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--color-text-subtle)', marginBottom: '24px' }}>
                LightGBM是一种高效的梯度提升决策树算法，LambdaRank是专门用于排序任务的损失函数。
              </p>
              <div className="info-box info-box-neutral" style={{ marginBottom: '16px' }}>
                <h4 style={{ fontWeight: 600, marginBottom: '10px', fontSize: '14px', color: 'var(--color-text)' }}>核心优势</h4>
                <ul className="feature-list">
                  <li>训练速度快，内存占用低</li>
                  <li>直接优化NDCG排序指标</li>
                  <li>支持类别特征，无需独热编码</li>
                  <li>叶子生长策略，精度更高</li>
                </ul>
              </div>
              <div className="code-box code-box-primary">
                <h4 style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: 'var(--color-primary)' }}>模型配置</h4>
                <pre style={{ margin: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-text-muted)' }}>
{`objective: lambdarank
num_leaves: 31
learning_rate: 0.05`}
                </pre>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-success)' }}></span>
              XGBoost rank:ndcg
            </div>
            <div className="card-body">
              <p style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--color-text-subtle)', marginBottom: '24px' }}>
                XGBoost是另一种流行的梯度提升框架，rank:ndcg目标函数专门用于学习排序任务。
              </p>
              <div className="info-box info-box-neutral" style={{ marginBottom: '16px' }}>
                <h4 style={{ fontWeight: 600, marginBottom: '10px', fontSize: '14px', color: 'var(--color-text)' }}>核心优势</h4>
                <ul className="feature-list">
                  <li>正则化防止过拟合</li>
                  <li>支持并行计算</li>
                  <li>内置处理缺失值</li>
                  <li>丰富的调参选项</li>
                </ul>
              </div>
              <div className="code-box code-box-success">
                <h4 style={{ fontWeight: 600, marginBottom: '8px', fontSize: '13px', color: 'var(--color-success)' }}>模型配置</h4>
                <pre style={{ margin: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--color-text-muted)' }}>
{`objective: rank:ndcg
max_depth: 6
learning_rate: 0.05`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* 因子类别分布 + 数据范围 + 回测框架 */}
      <ScrollReveal index={8}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', marginBottom: '32px' }}>
          <div className="card">
            <div className="card-header">因子类别分布</div>
            <div className="card-body">
              <PieChart data={factorCategoryPieData} donut centerLabel="因子总数" centerValue="20个" height="280px" showLegend showLabel />
              <ChartDescription text="饼图展示各类因子在总因子池中的数量占比。动量因子和技术指标因子占比较大，反映了策略对价格趋势的重视。" />
            </div>
          </div>

          <div className="card">
            <div className="card-header">数据范围</div>
            <div className="card-body">
              <div className="data-list">
                {[
                  { label: '时间跨度', value: '2014-01 ~ 2024-12' },
                  { label: '股票池', value: '2,258只存续A股' },
                  { label: '数据频率', value: '周频截面' },
                  { label: '训练集', value: '2014-2019' },
                  { label: '验证集', value: '2020-2021' },
                  { label: '测试集', value: '2022-2024' },
                ].map((item) => (
                  <div key={item.label} className="data-row">
                    <span className="data-label">{item.label}</span>
                    <span className="data-value">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">回测框架</div>
            <div className="card-body">
              <div className="framework-list">
                {frameworkItems.map((item) => (
                  <motion.div
                    key={item.title}
                    className="framework-item"
                    whileHover={{ x: 4, backgroundColor: 'rgba(0, 113, 227, 0.06)' }}
                    transition={{ duration: 0.2 }}
                  >
                    <span className="framework-icon">{item.icon}</span>
                    <div>
                      <p className="framework-title">{item.title}</p>
                      <p className="framework-desc">{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* 技术栈 */}
      <ScrollReveal index={9}>
        <div className="card" style={{ marginBottom: '32px' }}>
          <div className="card-header">技术栈</div>
          <div className="card-body">
            <div className="tech-grid">
              {techStack.map((tech) => (
                <motion.span
                  key={tech.name}
                  className="tech-badge"
                  whileHover={{ y: -2, scale: 1.03 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 17 }}
                >
                  {tech.name}
                  <span className="tech-category">{tech.category}</span>
                </motion.span>
              ))}
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* CTA区域 */}
      <ScrollReveal index={10}>
        <div className="cta-section">
          <div className="cta-content">
            <h2 className="cta-title">准备好开始了吗？</h2>
            <p className="cta-desc">查看AI智能推荐，获取最新投资建议</p>
            <RippleButton variant="primary" size="lg" onClick={() => navigate('/ai')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              立即开始
            </RippleButton>
          </div>
          <div className="cta-bg-pattern" />
        </div>
      </ScrollReveal>
    </div>
  )
}

function ArchNode({ emoji, label, color, desc }: { emoji: string; label: string; color: string; desc: string[] }) {
  const colors: Record<string, string> = {
    blue: 'rgba(0, 113, 227, 0.08)',
    green: 'rgba(52, 199, 89, 0.08)',
    purple: 'rgba(175, 82, 222, 0.08)',
    orange: 'rgba(255, 149, 0, 0.08)',
    pink: 'rgba(255, 55, 95, 0.08)',
  }

  return (
    <motion.div
      className="arch-node"
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <motion.div
        className="arch-node-box"
        style={{ background: colors[color] }}
        whileHover={{ scale: 1.06 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      >
        <span className="arch-node-emoji">{emoji}</span>
        <span className="arch-node-label">{label}</span>
      </motion.div>
      <p className="arch-node-desc">{desc.join(' / ')}</p>
    </motion.div>
  )
}

function ArrowIcon() {
  return (
    <svg className="arch-arrow" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"/>
      <polyline points="12 5 19 12 12 19"/>
    </svg>
  )
}

export default StrategyOverview
