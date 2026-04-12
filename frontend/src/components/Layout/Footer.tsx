/**
 * 页脚组件
 * 极简设计 + Space Grotesk 字体 + 微妙的分隔层次
 */
import { motion } from 'framer-motion'

function Footer() {
  return (
    <footer style={{
      backgroundColor: 'var(--color-surface)',
      borderTop: '1px solid var(--color-border-light)',
      marginTop: 'auto',
      position: 'relative',
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '28px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: '10px' }}
          whileHover={{ scale: 1.02 }}
          transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        >
          <span
            style={{
              fontSize: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0071E3, #0055B3)',
              color: 'white',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M3 13L8 8L13 13L21 5M21 11V19H3V5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
          <span style={{
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--color-text)',
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: '-0.01em',
          }}>
            QuantAlpha v2.0
          </span>
        </motion.div>

        <div style={{
          fontSize: '12px',
          color: 'var(--color-text-muted)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          fontFamily: "'Space Grotesk', sans-serif",
        }}>
          <span>基于排序学习的A股量化策略</span>
          <motion.span
            whileHover={{ scale: 1.05, color: '#0071E3' }}
            transition={{ type: 'spring', stiffness: 500, damping: 20 }}
            style={{
              padding: '2px 10px',
              borderRadius: '980px',
              background: 'var(--color-bg-subtle)',
              cursor: 'default',
              transition: 'color 0.2s ease',
            }}
          >
            © 2024
          </motion.span>
        </div>
      </div>
    </footer>
  )
}

export default Footer
