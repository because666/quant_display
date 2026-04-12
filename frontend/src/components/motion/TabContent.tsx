/**
 * Tab内容切换动画组件
 * Tab切换时提供平滑的淡入淡出+位移过渡效果
 *
 * @param activeTab - 当前激活的Tab键
 * @param tabs - 各Tab对应的内容映射
 * @param className - 自定义类名
 */
import { type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface TabContentProps {
  activeTab: string
  tabs: Record<string, ReactNode>
  className?: string
}

function TabContent({ activeTab, tabs, className }: TabContentProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className={className}
      >
        {tabs[activeTab]}
      </motion.div>
    </AnimatePresence>
  )
}

export default TabContent
