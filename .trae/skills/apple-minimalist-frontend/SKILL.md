---
name: "apple-minimalist-frontend"
description: "生成极简高级苹果风单页前端，严格遵循色彩/字体/动画规范，打造灵动有趣的视觉体验。当用户要求生成苹果风前端、极简页面、高级感UI时触发。"
---

# 苹果极简高级风前端生成器

## 技能概述

本技能用于生成极简高级、有层次感、灵动有趣的苹果风单页前端，严格遵循色彩、字体、动画规范，打造"极简但灵动、高级且有记忆点"的视觉体验。

## 触发条件

当用户使用以下关键词时自动触发：
- 生成苹果风前端
- 极简前端页面
- 高级感 UI 页面
- 苹果风格设计
- 枹简主义界面

## 首要约束（强制优先执行，禁止违规）

### ⚠️ 禁止过度极简到空洞
- 在保持纯白/极浅灰底色的基础上，增加有层次的细节质感
- 打造「极简但灵动、高级且有记忆点」的苹果风
- **禁止**"空白到无聊"的设计

### ⚠️ 点缀色严格规范
- 仅使用低饱和苹果蓝 `#0071E3`（透明度 0.8）
- 或柔和香槟金 `#F5E6D3`（透明度 0.7）
- 仅用于按钮、链接、图标高光
- **禁止**大面积使用高饱和纯蓝

### ⚠️ 动画必须可感知但不突兀
- 所有动画严格遵循「幽灵级但有灵性」
- 既要肉眼可见流畅感，又不喧宾夺主
- **禁止**动画平淡到不可见

## 核心视觉规范（强制优先执行，禁止擅自修改）

### 1. 色彩系统升级

**背景色：**
- 主背景：`#FFFFFF`（纯白）
- 模块背景：`#F5F5F7`（极浅灰）做区分，增加视觉层次

**文字色：**
- 主文字：`#1D1D1F`（深灰黑）
- 辅助文字：`#86868B`（中灰）
- 强调色：`#0071E3`（opacity: 0.8）

**点缀色（严格限制用途）：**
- 低饱和苹果蓝：`rgba(0, 113, 227, 0.8)` - 仅用于按钮、链接、图标高光
- 柔和香槟金：`rgba(245, 230, 211, 0.7)` - 仅用于特殊强调

**渐变规范：**
- 仅使用极淡线性/径向渐变（透明度≥90%）
- 用于卡片阴影、按钮背景
- **禁止**高饱和渐变

### 2. 字体与排版优化

**大标题：**
- 字体：SF Pro Display / Inter
- 字号：64px
- 字重：600（Semibold）
- 字间距：`-0.02em`
- 行高：1.1
- 突出重点

**副标题：**
- 字号：21px
- 字重：400（Regular）
- 行高：1.5
- 颜色：`#86868B`
- 与主标题形成明确层级

**卡片标题：**
- 字号：20px
- 字重：600（Semibold）
- 颜色：`#1D1D1F`

**卡片正文：**
- 字号：16px
- 字重：400（Regular）
- 行高：1.6
- 颜色：`#86868B`

**导航链接：**
- 字号：14px
- 字重：500（Medium）
- 颜色：`#1D1D1F`

**禁止：**
- 所有元素字号同质化
- 必须有「标题-副标题-正文」的清晰层级

### 3. 卡片与视觉元素优化

**卡片样式：**
- 背景：纯白 `#FFFFFF`
- 圆角：24px
- 阴影：
  ```css
  box-shadow: 
    0 15px 40px rgba(0, 0, 0, 0.06),
    0 5px 12px rgba(0, 0, 0, 0.04);
  ```
  既有立体感又不突兀

**卡片内边距：**
- ≥48px
- 图标与文字间距：≥24px
- 增加呼吸感

**Hero 区视觉元素：**
- 使用 3 层嵌套渐变圆环
- 外层：`#F5F5F7` 透明度 0.8，阴影 `0 10px 30px rgba(0, 0, 0, 0.03)`
- 中层：`#E8E8ED` 透明度 0.6，阴影 `0 5px 15px rgba(0, 0, 0, 0.02)`
- 内层：`#0071E3` 透明度 0.2，阴影 `0 2px 8px rgba(0, 113, 227, 0.1)`
- 添加呼吸动画：每 3s 轻微缩放 1.02 倍，平滑过渡

**卡片图标：**
- 使用线性极简图标
- 智能分析/数据安全用 `#0071E3`
- 实时监控/自动化流程用 `#F5E6D3`
- 图标背景用对应颜色极淡渐变（透明度 0.1）
- 添加 `0 4px 12px rgba(0, 113, 227, 0.1)` 悬浮阴影
- **禁止**模糊占位

**卡片差异化：**
- 每个卡片阴影轻微区分
- 突出重点

### 4. 留白层次优化

**模块间留白：**
- 首屏与内容网格间距：≥160px
- 内容网格与页脚间距：≥120px
- 避免过度空旷

**元素内边距：**
- 卡片内边距：≥48px
- 图标与文字间距：≥24px
- 导航栏左右：≥32px

## 页面结构布局（Z字型排版 + 巨型卡片）

生成的单页应用必须固定包含以下区块：

### 1. 导航栏 Navbar

**样式规范：**
- 毛玻璃效果：`backdrop-filter: blur(20px)`
- 背景：`rgba(255, 255, 255, 0.8)`
- 滚动时背景变为：`rgba(255, 255, 255, 0.95)`
- 滚动时毛玻璃效果：`backdrop-filter: blur(30px)`
- 高度：64px

**布局：**
- Logo：左侧（字号 20px，字重 600）
- 导航链接：居中（字号 14px，字重 500）
- 图标：右侧（线性极简搜索/用户图标）

**交互：**
- 导航链接 hover：颜色变为 `#0071E3`，同时 `translateY(-2px)`
- 无下划线
- 过渡：0.3s

### 2. 首屏 Hero 区域

**主标题：**
- 内容：极简 Slogan
- 尺寸：64px
- 字重：600
- 对齐：居中
- 动画：Blur Fade In 入场

**副标题：**
- 尺寸：21px
- 颜色：`#86868B`
- 延迟 0.3s 入场

**视觉元素：**
- 类型：3 层嵌套渐变圆环
- 外层：`#F5F5F7` 透明度 0.8，阴影 `0 10px 30px rgba(0, 0, 0, 0.03)`
- 中层：`#E8E8ED` 透明度 0.6，阴影 `0 5px 15px rgba(0, 0, 0, 0.02)`
- 内层：`#0071E3` 透明度 0.2，阴影 `0 2px 8px rgba(0, 113, 227, 0.1)`
- 呼吸动画：每 3s 轻微缩放 1.02 倍
- 禁止：复杂图案、生硬纯色圆

### 3. 内容网格 Product Grid

**布局：**
- 列数：两列
- 间距：32px（避免拥挤）

**卡片设计差异化：**
- 智能分析/数据安全用苹果蓝 `#0071E3`
- 实时监控/自动化流程用香槟金 `#F5E6D3`
- 每个卡片的图标颜色、阴影轻微区分
- 避免同质化

**卡片样式：**
- 背景：纯白 `#FFFFFF`
- 圆角：24px
- 阴影：
  ```css
  box-shadow: 
    0 15px 40px rgba(0, 0, 0, 0.06),
    0 5px 12px rgba(0, 0, 0, 0.04);
  ```

### 4. 按钮设计（立即开始）

**基础样式：**
- 液态玻璃效果：`backdrop-filter: blur(12px)`
- 背景：`rgba(255, 255, 255, 0.8)`
- 边框：`1px solid #E0E0E0`
- 圆角：12px
- 内边距：`16px 32px`
- 字号：16px
- 字重：500

**Hover 变化：**
- 边框变为：`rgba(0, 113, 227, 0.5)`
- 外扩 0.5px 极淡辉光：`0 0 15px rgba(0, 113, 227, 0.2)`
- 同时 `scale(1.03)`
- 阴影加深：`0 8px 20px rgba(0, 113, 227, 0.1)`
- 过渡：0.4s `cubic-bezier(0.25, 0.1, 0.25, 1)`

## 核心动画强制实现（禁止缺失）

### 1. 文字 Blur Fade In 入场

**实现要求：**
- 页面加载时触发
- 大标题：从 `filter: blur(10px) opacity(0)` 到 `filter: blur(0) opacity(1)`
- 时长：1.2s
- 曲线：`cubic-bezier(0.25, 0.1, 0.25, 1)`
- 副标题延迟 0.3s 入场
- 副标题：从 `filter: blur(5px) opacity(0)` 到 `filter: blur(0) opacity(1)`
- 副标题时长：0.8s

**代码示例：**
```css
@keyframes blurFadeIn {
  from {
    filter: blur(10px);
    opacity: 0;
  }
  to {
    filter: blur(0);
    opacity: 1;
  }
}

@keyframes blurFadeInLight {
  from {
    filter: blur(5px);
    opacity: 0;
  }
  to {
    filter: blur(0);
    opacity: 1;
  }
}

.hero-title {
  animation: blurFadeIn 1.2s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.hero-subtitle {
  animation: blurFadeInLight 0.8s cubic-bezier(0.25, 0.1, 0.25, 1) 0.3s backwards;
}
```

### 2. 卡片 Spotlight 聚光灯效果

**实现要求：**
- 触发：鼠标在卡片上移动
- 效果：卡片跟随极柔和径向渐变光斑
- 光斑样式：
  ```css
  radial-gradient(
    circle at var(--x) var(--y),
    rgba(0, 113, 227, 0.05) 0%,
    transparent 60%
  )
  ```
- 鼠标离开后 0.4s 平滑消失

**代码示例：**
```javascript
card.addEventListener('mousemove', (e) => {
  const rect = card.getBoundingClientRect();
  const x = ((e.clientX - rect.left) / rect.width) * 100;
  const y = ((e.clientY - rect.top) / rect.height) * 100;
  card.style.setProperty('--x', `${x}%`);
  card.style.setProperty('--y', `${y}%`);
});
```

### 3. 液态玻璃按钮

**基础样式：**
- 液态玻璃效果：`backdrop-filter: blur(12px)`
- 背景：`rgba(255, 255, 255, 0.8)`
- 边框：`1px solid #E0E0E0`

**Hover 变化：**
- 边框变为：`rgba(0, 113, 227, 0.5)`
- 外扩 0.5px 极淡辉光：`0 0 15px rgba(0, 113, 227, 0.2)`
- 同时 `scale(1.03)`
- 阴影加深：`0 8px 20px rgba(0, 113, 227, 0.1)`
- 过渡：0.4s

**代码示例：**
```css
.cta-button {
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #E0E0E0;
  transition: all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.cta-button:hover {
  border-color: rgba(0, 113, 227, 0.5);
  box-shadow: 
    0 0 15px rgba(0, 113, 227, 0.2),
    0 8px 20px rgba(0, 113, 227, 0.1);
  transform: scale(1.03);
}
```

### 4. 背景氛围粒子（必须可见，核心惊艳点）

#### Three.js 3D 莫比乌斯环粒子河

**技术实现：**
- 使用 Three.js 实现真正的 3D 效果
- 粒子数量：500 个
- 使用莫比乌斯环参数方程生成 3D 路径

**莫比乌斯环参数方程：**
```javascript
// u: 0-2π，沿环的角度
// v: -1到1，环的宽度方向
// R: 环的半径（18）
// w: 环的宽度（6）
const x = (R + v * w * Math.cos(u / 2)) * Math.cos(u);
const y = (R + v * w * Math.cos(u / 2)) * Math.sin(u);
const z = v * w * Math.sin(u / 2);
```

**粒子样式：**
- 形状：小球体（SphereGeometry）
- 大小：0.15-0.3（非常小）
- 颜色：70% 低饱和苹果蓝 `#0071E3`，30% 柔和香槟金 `#F5E6D3`
- 透明度：0.2-0.45
- 添加 12 条河流线条连接粒子，形成连续的河流效果

**运动规则：**
- 粒子沿莫比乌斯环表面流动（沿 u 方向移动）
- 流动速度：0.3-0.5（随机）
- 添加波浪效果（振幅 0.5，周期 2s）
- 整个环缓慢 3D 旋转（y 轴自转 + x 轴摆动 + 15°倾斜）
- 全局呼吸效果（4s 周期，缩放 1.02 倍）

**鼠标交互：**
- 影响范围：8 个 3D 单位（约 200px）
- 避让效果：粒子向远离鼠标方向偏移（最大 2px）
- 高亮效果：透明度提升至 0.7
- 平滑过渡：0.1 系数

**代码示例：**
```javascript
class MobiusParticleRiver {
  constructor() {
    this.container = document.getElementById('mobius-canvas');
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.particles = [];
    this.mouse = { x: 0, y: 0, normalizedX: 0, normalizedY: 0 };
    this.clock = new THREE.Clock();
    this.mobiusGroup = new THREE.Group();
    
    this.init();
    this.createMobiusRiver();
    this.setupEventListeners();
    this.animate();
  }

  init() {
    // 场景
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xFFFFFF);

    // 相机 - 3D透视
    const aspect = window.innerWidth / window.innerHeight;
    this.camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 2000);
    this.camera.position.set(0, 15, 40);
    this.camera.lookAt(0, 0, 0);

    // 渲染器
    this.renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true
    });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.appendChild(this.renderer.domElement);

    // 添加莫比乌斯环组到场景
    this.scene.add(this.mobiusGroup);
  }

  // 真正的莫比乌斯环参数方程
  getMobiusPoint(u, v, R, w) {
    const cosU = Math.cos(u);
    const sinU = Math.sin(u);
    const cosU2 = Math.cos(u / 2);
    const sinU2 = Math.sin(u / 2);
    
    const x = (R + v * w * cosU2) * cosU;
    const y = (R + v * w * cosU2) * sinU;
    const z = v * w * sinU2;
    
    return new THREE.Vector3(x, y, z);
  }

  // 创建莫比乌斯河流
  createMobiusRiver() {
    const R = 18; // 环的半径
    const w = 6;  // 环的宽度
    
    // 创建粒子系统 - 500个粒子
    const particleCount = 500;
    
    for (let i = 0; i < particleCount; i++) {
      // 在莫比乌斯环表面均匀分布
      const u = (i / particleCount) * Math.PI * 2;
      const v = (Math.random() * 2 - 1); // -1到1
      
      const particle = {
        u: u,
        v: v,
        speed: 0.3 + Math.random() * 0.2,
        size: 0.15 + Math.random() * 0.15,
        opacity: 0.2 + Math.random() * 0.25,
        isBlue: Math.random() < 0.7,
        phase: Math.random() * Math.PI * 2,
        R: R,
        w: w,
        mesh: null
      };

      // 创建粒子
      const geometry = new THREE.SphereGeometry(particle.size, 8, 8);
      
      const color = particle.isBlue ? 0x0071E3 : 0xF5E6D3;
      const material = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: particle.opacity
      });

      particle.mesh = new THREE.Mesh(geometry, material);
      
      // 设置初始位置
      const pos = this.getMobiusPoint(particle.u, particle.v, R, w);
      particle.mesh.position.copy(pos);
      
      this.mobiusGroup.add(particle.mesh);
      this.particles.push(particle);
    }

    // 添加河流线条 - 12条主线
    this.createRiverLines(R, w);
  }

  // 创建河流线条
  createRiverLines(R, w) {
    const lineCount = 12;
    
    for (let i = 0; i < lineCount; i++) {
      const v = (i / (lineCount - 1)) * 2 - 1;
      const points = [];
      const segments = 150;
      
      for (let j = 0; j <= segments; j++) {
        const u = (j / segments) * Math.PI * 2;
        const point = this.getMobiusPoint(u, v, R, w);
        points.push(point);
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      
      const isBlue = i % 2 === 0;
      const color = isBlue ? 0x0071E3 : 0xF5E6D3;
      
      const material = new THREE.LineBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.12
      });
      
      const line = new THREE.Line(geometry, material);
      this.mobiusGroup.add(line);
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    const deltaTime = this.clock.getDelta();
    const elapsedTime = this.clock.getElapsedTime();

    // 整个莫比乌斯环的3D旋转
    this.mobiusGroup.rotation.x = Math.sin(elapsedTime * 0.1) * 0.1;
    this.mobiusGroup.rotation.y += 0.002;
    this.mobiusGroup.rotation.z = Math.PI / 6; // 15度倾斜

    // 呼吸效果
    const breathScale = 1 + Math.sin(elapsedTime * 0.5) * 0.02;
    this.mobiusGroup.scale.set(breathScale, breathScale, breathScale);

    // 鼠标位置转换为3D
    const mouseVector = new THREE.Vector3(
      this.mouse.normalizedX * 25,
      this.mouse.normalizedY * 15,
      10
    );

    // 更新粒子
    this.particles.forEach((particle) => {
      // 沿u方向流动
      particle.u += particle.speed * deltaTime * 0.1;
      if (particle.u > Math.PI * 2) particle.u -= Math.PI * 2;

      // 获取新位置
      let position = this.getMobiusPoint(particle.u, particle.v, particle.R, particle.w);

      // 添加波浪效果
      const wave = Math.sin(elapsedTime * 2 + particle.phase) * 0.5;
      position.y += wave;

      // 鼠标交互
      const worldPosition = position.clone();
      worldPosition.applyMatrix4(this.mobiusGroup.matrixWorld);
      
      const distanceToMouse = worldPosition.distanceTo(mouseVector);
      const interactionRadius = 8;

      let targetOpacity = particle.opacity;

      if (distanceToMouse < interactionRadius) {
        const force = (interactionRadius - distanceToMouse) / interactionRadius;
        
        // 避让效果
        const avoidDir = position.clone().normalize();
        position.add(avoidDir.multiplyScalar(force * 2));

        // 高亮
        targetOpacity = 0.7;
      }

      // 平滑过渡
      particle.mesh.material.opacity += (targetOpacity - particle.mesh.material.opacity) * 0.1;
      particle.mesh.position.copy(position);
    });

    // 渲染
    this.renderer.render(this.scene, this.camera);
  }
}

// 初始化
window.addEventListener('load', () => {
  if (typeof THREE !== 'undefined') {
    new MobiusParticleRiver();
  }
});
```

### 5. 滚动视差 / Fade-in Up

**实现要求：**
- 页面滚动时触发
- 所有模块从 `translateY(30px) opacity(0)` 到 `translateY(0) opacity(1)`
- 时长：0.8s
- 曲线：`cubic-bezier(0.25, 0.1, 0.25, 1)`
- 不同模块延迟入场，打造滚动生命力

**代码示例：**
```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.25, 0.1, 0.25, 1);
}
```

### 6. Hero 区呼吸动画

**实现要求：**
- 3 层嵌套圆环
- 每 3s 轻微缩放 1.02 倍
- 平滑过渡

**代码示例：**
```css
@keyframes breathe {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.02);
  }
}

.circle {
  animation: breathe 3s ease-in-out infinite;
}
```

## 交互细节优化

### 统一过渡规范

**过渡曲线：**
```css
transition-timing-function: cubic-bezier(0.25, 0.1, 0.25, 1);
transition-duration: 0.4s;
```

### 按钮/卡片 Hover

**效果：**
```css
transform: scale(1.02);
box-shadow: 
  0 15px 40px rgba(0, 0, 0, 0.08);
```

### 导航栏滚动交互

**效果：**
- 滚动时毛玻璃效果增强：`backdrop-filter: blur(30px)`
- 背景透明度从 0.8 变为 0.95
- 增加交互反馈

## 阴影分层规范

**卡片阴影（最深）：**
```css
box-shadow: 
  0 15px 40px rgba(0, 0, 0, 0.06),
  0 5px 12px rgba(0, 0, 0, 0.04);
```

**图标阴影（中等）：**
```css
box-shadow: 0 4px 12px rgba(0, 113, 227, 0.1);
```

**按钮阴影（最浅）：**
```css
box-shadow: 0 4px 12px rgba(0, 113, 227, 0.08);
```

## 响应式适配

### 桌面端（≥1024px）
- 两列布局
- 大标题：64px
- 模块内边距：64px

### 平板端（768px - 1023px）
- 两列布局
- 大标题：48px
- 模块内边距：48px

### 移动端（<768px）
- 单列布局
- 大标题：36px
- 导航栏改为汉堡菜单
- 模块内边距：32px
- 所有元素自适应留白，保证呼吸感

## 全局约束原则（禁止违规）

### 必须遵守

1. 整体保持纯白/极浅灰底色，但有层次感
2. 使用极简无衬线字体，有清晰层级
3. 所有动画必须可感知但不突兀
4. 点缀色严格限制用途和透明度
5. 留白有层次，避免过度空旷
6. 粒子效果必须有灵性，禁止随机噪点

### 严禁使用

1. ❌ 高饱和渐变
2. ❌ 硬边描边
3. ❌ 大面积光污染
4. ❌ 复杂背景图
5. ❌ 过度装饰元素
6. ❌ 过度极简到空洞无聊
7. ❌ 动画平淡到不可见
8. ❌ 元素同质化严重
9. ❌ 随机闪烁的粒子效果
10. ❌ 硬边小点粒子

## 输出要求

### 代码规范

1. **技术栈适配：**
   - 根据项目栈选择：HTML/CSS/JS 或 React/Vue
   - 确保可直接运行

2. **参数严格执行：**
   - 所有色值、尺寸、动画参数严格照搬
   - 禁止自定义调整

3. **代码质量：**
   - 代码精简无冗余
   - 注释清晰（使用简体中文）
   - 响应式适配所有屏幕

4. **设计原则：**
   - 全程保持极简高级感
   - 有记忆点和灵动性
   - 避免空洞无聊
   - 粒子效果必须有灵性

## 执行流程

1. **分析需求**：确认页面类型和核心功能
2. **选择技术栈**：根据项目环境选择合适的框架
3. **构建结构**：按照Z字型布局创建页面骨架
4. **应用样式**：严格执行色彩、字体、留白规范
5. **添加动画**：实现所有核心动画效果（粒子、Blur Fade In、聚光灯等）
6. **优化交互**：添加聚光灯、粒子等交互效果
7. **响应式适配**：确保所有屏幕下的视觉效果
8. **验证输出**：检查是否符合所有约束条件

## 注意事项

- ⚠️ 所有参数必须严格遵循，不得擅自修改
- ⚠️ 动画必须可感知，禁止平淡到不可见
- ⚠️ 点缀色严格限制用途和透明度
- ⚠️ 留白有层次，避免过度空旷
- ⚠️ 保持苹果设计的克制与优雅，但要有灵性
- ⚠️ 确保代码可直接运行，无依赖缺失
- ⚠️ 禁止过度极简到空洞无聊
- ⚠️ 禁止元素同质化严重
- ⚠️ 粒子效果必须有灵性，禁止随机噪点和硬边小点
- ⚠️ 粒子必须使用柔和圆形模糊光斑