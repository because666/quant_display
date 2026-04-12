/**
 * 滚动揭示动画组件
 * 当元素进入视口时触发淡入上浮效果，支持交错延迟
 *
 * @param children - 子元素
 * @param index - 用于计算交错延迟的索引
 * @param direction - 动画方向，默认 'up'
 * @param delay - 额外延迟时间(ms)，默认 0
 * @param distance - 移动距离(px)，默认 30
 * @param once - 是否只触发一次，默认 true
 * @param className - 自定义类名
 * @param style - 自定义样式
 */
import { useRef, type ReactNode } from 'react'
import { motion, useInView } from 'framer-motion'

type ScrollRevealProps = {
  children: ReactNode
  index?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
  delay?: number
  distance?: number
  once?: boolean
  className?: string
  style?: React.CSSProperties
}

const directionMap = {
  up: { y: 1, x: 0 },
  down: { y: -1, x: 0 },
  left: { x: 1, y: 0 },
  right: { x: -1, y: 0 },
  none: { x: 0, y: 0 },
}

function ScrollReveal({
  children,
  index = 0,
  direction = 'up',
  delay = 0,
  distance = 30,
  once = true,
  className,
  style,
}: ScrollRevealProps) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once, margin: '-60px' })
  const dir = directionMap[direction]

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: dir.x * distance, y: dir.y * distance }}
      animate={isInView ? { opacity: 1, x: 0, y: 0 } : {}}
      transition={{
        duration: 0.5,
        delay: index * 0.08 + delay,
        ease: [0.22, 1, 0.36, 1],
      }}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  )
}

export default ScrollReveal
