/**
 * 响应式图表容器组件
 * 自动监听窗口大小变化，触发图表重新渲染
 */
import { memo, useState, useEffect, useRef, type ReactNode } from 'react'

export interface ResponsiveChartProps {
  /** 子组件 */
  children: ReactNode
  /** 最小宽度 */
  minWidth?: number
  /** 最小高度 */
  minHeight?: number
  /** 宽度 */
  width?: string | number
  /** 高度 */
  height?: string | number
  /** 类名 */
  className?: string
}

function ResponsiveChartComponent({
  children,
  minWidth = 300,
  minHeight = 200,
  width = '100%',
  height = '400px',
  className = '',
}: ResponsiveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { offsetWidth, offsetHeight } = containerRef.current
        setDimensions({
          width: Math.max(offsetWidth, minWidth),
          height: Math.max(offsetHeight, minHeight),
        })
      }
    }

    updateDimensions()

    const resizeObserver = new ResizeObserver(() => {
      updateDimensions()
    })

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    window.addEventListener('resize', updateDimensions)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateDimensions)
    }
  }, [minWidth, minHeight])

  return (
    <div
      ref={containerRef}
      className={`responsive-chart ${className}`}
      style={{
        width,
        height,
        minWidth,
        minHeight,
      }}
      data-width={dimensions.width}
      data-height={dimensions.height}
    >
      {children}
    </div>
  )
}

const ResponsiveChart = memo(ResponsiveChartComponent)

export default ResponsiveChart
