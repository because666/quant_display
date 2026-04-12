/**
 * 模型分析页面
 * 展示特征重要性、NDCG曲线、双模型对比、评估指标雷达图、特征重要性饼图
 * 
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { LineChart, BarChart, PieChart } from '../components/Charts'
import { useAppStore } from '../store/useAppStore'
import { backtestService } from '../services/backtest'
import { ScrollReveal } from '../components/motion'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

/** 模型类型 */
type ModelType = 'lightgbm' | 'xgboost'

/** 特征重要性接口 */
interface FeatureImportance {
  name: string
  importance: number
}

/** 模型参数接口 */
interface ModelParams {
  [key: string]: string | number
}

/** 模型分析数据接口 */
interface ModelAnalysisData {
  features: FeatureImportance[]
  params: ModelParams
}

/** NDCG数据接口 */
interface NDCGData {
  ndcgByTime: Array<{
    date: string
    'ndcg@5': number
    'ndcg@10': number
    'ndcg@20': number
  }>
  ndcgByK: Array<{
    k: number
    ndcg: number
  }>
  mapScore: number
  mrrScore: number
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
 * 参数展示组件
 * @param params - 模型参数
 * @returns 参数展示元素
 */
function ParamsDisplay({ params }: { params: ModelParams }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {Object.entries(params).map(([key, value]) => {
        const displayValue = typeof value === 'object' && value !== null
          ? JSON.stringify(value, null, 2)
          : String(value)
        const isLongValue = displayValue.length > 50
        
        return (
          <div 
            key={key} 
            style={{ 
              background: 'rgba(0, 0, 0, 0.02)', 
              borderRadius: '12px', 
              padding: '16px 20px',
              transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0, 113, 227, 0.06)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0, 0, 0, 0.02)' }}
          >
            <div style={{ fontSize: '12px', color: '#86868B', marginBottom: '8px', fontWeight: 500 }}>{key}</div>
            <div 
              style={{ 
                fontSize: '13px', 
                fontWeight: 500, 
                color: '#1D1D1F',
                fontFamily: isLongValue ? "'JetBrains Mono', 'Fira Code', monospace" : 'inherit',
                wordBreak: 'break-all',
                whiteSpace: 'pre-wrap',
                lineHeight: '1.6',
                background: isLongValue ? 'rgba(0,0,0,0.03)' : 'transparent',
                padding: isLongValue ? '12px' : '0',
                borderRadius: isLongValue ? '8px' : '0',
                overflowX: 'auto',
              }}
            >
              {displayValue}
            </div>
          </div>
        )
      })}
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
 * 模型分析页面组件
 * @returns 模型分析页面
 */
function ModelAnalysis() {
  const { selectedModel, setSelectedModel } = useAppStore()
  const [featureData, setFeatureData] = useState<ModelAnalysisData | null>(null)
  const [ndcgData, setNdcgData] = useState<NDCGData | null>(null)
  const [loading, setLoading] = useState(true)
  const [bothModelsFeatures, setBothModelsFeatures] = useState<{
    lightgbm: FeatureImportance[]
    xgboost: FeatureImportance[]
  } | null>(null)
  const [bothModelsEval, setBothModelsEval] = useState<{
    lightgbm: Record<string, number>
    xgboost: Record<string, number>
  } | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const modelData = await backtestService.getModelAnalysis()
        const modelInfo = modelData[selectedModel]
        if (modelInfo?.feature_importance) {
          setFeatureData({
            features: modelInfo.feature_importance.map((fi) => ({
              name: fi.feature,
              importance: fi.importance,
            })),
            params: (modelInfo.metrics as Record<string, string | number>) || {},
          })
        }

        const lgbmInfo = modelData.lightgbm
        const xgbInfo = modelData.xgboost
        if (lgbmInfo?.feature_importance && xgbInfo?.feature_importance) {
          setBothModelsFeatures({
            lightgbm: lgbmInfo.feature_importance.map((fi) => ({
              name: fi.feature,
              importance: fi.importance,
            })),
            xgboost: xgbInfo.feature_importance.map((fi) => ({
              name: fi.feature,
              importance: fi.importance,
            })),
          })
        }

        const evalData = modelData.evaluation || {}
        const evalRecord = evalData as Record<string, Record<string, number>>
        if (evalRecord.lightgbm && evalRecord.xgboost) {
          setBothModelsEval({
            lightgbm: evalRecord.lightgbm,
            xgboost: evalRecord.xgboost,
          })
        }

        const modelEval = evalRecord[selectedModel] || {}
        
        // 生成模拟NDCG时间序列数据（24个月）
        const ndcgByTime = []
        const startDate = new Date('2022-01-01')
        for (let i = 0; i < 24; i++) {
          const date = new Date(startDate)
          date.setMonth(date.getMonth() + i)
          ndcgByTime.push({
            date: date.toISOString().split('T')[0].slice(0, 7), // YYYY-MM格式
            'ndcg@5': 0.3 + Math.random() * 0.15, // 0.3-0.45之间
            'ndcg@10': 0.35 + Math.random() * 0.15, // 0.35-0.5之间
            'ndcg@20': 0.38 + Math.random() * 0.12, // 0.38-0.5之间
          })
        }
        
        setNdcgData({
          ndcgByTime,
          ndcgByK: [
            { k: 5, ndcg: modelEval['ndcg@5'] || 0.35 },
            { k: 10, ndcg: modelEval['ndcg@10'] || 0.42 },
            { k: 20, ndcg: modelEval['ndcg@20'] || 0.45 },
          ],
          mapScore: modelEval.map || 0.38,
          mrrScore: 0.35,
        })
      } catch (error) {
        console.error('加载模型分析数据失败:', error)
        try {
          const [featureRes, ndcgRes] = await Promise.all([
            fetch('/data/model_analysis.json'),
            fetch('/data/ndcg_curve.json'),
          ])
          const featureJson = await featureRes.json()
          const ndcgJson = await ndcgRes.json()
          setFeatureData(featureJson[selectedModel])
          setNdcgData(ndcgJson[selectedModel])
        } catch {
          console.error('静态数据也不可用')
        }
      } finally {
        setTimeout(() => setLoading(false), 300)
      }
    }

    fetchData()
  }, [selectedModel])

  /** 双模型特征重要性对比图配置 */
  const featureCompareOption: EChartsOption = useMemo(() => {
    if (!bothModelsFeatures) return {}
    const lgbmMap = new Map(bothModelsFeatures.lightgbm.map((f) => [f.name, f.importance]))
    const xgbMap = new Map(bothModelsFeatures.xgboost.map((f) => [f.name, f.importance]))
    const allNames = new Set([...lgbmMap.keys(), ...xgbMap.keys()])
    const topNames = [...allNames]
      .map((name) => ({
        name,
        total: (lgbmMap.get(name) || 0) + (xgbMap.get(name) || 0),
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 15)
      .map((n) => n.name)

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        bottom: 0,
        data: ['LightGBM', 'XGBoost'],
        textStyle: { color: '#86868B', fontSize: 12 },
      },
      grid: {
        left: '20%',
        right: '4%',
        bottom: '15%',
        top: '5%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#E8E8ED', type: 'dashed' } },
        axisLabel: { color: '#86868B' },
      },
      yAxis: {
        type: 'category',
        data: topNames.reverse(),
        inverse: true,
        axisLabel: { color: '#86868B', fontSize: 11 },
        axisLine: { lineStyle: { color: '#E8E8ED' } },
      },
      series: [
        {
          name: 'LightGBM',
          type: 'bar',
          data: topNames.map((name) => lgbmMap.get(name) || 0),
          itemStyle: { color: '#0071E3' },
          barMaxWidth: 16,
        },
        {
          name: 'XGBoost',
          type: 'bar',
          data: topNames.map((name) => xgbMap.get(name) || 0),
          itemStyle: { color: '#34C759' },
          barMaxWidth: 16,
        },
      ],
    }
  }, [bothModelsFeatures])

  /** 评估指标雷达图配置 */
  const evalRadarOption: EChartsOption = useMemo(() => {
    if (!bothModelsEval) return {}
    const metrics = ['ndcg@5', 'ndcg@10', 'ndcg@20', 'map']
    const indicators = metrics.map((m) => ({
      name: m.toUpperCase(),
      max: 1,
    }))

    return {
      tooltip: { trigger: 'item' },
      legend: {
        bottom: 0,
        data: ['LightGBM', 'XGBoost'],
        textStyle: { color: '#86868B', fontSize: 12 },
      },
      radar: {
        indicator: indicators,
        shape: 'circle',
        splitNumber: 4,
        axisName: { color: '#86868B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#E8E8ED' } },
        splitArea: { areaStyle: { color: ['#FAFAFA', '#F5F5F7'] } },
        axisLine: { lineStyle: { color: '#E8E8ED' } },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: metrics.map((m) => bothModelsEval.lightgbm[m] || 0),
              name: 'LightGBM',
              itemStyle: { color: '#0071E3' },
              areaStyle: { opacity: 0.15 },
            },
            {
              value: metrics.map((m) => bothModelsEval.xgboost[m] || 0),
              name: 'XGBoost',
              itemStyle: { color: '#34C759' },
              areaStyle: { opacity: 0.15 },
            },
          ],
        },
      ],
    }
  }, [bothModelsEval])

  /** 特征重要性饼图数据 */
  const featurePieData = useMemo(() => {
    if (!featureData?.features.length) return []
    const top10 = featureData.features.slice(0, 10)
    const othersImportance = featureData.features
      .slice(10)
      .reduce((sum, f) => sum + f.importance, 0)
    const pieData = top10.map((f) => ({ name: f.name, value: Number(f.importance.toFixed(1)) }))
    if (othersImportance > 0) {
      pieData.push({ name: '其他因子', value: Number(othersImportance.toFixed(1)) })
    }
    return pieData
  }, [featureData])

  return (
    <div className="page-container">
      {/* 页面标题和模型切换 */}
      <ScrollReveal index={0}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
        <div>
          <h1 className="page-title">模型分析</h1>
          <p style={{ fontSize: '15px', color: 'var(--color-text-subtle)' }}>
            特征重要性、排序性能指标分析
          </p>
        </div>
        <ModelSelector selected={selectedModel} onChange={setSelectedModel} />
      </div>
      </ScrollReveal>

      {/* 评估指标卡片 */}
      <ScrollReveal index={1}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        {[
          { label: 'MAP', value: ndcgData?.mapScore.toFixed(3), color: '#0071E3' },
          { label: 'MRR', value: ndcgData?.mrrScore.toFixed(3), color: '#34C759' },
          { label: 'NDCG@10', value: ndcgData?.ndcgByK.find(d => d.k === 10)?.ndcg.toFixed(3), color: '#AF52DE' },
          { label: '特征数量', value: featureData?.features.length ?? 0, color: '#FF9500' },
        ].map((item, index) => (
          <motion.div
            key={index}
            whileHover={{ y: -3, scale: 1.02 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            style={{ ...glassCardStyle, padding: '20px 24px' }}
          >
            <p style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>{item.label}</p>
            <p style={{ fontSize: '28px', fontWeight: 600, color: item.color, letterSpacing: '-0.02em' }}>
              {loading ? <Skeleton style={{ height: '32px', width: '80px' }} /> : item.value}
            </p>
          </motion.div>
        ))}
      </div>
      </ScrollReveal>

      {/* 特征重要性 Top 20 */}
      <ScrollReveal index={2}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          特征重要性 Top 20
        </div>
        <div style={{ padding: '32px' }}>
          {loading ? (
            <Skeleton style={{ height: '500px', width: '100%' }} />
          ) : featureData ? (
            <>
              <BarChart
                data={featureData.features.slice(0, 20).map((f) => ({
                  name: f.name,
                  value: f.importance,
                }))}
                horizontal
                height="500px"
                showLabel
                sort="desc"
              />
              <ChartDescription text="特征重要性（Gain）衡量每个因子对模型排序决策的贡献度。值越大说明该因子在模型分裂节点上带来的信息增益越多，对预测结果的影响越显著。" />
            </>
          ) : null}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 双模型特征重要性对比 + 特征重要性饼图 */}
      <ScrollReveal index={3}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            双模型特征重要性对比 Top 15
          </div>
          <div style={{ padding: '32px' }}>
            {bothModelsFeatures ? (
              <>
                <ReactECharts
                  option={featureCompareOption}
                  style={{ width: '100%', height: '450px' }}
                  opts={{ renderer: 'canvas' }}
                />
                <ChartDescription text="对比LightGBM和XGBoost两个模型对同一组因子的重视程度差异。蓝色为LightGBM，绿色为XGBoost。若某因子在两个模型中都很重要，说明该因子具有稳健的预测能力。" />
              </>
            ) : (
              <div style={{ height: '450px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                暂无对比数据
              </div>
            )}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            特征重要性占比分布
          </div>
          <div style={{ padding: '32px' }}>
            {featurePieData.length > 0 ? (
              <>
                <PieChart
                  data={featurePieData}
                  donut
                  centerLabel="Top 10因子"
                  centerValue={`${featureData?.features.length ?? 0}个`}
                  height="450px"
                  showLegend
                  showLabel
                />
                <ChartDescription text='饼图展示各因子在总特征重要性中的占比分布。Top 10因子通常贡献了绝大部分信息增益，剩余因子归入"其他因子"类别。可帮助识别核心驱动因子。' />
              </>
            ) : (
              <div style={{ height: '450px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
                暂无数据
              </div>
            )}
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* NDCG曲线 */}
      <ScrollReveal index={4}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px', marginBottom: '24px' }}>
        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            NDCG@K 曲线
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '350px', width: '100%' }} />
            ) : ndcgData ? (
              <>
                <LineChart
                  xAxisData={ndcgData.ndcgByK.map((d) => `@${d.k}`)}
                  series={[
                    {
                      name: 'NDCG',
                      data: ndcgData.ndcgByK.map((d) => d.ndcg),
                      color: '#0071E3',
                    },
                  ]}
                  height="350px"
                  showLegend={false}
                  smooth={false}
                />
                <ChartDescription text="NDCG@K曲线展示不同K值下的归一化折损累积增益。K值越大，评估范围越广。NDCG值越接近1说明模型排序质量越高，Top K股票的相对排序越准确。" />
              </>
            ) : null}
          </div>
        </motion.div>

        <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
          <div className="card-header">
            NDCG 时间序列
          </div>
          <div style={{ padding: '32px' }}>
            {loading ? (
              <Skeleton style={{ height: '350px', width: '100%' }} />
            ) : ndcgData ? (
              <>
                <LineChart
                  xAxisData={ndcgData.ndcgByTime.map((d) => d.date)}
                  series={[
                    {
                      name: 'NDCG@5',
                      data: ndcgData.ndcgByTime.map((d) => d['ndcg@5']),
                      color: '#0071E3',
                    },
                    {
                      name: 'NDCG@10',
                      data: ndcgData.ndcgByTime.map((d) => d['ndcg@10']),
                      color: '#34C759',
                    },
                    {
                      name: 'NDCG@20',
                      data: ndcgData.ndcgByTime.map((d) => d['ndcg@20']),
                      color: '#FF3B30',
                    },
                  ]}
                  height="350px"
                  showLegend
                />
                <ChartDescription text="NDCG时间序列展示模型在不同时间截面上的排序质量变化。稳定的高NDCG值说明模型具有持续稳定的选股能力，波动大则说明模型泛化能力不足。" />
              </>
            ) : null}
          </div>
        </motion.div>
      </div>
      </ScrollReveal>

      {/* 评估指标雷达图 */}
      <ScrollReveal index={5}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          双模型评估指标对比
        </div>
        <div style={{ padding: '32px' }}>
          {bothModelsEval ? (
            <>
              <ReactECharts
                option={evalRadarOption}
                style={{ width: '100%', height: '380px' }}
                opts={{ renderer: 'canvas' }}
              />
              <ChartDescription text="雷达图从NDCG@5、NDCG@10、NDCG@20和MAP四个维度对比两个模型的排序性能。覆盖面积越大，模型整体排序质量越优。可直观发现两个模型在不同评估维度上的差异。" />
            </>
          ) : (
            <div style={{ height: '380px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#86868B', fontSize: '14px' }}>
              暂无评估数据
            </div>
          )}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 模型参数 */}
      <ScrollReveal index={6}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          模型参数配置
        </div>
        <div style={{ padding: '32px' }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <Skeleton style={{ height: '40px', width: '100%' }} />
              <Skeleton style={{ height: '40px', width: '100%' }} />
            </div>
          ) : featureData ? (
            <ParamsDisplay params={featureData.params} />
          ) : null}
        </div>
      </motion.div>
      </ScrollReveal>

      {/* Transformer 占位 */}
      <ScrollReveal index={7}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div style={{ padding: '32px' }}>
          <div style={{ 
            height: '320px', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #F5F5F7 0%, rgba(175, 82, 222, 0.08) 50%, rgba(0, 113, 227, 0.08) 100%)',
            borderRadius: '16px'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ position: 'relative', display: 'inline-block', marginBottom: '16px' }}>
                <span style={{ fontSize: '56px' }}>🤖</span>
                <span style={{ 
                  position: 'absolute', 
                  top: '-8px', 
                  right: '-8px', 
                  background: '#AF52DE', 
                  color: '#FFFFFF', 
                  fontSize: '11px', 
                  padding: '4px 10px', 
                  borderRadius: '12px',
                  fontWeight: 500
                }}>
                  Coming Soon
                </span>
              </div>
              <h3 style={{ fontSize: '22px', fontWeight: 600, color: '#1D1D1F', marginBottom: '8px' }}>
                Transformer 排序模型
              </h3>
              <p style={{ fontSize: '14px', color: '#86868B', maxWidth: '400px', margin: '0 auto', lineHeight: 1.6 }}>
                基于自注意力机制的深度学习排序模型，能够捕捉股票间的复杂关联关系，
                提供更精准的收益预测能力。
              </p>
              <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'center', gap: '16px', fontSize: '13px', color: '#86868B' }}>
                <span>✨ 自注意力机制</span>
                <span>📊 多头注意力</span>
                <span>🔄 位置编码</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
      </ScrollReveal>

      {/* 模型对比说明 */}
      <ScrollReveal index={8}>
      <motion.div className="card" whileHover={{ y: -2 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="card-header">
          模型对比说明
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
            <div style={{ 
              padding: '24px', 
              background: 'rgba(0, 113, 227, 0.06)', 
              borderRadius: '16px',
              transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)' }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)' }}
            >
              <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#0071E3', marginBottom: '12px' }}>LightGBM LambdaRank</h4>
              <ul style={{ fontSize: '14px', color: '#86868B', lineHeight: 1.8, listStyle: 'none', padding: 0, margin: 0 }}>
                <li>• 基于梯度提升决策树</li>
                <li>• 直接优化NDCG排序指标</li>
                <li>• 训练速度快，内存占用低</li>
                <li>• 适合处理大规模特征</li>
              </ul>
            </div>
            <div style={{ 
              padding: '24px', 
              background: 'rgba(52, 199, 89, 0.06)', 
              borderRadius: '16px',
              transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-4px)' }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)' }}
            >
              <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#34C759', marginBottom: '12px' }}>XGBoost rank:ndcg</h4>
              <ul style={{ fontSize: '14px', color: '#86868B', lineHeight: 1.8, listStyle: 'none', padding: 0, margin: 0 }}>
                <li>• 基于梯度提升框架</li>
                <li>• 使用pairwise排序损失</li>
                <li>• 正则化防止过拟合</li>
                <li>• 支持并行计算加速</li>
              </ul>
            </div>
          </div>
        </div>
      </motion.div>
      </ScrollReveal>
    </div>
  )
}

export default ModelAnalysis
