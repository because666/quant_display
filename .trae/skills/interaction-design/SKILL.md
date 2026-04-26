---
name: "interaction-design"
description: "设计和实现微交互、动效设计、过渡动画和用户反馈模式。当用户要求添加交互效果、加载状态、微交互、滚动动画时触发。"
---

# Interaction Design - 前端交互設計技能

**來源:** wshobson/agents (GitHub)

## 🎯 觸發條件

當用戶需要以下功能時觸發：
- 為UI添加微互動增強用戶反饋
- 實現平滑的頁面和組件過渡動畫
- 設計加載狀態和骨架屏（Skeleton）
- 創建手勢交互（滑動、拖拽）
- 構建通知和Toast系統
- 添加滾動觸發的動畫（Scroll Reveal）
- 設計Hover和Focus狀態
- 為首頁/表單/列表優化交互體驗

## 核心原則：有目的的運動（Purposeful Motion）

動效應該傳達信息，而非裝飾：

1. **反饋（Feedback）**: 確認用戶操作已發生
2. **導向（Orientation）**: 展示元素從哪裡來/到哪裡去
3. **聚焦（Focus）**: 將注意力引向重要變化
4. **連續性（Continuity）**: 在過渡期間維持上下文

## ⏱️ 時間指南

| 持續時間 | 使用場景 |
|----------|---------|
| 100-150ms | 微反饋（懸停、點擊） |
| 200-300ms | 小過渡（切換、下拉菜單） |
| 300-500ms | 中等過渡（模態框、頁面切換） |
| 500ms+ | 複雜編排動畫 |

## 🎯 緩動函數（Easing Functions）

```css
/* 通用緩動函數 */
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);    /* 減速 - 元素進入 */
--ease-in: cubic-bezier(0.55, 0, 1, 0.45);     /* 加速 - 元素離開 */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1); /* 雙向 - 移動中 */
--spring: cubic-bezier(0.34, 1.56, 0.64, 1);   /* 彈跳 - 活潑感 */
```

## 🔥 快速上手：按鈕微交互

```tsx
import { motion } from "framer-motion";

export function InteractiveButton({ children, onClick }: {
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 17 }}
      style={{
        padding: '8px 16px',
        background: '#0071E3',
        color: 'white',
        borderRadius: '980px',
        border: 'none',
        cursor: 'pointer',
      }}
    >
      {children}
    </motion.button>
  );
}
```

## 📋 交互模式詳解

### 1. 加載狀態（Loading States）

#### 骨架屏（Skeleton Screens）：保留佈局的同時加載

```tsx
function CardSkeleton() {
  return (
    <div className="animate-pulse" style={{ borderRadius: 24 }}>
      <div style={{ height: 192, background: '#F5F5F7', borderRadius: 24 }} />
      <div style={{ marginTop: 16, height: 14, background: '#F5F5F7', borderRadius: 8, width: '75%' }} />
      <div style={{ marginTop: 8, height: 14, background: '#F5F5F7', borderRadius: 8, width: '50%' }} />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="animate-pulse">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, padding: '14px 20px', borderBottom: '1px solid #E8E8ED' }}>
          <div style={{ width: 80, height: 14, background: '#F5F5F7', borderRadius: 7 }} />
          <div style={{ flex: 1, height: 14, background: '#F5F5F7', borderRadius: 7 }} />
          <div style={{ width: 60, height: 14, background: '#F5F5F7', borderRadius: 7 }} />
          <div style={{ width: 80, height: 14, background: '#F5F5F7', borderRadius: 7 }} />
        </div>
      ))}
    </div>
  );
}
```

#### 進度指示器：顯示確定性進度

```tsx
function ProgressBar({ progress }: { progress: number }) {
  return (
    <div style={{ height: 6, background: '#E8E8ED', borderRadius: 9999, overflow: 'hidden' }}>
      <motion.div
        style={{
          height: '100%',
          background: '#0071E3',
          borderRadius: 9999,
        }}
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ ease: [0.22, 1, 0.36, 1], duration: 0.4 }}
      />
    </div>
  );
}
```

### 2. 狀態過渡（State Transitions）

#### 切換帶平滑過渡：

```tsx
function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        position: 'relative',
        width: 48,
        height: 28,
        borderRadius: 9999,
        background: checked ? '#0071E3' : '#E8E8ED',
        transition: 'background-color 0.25s cubic-bezier(0.22, 1, 0.36, 1)',
        border: 'none',
        cursor: 'pointer',
        padding: 2,
      }}
    >
      <motion.span
        style={{
          position: 'absolute',
          top: 2,
          left: 2,
          width: 24,
          height: 24,
          borderRadius: 9999,
          background: 'white',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        }}
        animate={{ x: checked ? 20 : 0 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      />
    </button>
  );
}
```

### 3. 頁面過渡（Page Transitions）

```tsx
import { AnimatePresence, motion } from "framer-motion";

function PageTransition({ children, pageKey }: {
  children: React.ReactNode;
  pageKey: string;
}) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pageKey}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

### 4. 反饋模式（Feedback Patterns）

#### 點擊漣漪效果（Ripple Effect）：

```tsx
function RippleButton({ children, onClick }: {
  children: React.ReactNode;
  onClick?: (e: React.MouseEvent) => void;
}) {
  const [ripples, setRipples] = useState<Array<{
    id: number; x: number; y: number
  }>>([]);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ripple = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      id: Date.now(),
    };
    setRipples(prev => [...prev, ripple]);
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== ripple.id));
    }, 600);
    onClick?.(e);
  };

  return (
    <button
      onClick={handleClick}
      style={{
        position: 'relative',
        overflow: 'hidden',
        padding: '12px 24px',
        borderRadius: '980px',
        background: '#0071E3',
        color: 'white',
        border: 'none',
        cursor: 'pointer',
      }}
    >
      {children}
      {ripples.map(ripple => (
        <span
          key={ripple.id}
          style={{
            position: 'absolute',
            left: ripple.x,
            top: ripple.y,
            width: 24,
            height: 24,
            marginLeft: -12,
            marginTop: -12,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.3)',
            animation: 'ripple 0.6s ease-out forwards',
          }}
        />
      ))}
    </button>
  );
}
```

### 5. 手勢交互（Gesture Interactions）

#### 滑動關閉（Swipe to Dismiss）：

```tsx
function SwipeCard({ children, onDismiss }: {
  children: React.ReactNode;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={(_, info) => {
        if (Math.abs(info.offset.x) > 120) {
          onDismiss();
        }
      }}
      style={{
        cursor: 'grab',
        touchAction: 'pan-y',
      }}
      whileTap={{ cursor: 'grabbing' }}
    >
      {children}
    </motion.div>
  );
}
```

### 6. 滚动触发动画（Scroll Reveal）

列表或卡片在进入視口時有一個平滑的淡入上浮效果：

```tsx
import { useEffect, useRef } from 'react';
import { useInView } from 'framer-motion';

function ScrollRevealItem({ children, index }: {
  children: React.ReactNode; index: number;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{
        duration: 0.5,
        delay: index * 0.08,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
```

### 7. Tab切换动画

Tab切換時加上淡入淡出的平滑過渡，不要生硬跳轉：

```tsx
function TabContent({ activeTab, tabs }: {
  activeTab: string;
  tabs: Record<string, React.ReactNode>;
}) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      >
        {tabs[activeTab]}
      </motion.div>
    </AnimatePresence>
  );
}
```

## CSS 動畫模式

### 關鍵幀動畫

```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

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

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.animate-fadeInUp {
  animation: fadeInUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.animate-blur-fade-in {
  animation: blurFadeIn 1.2s ease-out both;
}

.animate-shimmer {
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

### CSS 過渡

```css
.card {
  transition:
    transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.card:hover {
  transform: translateY(-4px) scale(1.005);
  box-shadow:
    0 24px 48px rgba(0, 0, 0, 0.03),
    0 8px 16px rgba(0, 0, 0, 0.04);
}
```

## ♿ 無障礙考慮

```css
/* 尊重用戶的減少動效偏好設定 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

```tsx
function AnimatedComponent({ children }: { children: React.ReactNode }) {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: prefersReducedMotion ? 0 : 0.35 }}
    >
      {children}
    </motion.div>
  );
}
```

## ✅ 最佳實踐

1. **性能優先**: 使用 `transform` 和 `opacity` 實現流暢的 60fps 動畫，避免動畫 `width`、`height`、`top`、`left`
2. **支持減少動效**: 始終尊重 `prefers-reduced-motion` 媒體查詢
3. **一致的時間節奏**: 在整個應用中使用統一的時間標尺
4. **自然物理**: 優先使用彈簧動畫（spring）而非線性緩動
5. **可中斷**: 允許用戶取消長時間的動畫
6. **漸進增強**: 在沒有 JS 動畫的情況下也能正常工作
7. **在真機上測試**: 性能在不同設備上有顯著差異

## ❌ 常見問題

| 問題 | 解決方案 |
|------|---------|
| 卡頓動畫 | 避免動畫 width/height/top/left 屬性 |
| 過度動畫 | 太多動效會讓用戶疲勞，適可而止 |
| 阻塞交互 | 不要在動畫期間阻止用戶輸入 |
| 內存洩漏 | 卸載時清理動畫監聽器 |
| 內容閃爍 | 謹慎使用 will-change 進行優化 |
