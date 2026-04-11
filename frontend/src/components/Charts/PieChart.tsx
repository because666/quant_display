/**
 * 饼图组件
 * 基于ECharts封装，支持饼图和环形图，用于持仓分布、数据集划分等场景
 */
import { memo, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

export interface PieChartProps {
  /** 数据项 */
  data: Array<{
    name: string
    value: number
  }>
  /** 图表标题 */
  title?: string
  /** 是否环形图 */
  donut?: boolean
  /** 环形图中心文字 */
  centerLabel?: string
  /** 环形图中心数值 */
  centerValue?: string
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 是否显示图例 */
  showLegend?: boolean
  /** 是否显示标签 */
  showLabel?: boolean
  /** 标签位置：outer-外侧, inside-内部, center-中心(仅环形图) */
  labelPosition?: 'outer' | 'inside' | 'center'
  /** 是否显示引导线 */
  showLabelLine?: boolean
  /** 加载状态 */
  loading?: boolean
  /** 是否暗色主题 */
  isDark?: boolean
}

const COLORS = [
  '#2563eb',
  '#16a34a',
  '#dc2626',
  '#9333ea',
  '#ea580c',
  '#0891b2',
  '#4f46e5',
  '#be185d',
  '#65a30d',
  '#0d9488',
  '#c026d3',
  '#e11d48',
]

function PieChartComponent({
  data,
  title,
  donut = false,
  centerLabel,
  centerValue,
  width = '100%',
  height = '400px',
  showLegend = true,
  showLabel = true,
  labelPosition = 'outer',
  showLabelLine = true,
  loading = false,
  isDark = false,
}: PieChartProps) {
  const textColor = isDark ? '#f1f5f9' : '#0f172a'
  const textSubtleColor = isDark ? '#94a3b8' : '#64748b'
  const bgColor = isDark ? '#1e293b' : '#ffffff'

  const option: EChartsOption = useMemo(() => {
    return {
      backgroundColor: bgColor,
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: {
              fontSize: 16,
              fontWeight: 600,
              color: textColor,
            },
          }
        : undefined,
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        backgroundColor: bgColor,
        borderColor: isDark ? '#475569' : '#e2e8f0',
        textStyle: {
          color: textColor,
        },
      },
      legend: showLegend
        ? {
            bottom: 0,
            type: 'scroll',
            textStyle: {
              color: textSubtleColor,
              fontSize: 12,
            },
          }
        : undefined,
      graphic: donut && (centerLabel || centerValue)
        ? [
            {
              type: 'text',
              left: 'center',
              top: 'center',
              style: {
                text: centerValue || '',
                fontSize: 24,
                fontWeight: 700,
                fill: textColor,
                textAlign: 'center',
              },
            },
            {
              type: 'text',
              left: 'center',
              top: 'center',
              style: {
                text: centerLabel || '',
                fontSize: 12,
                fill: textSubtleColor,
                textAlign: 'center',
                y: centerValue ? 20 : 0,
              },
            },
          ]
        : undefined,
      series: [
        {
          type: 'pie',
          radius: donut ? ['45%', '70%'] : [0, '70%'],
          center: ['50%', '48%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: donut ? 6 : 0,
            borderColor: bgColor,
            borderWidth: 2,
          },
          label: showLabel
            ? {
                show: true,
                position: labelPosition,
                formatter: '{b}\n{d}%',
                fontSize: 11,
                color: textSubtleColor,
              }
            : { show: false },
          labelLine: showLabelLine
            ? {
                show: true,
                length: 15,
                length2: 10,
              }
            : { show: false },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold',
            },
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.2)',
            },
          },
          data: data.map((d, i) => ({
            name: d.name,
            value: d.value,
            itemStyle: {
              color: COLORS[i % COLORS.length],
            },
          })),
        },
      ],
    }
  }, [
    data, title, donut, centerLabel, centerValue, showLegend,
    showLabel, labelPosition, showLabelLine, isDark,
    textColor, textSubtleColor, bgColor,
  ])

  return (
    <ReactECharts
      option={option}
      style={{ width, height }}
      showLoading={loading}
      opts={{ renderer: 'canvas' }}
    />
  )
}

const PieChart = memo(PieChartComponent)

export default PieChart
