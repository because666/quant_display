/**
 * 涟漪按钮组件
 * 点击时产生从点击位置扩散的涟漪效果，配合弹簧物理交互
 *
 * @param children - 按钮内容
 * @param onClick - 点击回调
 * @param variant - 按钮变体：primary/outline/secondary/ghost/danger
 * @param size - 按钮尺寸：sm/md/lg
 * @param disabled - 是否禁用
 * @param loading - 是否加载中
 * @param className - 自定义类名
 */
import { useState, useCallback, type ReactNode, type MouseEvent } from 'react'
import { motion } from 'framer-motion'

type RippleButtonVariant = 'primary' | 'outline' | 'secondary' | 'ghost' | 'danger'
type RippleButtonSize = 'sm' | 'md' | 'lg'

interface Ripple {
  id: number
  x: number
  y: number
}

type RippleButtonProps = {
  children: ReactNode
  onClick?: (e: MouseEvent<HTMLButtonElement>) => void
  variant?: RippleButtonVariant
  size?: RippleButtonSize
  disabled?: boolean
  loading?: boolean
  className?: string
}

const sizeMap: Record<RippleButtonSize, { padding: string; fontSize: string }> = {
  sm: { padding: '8px 16px', fontSize: '13px' },
  md: { padding: '12px 24px', fontSize: '14px' },
  lg: { padding: '16px 36px', fontSize: '15px' },
}

function RippleButton({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
}: RippleButtonProps) {
  const [ripples, setRipples] = useState<Ripple[]>([])

  const handleClick = useCallback(
    (e: MouseEvent<HTMLButtonElement>) => {
      if (disabled || loading) return

      const rect = e.currentTarget.getBoundingClientRect()
      const ripple: Ripple = {
        id: Date.now(),
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      }

      setRipples((prev) => [...prev, ripple])
      setTimeout(() => {
        setRipples((prev) => prev.filter((r) => r.id !== ripple.id))
      }, 600)

      onClick?.(e)
    },
    [onClick, disabled, loading]
  )

  const { padding, fontSize } = sizeMap[size]

  return (
    <motion.button
      onClick={handleClick}
      disabled={disabled || loading}
      whileHover={disabled ? {} : { scale: 1.02, y: -1 }}
      whileTap={disabled ? {} : { scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className={`btn btn-${variant} ${size !== 'md' ? `btn-${size}` : ''} ${loading ? 'loading' : ''} ${className}`}
      style={{
        padding,
        fontSize,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <span style={{ position: 'relative', zIndex: 1, display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
        {children}
      </span>

      {ripples.map((ripple) => (
        <span
          key={ripple.id}
          style={{
            position: 'absolute',
            left: ripple.x,
            top: ripple.y,
            width: 20,
            height: 20,
            marginLeft: -10,
            marginTop: -10,
            borderRadius: '50%',
            background: variant === 'primary' || variant === 'danger'
              ? 'rgba(255,255,255,0.35)'
              : 'rgba(0,113,227,0.2)',
            animation: 'ripple 0.6s ease-out forwards',
            pointerEvents: 'none',
          }}
        />
      ))}
    </motion.button>
  )
}

export default RippleButton
