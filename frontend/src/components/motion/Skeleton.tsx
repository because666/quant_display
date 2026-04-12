/**
 * 卡片骨架屏组件
 * 数据加载时展示骨架屏占位，保留布局结构的同时提供视觉反馈
 *
 * @param variant - 骨架屏变体：card/chart/table/stat
 * @param lines - 文本行数（仅table类型）
 * @param className - 自定义类名
 */
import { motion } from 'framer-motion'

type SkeletonVariant = 'card' | 'chart' | 'table' | 'stat'

interface SkeletonProps {
  variant?: SkeletonVariant
  lines?: number
  className?: string
}

function Skeleton({ variant = 'card', lines = 6, className = '' }: SkeletonProps) {
  const content = (() => {
    switch (variant) {
      case 'card':
        return (
          <div className="skeleton-card">
            <div className="skeleton skeleton-line" style={{ height: 16, width: '40%', marginBottom: 20 }} />
            <div className="skeleton skeleton-chart" />
            <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
              <div className="skeleton skeleton-line" style={{ flex: 1 }} />
              <div className="skeleton skeleton-line skeleton-line-short" style={{ width: 100 }} />
            </div>
          </div>
        )

      case 'chart':
        return (
          <div style={{ borderRadius: 24, padding: 32, background: 'var(--color-surface)', boxShadow: 'var(--shadow-lg)' }}>
            <div className="skeleton skeleton-line" style={{ height: 14, width: '35%', marginBottom: 24 }} />
            <div className="skeleton skeleton-chart" />
          </div>
        )

      case 'table':
        return (
          <div className="animate-pulse" style={{ borderRadius: 24 }}>
            <div style={{ display: 'flex', gap: 12, padding: '14px 20px', borderBottom: '1px solid var(--color-border-light)' }}>
              <div className="skeleton" style={{ width: 80, height: 14, borderRadius: 7 }} />
              <div className="skeleton" style={{ flex: 1, height: 14, borderRadius: 7 }} />
              <div className="skeleton" style={{ width: 60, height: 14, borderRadius: 7 }} />
              <div className="skeleton" style={{ width: 80, height: 14, borderRadius: 7 }} />
            </div>
            {Array.from({ length: lines }).map((_, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: '14px 20px',
                  borderBottom: i < lines - 1 ? '1px solid var(--color-border-light)' : 'none',
                }}
              >
                <div className="skeleton" style={{ width: 80, height: 14, borderRadius: 7 }} />
                <div className="skeleton" style={{ flex: 1, height: 14, borderRadius: 7 }} />
                <div className="skeleton" style={{ width: 60, height: 14, borderRadius: 7 }} />
                <div className="skeleton" style={{ width: 80, height: 14, borderRadius: 7 }} />
              </div>
            ))}
          </div>
        )

      case 'stat':
        return (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            padding: '28px 32px',
            borderRadius: 24,
            background: 'var(--color-surface)',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <div className="skeleton skeleton-circle" style={{ width: 50, height: 50, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div className="skeleton skeleton-line" style={{ width: '60%', marginBottom: 8 }} />
              <div className="skeleton skeleton-line skeleton-line-short" style={{ width: '40%' }} />
            </div>
          </div>
        )

      default:
        return null
    }
  })()

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className={className}
    >
      {content}
    </motion.div>
  )
}

export default Skeleton
