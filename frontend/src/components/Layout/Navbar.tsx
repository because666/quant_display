/**
 * 导航栏组件
 * 苹果极简风格，毛玻璃效果，支持路由高亮、移动端响应式菜单
 */
import { useEffect, useCallback, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAppStore } from '../../store/useAppStore'
import type { ThemeMode } from '../../store/useAppStore'

type NavItem = {
  path: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { path: '/strategy', label: '策略概览', icon: '📊' },
  { path: '/stockpool', label: '选股池', icon: '🎯' },
  { path: '/backtest', label: '回测仪表盘', icon: '📈' },
  { path: '/model', label: '模型分析', icon: '🤖' },
  { path: '/factors', label: '因子探索', icon: '🔍' },
  { path: '/ai', label: 'AI推荐', icon: '💡' },
  { path: '/account', label: '影子账户', icon: '💼' },
]

function Navbar() {
  const { theme, setTheme, mobileMenuOpen, setMobileMenuOpen } = useAppStore()
  const [scrolled, setScrolled] = useState(false)

  // 监听滚动，添加scrolled状态
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    const isDark =
      theme === 'dark' ||
      (theme === 'system' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches)

    if (isDark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const root = document.documentElement
      if (mediaQuery.matches) {
        root.classList.add('dark')
      } else {
        root.classList.remove('dark')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  const cycleTheme = useCallback(() => {
    const order: ThemeMode[] = ['light', 'dark', 'system']
    const currentIndex = order.indexOf(theme)
    const nextIndex = (currentIndex + 1) % order.length
    setTheme(order[nextIndex])
  }, [theme, setTheme])

  return (
    <nav 
      className="navbar" 
      style={{
        background: scrolled 
          ? 'rgba(255, 255, 255, 0.95)' 
          : 'rgba(255, 255, 255, 0.8)',
        backdropFilter: scrolled ? 'blur(30px)' : 'blur(20px)',
        WebkitBackdropFilter: scrolled ? 'blur(30px)' : 'blur(20px)',
        borderBottom: scrolled 
          ? '1px solid rgba(0, 0, 0, 0.1)' 
          : '1px solid rgba(0, 0, 0, 0.05)',
        transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
        height: '64px',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
      }}
    >
      <div className="navbar-inner" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 32px', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <NavLink to="/strategy" className="navbar-brand" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
          <div className="brand-icon" style={{ 
            width: '32px', 
            height: '32px', 
            borderRadius: '8px', 
            background: '#0071E3', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            color: 'white'
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M3 13L8 8L13 13L21 5M21 11V19H3V5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="brand-text" style={{ fontSize: '20px', fontWeight: 600, color: '#1D1D1F', letterSpacing: '-0.02em' }}>QuantAlpha</span>
        </NavLink>

        <div className="navbar-links" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                borderRadius: '980px',
                fontSize: '14px',
                fontWeight: isActive ? 500 : 400,
                color: isActive ? '#0071E3' : '#1D1D1F',
                background: isActive ? 'rgba(0, 113, 227, 0.08)' : 'transparent',
                textDecoration: 'none',
                transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
              })}
            >
              <span className="nav-link-icon">{item.icon}</span>
              <span className="nav-link-label">{item.label}</span>
            </NavLink>
          ))}
        </div>

        <div className="navbar-actions" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={cycleTheme} 
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              border: 'none',
              background: 'transparent',
              color: '#1D1D1F',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
            }}
            title={`主题: ${getThemeLabel(theme)}`}
          >
            {getThemeIcon(theme)}
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{
              display: 'none',
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              border: 'none',
              background: 'transparent',
              color: '#1D1D1F',
              cursor: 'pointer',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileMenuOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6"/>
                  <line x1="3" y1="12" x2="21" y2="12"/>
                  <line x1="3" y1="18" x2="21" y2="18"/>
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="mobile-menu" style={{ 
          position: 'absolute', 
          top: '64px', 
          left: 0, 
          right: 0, 
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          borderTop: '1px solid rgba(0, 0, 0, 0.1)',
          padding: '16px',
          animation: 'slideUp 0.3s ease-out'
        }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) => `mobile-nav-item ${isActive ? 'mobile-nav-item-active' : ''}`}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '14px 20px',
                borderRadius: '12px',
                fontSize: '15px',
                fontWeight: isActive ? 500 : 400,
                color: isActive ? '#0071E3' : '#1D1D1F',
                background: isActive ? 'rgba(0, 113, 227, 0.08)' : 'transparent',
                textDecoration: 'none',
                marginBottom: '4px',
              })}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </nav>
  )
}

function getThemeLabel(theme: ThemeMode): string {
  if (theme === 'dark') return '暗色模式'
  if (theme === 'light') return '亮色模式'
  return '跟随系统'
}

function getThemeIcon(theme: ThemeMode) {
  if (theme === 'dark') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
      </svg>
    )
  }
  if (theme === 'light') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
    )
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  )
}

export default Navbar
