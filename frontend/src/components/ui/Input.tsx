import { clsx } from 'clsx'
import type { InputHTMLAttributes, ReactNode } from 'react'

export type InputSize = 'sm' | 'md' | 'lg'

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: InputSize
  error?: boolean
  prefixIcon?: ReactNode
  suffixIcon?: ReactNode
}

/**
 * 通用输入框组件，支持尺寸、错误态和前后图标槽位。
 * @example
 * <Input prefix="¥" placeholder="请输入价格" />
 */
export function Input({
  size = 'md',
  error = false,
  prefixIcon,
  suffixIcon,
  className,
  ...rest
}: InputProps) {
  return (
    <label className={clsx('ui-input-wrap', error && 'ui-input-wrap--error')}>
      {prefixIcon ? <span>{prefixIcon}</span> : null}
      <input {...rest} className={clsx('ui-input', `ui-input--${size}`, className)} />
      {suffixIcon ? <span>{suffixIcon}</span> : null}
    </label>
  )
}
