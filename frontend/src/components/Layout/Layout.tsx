/**
 * 布局组件
 * 包含Navbar、Footer、莫比乌斯环粒子背景和主内容区域
 * 集成 PageTransition 实现路由切换的平滑过渡
 */
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import { MobiusBackground } from '../MobiusBackground'
import { PageTransition } from '../motion'

function Layout() {
  const location = useLocation()

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <MobiusBackground />
      <Navbar />

      <main style={{ flex: 1, position: 'relative', zIndex: 1 }}>
        <PageTransition pageKey={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>

      <Footer />
    </div>
  )
}

export default Layout
