import type { ReactNode } from 'react'

export interface TableColumn<T> {
  key: keyof T
  title: string
  render?: (value: T[keyof T], row: T, rowIndex: number) => ReactNode
}

export interface TableProps<T extends Record<string, unknown>> {
  columns: TableColumn<T>[]
  dataSource: T[]
  loading?: boolean
  rowKey: keyof T
  emptyText?: string
}

/**
 * 通用表格组件，支持列定义、数据源和加载状态。
 * @example
 * <Table rowKey="code" columns={columns} dataSource={rows} />
 */
export function Table<T extends Record<string, unknown>>({
  columns,
  dataSource,
  loading = false,
  rowKey,
  emptyText = '暂无数据',
}: TableProps<T>) {
  if (loading) {
    return <div className="ui-table-empty">加载中...</div>
  }

  if (dataSource.length === 0) {
    return <div className="ui-table-empty">{emptyText}</div>
  }

  return (
    <div className="ui-table-wrap">
      <table className="ui-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={String(column.key)}>{column.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataSource.map((row, rowIndex) => (
            <tr key={String(row[rowKey])}>
              {columns.map((column) => {
                const value = row[column.key]
                return (
                  <td key={String(column.key)}>
                    {column.render ? column.render(value, row, rowIndex) : String(value ?? '')}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
