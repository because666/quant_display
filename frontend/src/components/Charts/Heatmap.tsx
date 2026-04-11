/**
 * 热力图组件
 * 基于ECharts封装，用于月度收益热力图，支持暗色主题
 */
import { useEffect, useRef, useMemo } from 'react'
import * as echarts from 'echarts'

export interface HeatmapProps {
  /** 数据矩阵 */
  data: number[][]
  /** X轴标签 */
  xLabels: string[]
  /** Y轴标签 */
  yLabels: string[]
  /** 图表标题 */
  title?: string
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 颜色范围 */
  colorRange?: [number, number]
  /** 颜色方案 */
  colorscale?: string
  /** 加载状态 */
  loading?: boolean
  /** 是否暗色主题 */
  isDark?: boolean
}

function Heatmap({
  data,
  xLabels,
  yLabels,
  title,
  width = '100%',
  height = '400px',
  colorRange,
  loading = false,
  isDark = false,
}: HeatmapProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  const textColor = isDark ? '#f1f5f9' : '#0f172a'
  const textSubtleColor = isDark ? '#94a3b8' : '#64748b'
  const bgColor = isDark ? '#1e293b' : '#ffffff'

  const chartData = useMemo(() => {
    const result: Array<[number, number, number]> = []
    data.forEach((row, rowIndex) => {
      row.forEach((value, colIndex) => {
        result.push([colIndex, rowIndex, value])
      })
    })
    return result
  }, [data])

  const minVal = useMemo(() => {
    if (colorRange) return colorRange[0]
    let min = Infinity
    data.forEach(row => {
      row.forEach(val => {
        if (val < min) min = val
      })
    })
    return min === Infinity ? 0 : min
  }, [data, colorRange])

  const maxVal = useMemo(() => {
    if (colorRange) return colorRange[1]
    let max = -Infinity
    data.forEach(row => {
      row.forEach(val => {
        if (val > max) max = val
      })
    })
    return max === -Infinity ? 0 : max
  }, [data, colorRange])

  useEffect(() => {
    if (!chartRef.current || loading) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, isDark ? 'dark' : undefined)
    }

    const option: echarts.EChartsOption = {
      backgroundColor: bgColor,
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: {
              color: textColor,
              fontSize: 16,
              fontWeight: 600,
            },
          }
        : undefined,
      tooltip: {
        position: 'top',
        formatter: (params: unknown) => {
          const p = params as { data: [number, number, number] }
          const [xIdx, yIdx, value] = p.data
          const percent = (value * 100).toFixed(2)
          return `${yLabels[yIdx]}<br/>${xLabels[xIdx]}<br/>收益率: ${percent}%`
        },
        backgroundColor: isDark ? '#334155' : '#ffffff',
        borderColor: isDark ? '#475569' : '#e2e8f0',
        textStyle: {
          color: textColor,
        },
      },
      grid: {
        left: 80,
        right: 40,
        top: title ? 60 : 40,
        bottom: 60,
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        axisLabel: {
          color: textSubtleColor,
          rotate: -45,
        },
        axisLine: {
          lineStyle: {
            color: textSubtleColor,
          },
        },
        splitLine: {
          show: false,
        },
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        axisLabel: {
          color: textSubtleColor,
        },
        axisLine: {
          lineStyle: {
            color: textSubtleColor,
          },
        },
        splitLine: {
          show: false,
        },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 10,
        inRange: {
          color: ['#ef4444', '#fbbf24', '#22c55e'],
        },
        text: ['高', '低'],
        textStyle: {
          color: textSubtleColor,
        },
      },
      series: [
        {
          type: 'heatmap',
          data: chartData,
          label: {
            show: false,
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)',
            },
          },
        },
      ],
    }

    chartInstance.current.setOption(option, true)

    const handleResize = () => {
      chartInstance.current?.resize()
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [chartData, xLabels, yLabels, title, minVal, maxVal, loading, isDark, textColor, textSubtleColor, bgColor])

  useEffect(() => {
    return () => {
      chartInstance.current?.dispose()
      chartInstance.current = null
    }
  }, [])

  useEffect(() => {
    chartInstance.current?.resize()
  }, [width, height])

  if (loading) {
    return (
      <div
        style={{ width, height, minHeight: '300px' }}
        className={`flex items-center justify-center rounded ${
          isDark ? 'bg-slate-800' : 'bg-gray-50'
        }`}
      >
        <span className={isDark ? 'text-slate-400' : 'text-gray-400'}>加载中...</span>
      </div>
    )
  }

  return (
    <div
      ref={chartRef}
      style={{ width, height, minHeight: '300px' }}
    />
  )
}

export default Heatmap
