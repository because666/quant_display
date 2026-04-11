/**
 * 页脚组件
 * 苹果极简风格，纯白背景，极淡分隔线
 */
function Footer() {
  return (
    <footer style={{
      backgroundColor: 'var(--color-surface)',
      borderTop: '1px solid var(--color-border-light)',
      marginTop: 'auto',
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '24px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px' }}>📈</span>
          <span style={{ fontSize: '13px', color: 'var(--color-text-subtle)' }}>
            量化选股系统 v2.0
          </span>
        </div>
        <div style={{
          fontSize: '13px',
          color: 'var(--color-text-muted)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
        }}>
          <span>基于排序学习的A股量化策略</span>
          <span>© 2024</span>
        </div>
      </div>
    </footer>
  )
}

export default Footer
