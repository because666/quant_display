/**
 * 折线图组件
 * 基于ECharts封装，支持多系列数据和暗色主题
 */
import { memo, useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

export interface LineChartProps {
  /** X轴数据（日期） */
  xAxisData: string[]
  /** 系列数据 */
  series: Array<{
    name: string
    data: number[]
    color?: string
  }>
  /** 图表标题 */
  title?: string
  /** 是否显示图例 */
  showLegend?: boolean
  /** 是否显示工具提示 */
  showTooltip?: boolean
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 是否平滑曲线 */
  smooth?: boolean
  /** 是否显示区域填充 */
  areaStyle?: boolean
  /** Y轴单位 */
  yAxisUnit?: string
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

function LineChartComponent({
  xAxisData,
  series,
  title,
  showLegend = true,
  showTooltip = true,
  width = '100%',
  height = '400px',
  smooth = true,
  areaStyle = false,
  yAxisUnit = '',
  loading = false,
  isDark = false,
}: LineChartProps) {
  const colors = isDark ? COLORS_DARK : COLORS_LIGHT
  const textColor = isDark ? '#f1f5f9' : '#0f172a'
  const textSubtleColor = isDark ? '#94a3b8' : '#64748b'
  const borderColor = isDark ? '#334155' : '#e2e8f0'
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
      tooltip: showTooltip
        ? {
            trigger: 'axis',
            axisPointer: {
              type: 'cross',
            },
            backgroundColor: bgColor,
            borderColor: borderColor,
            textStyle: {
              color: textColor,
            },
          }
        : undefined,
      legend: showLegend
        ? {
            bottom: 0,
            data: series.map((s) => s.name),
            textStyle: {
              color: textSubtleColor,
            },
          }
        : undefined,
      grid: {
        left: '3%',
        right: '4%',
        bottom: showLegend ? '15%' : '3%',
        top: title ? '15%' : '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: xAxisData,
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
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: yAxisUnit ? `{value}${yAxisUnit}` : undefined,
          color: textSubtleColor,
        },
        splitLine: {
          lineStyle: {
            color: borderColor,
            type: 'dashed',
          },
        },
      },
      series: series.map((s, index) => ({
        name: s.name,
        type: 'line',
        smooth,
        data: s.data,
        itemStyle: {
          color: s.color || colors[index % colors.length],
        },
        areaStyle: areaStyle
          ? {
              opacity: isDark ? 0.2 : 0.1,
            }
          : undefined,
        emphasis: {
          focus: 'series',
        },
      })),
    }
  }, [
    xAxisData,
    series,
    title,
    showLegend,
    showTooltip,
    smooth,
    areaStyle,
    yAxisUnit,
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

const LineChart = memo(LineChartComponent)

export default LineChart
