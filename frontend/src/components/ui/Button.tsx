import { clsx } from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  children: ReactNode
}

/**
 * 通用按钮组件。
 * @example
 * <Button variant="primary" size="md" onClick={handleClick}>提交</Button>
 */
export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  children,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={clsx('ui-button', `ui-button--${variant}`, `ui-button--${size}`, className)}
    >
      {loading ? '加载中...' : children}
    </button>
  )
}
