/**
 * 布局组件
 * 包含Navbar、Footer、莫比乌斯环粒子背景和主内容区域
 */
import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import { MobiusBackground } from '../MobiusBackground'

function Layout() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 莫比乌斯环粒子背景 */}
      <MobiusBackground />
      
      {/* 导航栏 */}
      <Navbar />
      
      {/* 主内容区域 */}
      <main style={{ flex: 1, position: 'relative', zIndex: 1 }}>
        <Outlet />
      </main>
      
      {/* 页脚 */}
      <Footer />
    </div>
  )
}

export default Layout
