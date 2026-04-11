/**
 * 通用UI组件
 * Card, Button, Input, Modal
 */
import { ReactNode } from 'react'

type CardProps = {
  header?: string
  footer?: ReactNode
  children: ReactNode
  className?: string
}

export function Card({ header, footer, children, className = '' }: CardProps) {
  return (
    <div className={`card ${className}`}>
      {header && <div className="card-header">{header}</div>}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  )
}

type ButtonProps = {
  children: ReactNode
  variant?: 'primary' | 'outline'
  onClick?: () => void
  loading?: boolean
  disabled?: boolean
  className?: string
}

export function Button({
  children,
  variant = 'primary',
  onClick,
  loading = false,
  disabled = false,
  className = '',
}: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant} ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? '加载中...' : children}
    </button>
  )
}

type InputProps = {
  type?: string
  placeholder?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  className?: string
}

export function Input({
  type = 'text',
  placeholder,
  value,
  onChange,
  className = '',
}: InputProps) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      className={`input ${className}`}
    />
  )
}

type ModalProps = {
  open: boolean
  title: string
  children: ReactNode
  footer?: ReactNode
  onClose: () => void
}

export function Modal({ open, title, children, footer, onClose }: ModalProps) {
  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">{title}</div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}
