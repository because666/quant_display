import type { ReactNode } from 'react'
import { useEffect } from 'react'

export interface ModalProps {
  open: boolean
  title?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  onClose: () => void
  closeOnOverlayClick?: boolean
  closeOnEsc?: boolean
}

/**
 * 通用弹窗组件，支持遮罩关闭与 ESC 关闭。
 * @example
 * <Modal open={open} title="提示" onClose={() => setOpen(false)}>内容</Modal>
 */
export function Modal({
  open,
  title,
  children,
  footer,
  onClose,
  closeOnOverlayClick = true,
  closeOnEsc = true,
}: ModalProps) {
  useEffect(() => {
    if (!open || !closeOnEsc) {
      return
    }
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, closeOnEsc, onClose])

  if (!open) {
    return null
  }

  return (
    <div
      className="ui-modal-overlay"
      onClick={() => {
        if (closeOnOverlayClick) {
          onClose()
        }
      }}
      role="presentation"
    >
      <section className="ui-modal" onClick={(event) => event.stopPropagation()}>
        {title ? (
          <header className="ui-modal__header">
            <h3 className="ui-modal__title">{title}</h3>
          </header>
        ) : null}
        <div className="ui-modal__body">{children}</div>
        {footer ? <footer className="ui-modal__footer">{footer}</footer> : null}
      </section>
    </div>
  )
}
