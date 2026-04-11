import { clsx } from 'clsx'
import type { ReactNode } from 'react'

export type CardPadding = 'sm' | 'md' | 'lg'

export interface CardProps {
  header?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  padding?: CardPadding
  className?: string
}

/**
 * 通用卡片组件，支持 header/content/footer 插槽。
 * @example
 * <Card header="标题" footer={<Button>确定</Button>}>内容</Card>
 */
export function Card({ header, children, footer, padding = 'md', className }: CardProps) {
  return (
    <section className={clsx('ui-card', `ui-card--${padding}`, className)}>
      {header ? <header className="ui-card__header">{header}</header> : null}
      <div className="ui-card__content">{children}</div>
      {footer ? <footer className="ui-card__footer">{footer}</footer> : null}
    </section>
  )
}
