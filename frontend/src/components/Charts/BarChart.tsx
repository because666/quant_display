/**
 * 条形图组件
 * 支持横向和纵向条形图，用于特征重要性展示
 */
import { memo, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

export interface BarChartProps {
  /** 数据 */
  data: Array<{
    name: string
    value: number
    color?: string
  }>
  /** 图表标题 */
  title?: string
  /** 是否横向 */
  horizontal?: boolean
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 是否显示工具提示 */
  showTooltip?: boolean
  /** 是否显示数值标签 */
  showLabel?: boolean
  /** 排序方式 */
  sort?: 'asc' | 'desc' | 'none'
  /** X轴单位 */
  xAxisUnit?: string
  /** 加载状态 */
  loading?: boolean
  /** 是否暗色主题 */
  isDark?: boolean
}

const COLORS_LIGHT = [
  '#2563eb',
  '#16a34a',
  '#dc2626',
  '#9333ea',
  '#ea580c',
  '#0891b2',
  '#4f46e5',
  '#be185d',
]

const COLORS_DARK = [
  '#3b82f6',
  '#22c55e',
  '#ef4444',
  '#a855f7',
  '#f97316',
  '#06b6d4',
  '#6366f1',
  '#ec4899',
]

function BarChartComponent({
  data,
  title,
  horizontal = true,
  width = '100%',
  height = '400px',
  showTooltip = true,
  showLabel = true,
  sort = 'desc',
  xAxisUnit = '',
  loading = false,
  isDark = false,
}: BarChartProps) {
  const colors = isDark ? COLORS_DARK : COLORS_LIGHT
  const textColor = isDark ? '#f1f5f9' : '#0f172a'
  const textSubtleColor = isDark ? '#94a3b8' : '#64748b'
  const borderColor = isDark ? '#334155' : '#e2e8f0'
  const bgColor = isDark ? '#1e293b' : '#ffffff'

  const sortedData = useMemo(() => {
    if (sort === 'none') return data
    return [...data].sort((a, b) => (sort === 'desc' ? b.value - a.value : a.value - b.value))
  }, [data, sort])

  const option: EChartsOption = useMemo(() => {
    const names = sortedData.map((d) => d.name)
    const values = sortedData.map((d) => d.value)
    const itemColors = sortedData.map((d, i) => d.color || colors[i % colors.length])

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
      tooltip: showTooltip
        ? {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow',
            },
            backgroundColor: bgColor,
            borderColor: borderColor,
            textStyle: {
              color: textColor,
            },
          }
        : undefined,
      grid: {
        left: horizontal ? '20%' : '3%',
        right: '4%',
        bottom: horizontal ? '3%' : '15%',
        top: title ? '15%' : '10%',
        containLabel: true,
      },
      xAxis: horizontal
        ? {
            type: 'value',
            axisLabel: {
              formatter: xAxisUnit ? `{value}${xAxisUnit}` : undefined,
              color: textSubtleColor,
            },
            splitLine: {
              lineStyle: {
                color: borderColor,
                type: 'dashed',
              },
            },
          }
        : {
            type: 'category',
            data: names,
            axisLabel: {
              rotate: 45,
              color: textSubtleColor,
            },
            axisLine: {
              lineStyle: {
                color: borderColor,
              },
            },
          },
      yAxis: horizontal
        ? {
            type: 'category',
            data: names,
            inverse: true,
            axisLabel: {
              color: textSubtleColor,
            },
            axisLine: {
              lineStyle: {
                color: borderColor,
              },
            },
          }
        : {
            type: 'value',
            axisLabel: {
              formatter: xAxisUnit ? `{value}${xAxisUnit}` : undefined,
              color: textSubtleColor,
            },
            splitLine: {
              lineStyle: {
                color: borderColor,
                type: 'dashed',
              },
            },
          },
      series: [
        {
          type: 'bar',
          data: values.map((value, index) => ({
            value,
            itemStyle: {
              color: itemColors[index],
            },
          })),
          label: showLabel
            ? {
                show: true,
                position: horizontal ? 'right' : 'top',
                formatter: '{c}',
                color: textSubtleColor,
              }
            : undefined,
          barMaxWidth: 40,
        },
      ],
    }
  }, [
    sortedData,
    title,
    horizontal,
    showTooltip,
    showLabel,
    xAxisUnit,
    isDark,
    colors,
    textColor,
    textSubtleColor,
    borderColor,
    bgColor,
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

const BarChart = memo(BarChartComponent)

export default BarChart
