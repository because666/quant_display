/**
 * 页面过渡动画组件
 * 路由切换时提供平滑的淡入+上浮过渡效果
 *
 * @param pageKey - 页面唯一标识（用于触发重新动画）
 * @param children - 页面内容
 * @param className - 自定义类名
 */
import { type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface PageTransitionProps {
  pageKey: string
  children: ReactNode
  className?: string
}

function PageTransition({ pageKey, children, className }: PageTransitionProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pageKey}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

export default PageTransition
