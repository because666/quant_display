---
name: "frontend-design"
description: "创建独特、生产级的前端界面，拒绝AI通用美学。当用户要求前端设计、UI设计、界面设计、网页设计时触发。"
---

# Frontend Design - 前端設計技能

**技能 ID:** frontend-design  
**版本:** v1.0  
**用途:** 創建獨特、生產級的前端介面，拒絕「AI 通用美學」  
**來源:** 基於 Anthropic 官方 Frontend Design Skill 授權

## 🎯 觸發條件

關鍵字列表：
- 前端設計、UI 設計、界面設計
- frontend design、網頁設計、web design
- CSS、HTML、React 組件
- 視覺設計、美學設計、用戶介面
- landing page、dashboard、儀表板、表單設計、卡片設計

## 🧠 核心設計理念：反 AI 通用美學（Anti-AI Slop Aesthetics）

核心原則: 每個設計都應該有明確的美學觀點，而不是通用的「AI 風格」

### 必須避免的「AI 通用美學」特徵

| 反模式 | 問題 | 替代方案 |
|--------|------|----------|
| 過度使用的字體 | Arial, Inter, Roboto | 選擇獨特字體：JetBrains Mono, Playfair Display, Space Grotesk |
| 陳腐的配色 | #4F46E5 (藍紫), 彩虹漸層 | 建立有性格的調色板：單色主導 + 銳利點綴色 |
| 可預測的佈局 | 12 欄格線、卡片牆、英雄區 + 功能區 | 不對稱、意外的空間構圖、大膽的負空間 |
| 通用的動效 | 淡入淡出、基本懸停效果 | 意圖明確的微互動、高影響力時刻的動畫 |
| 缺乏深度 | 純色背景、無紋理 | 大氣背景、微妙漸層、情境細節 |

## 🏗️ 設計思維框架（Design Before Code）

在編寫任何代碼之前，必須建立大膽的美學方向：

### 四個核心問題

1. **PURPOSE（目的）**
   - 這個介面解決什麼問題？
   - 目標用戶是誰？
   - 用戶的情感需求是什麼？

2. **TONE（調性）**
   選擇一個大膽的美學方向：
   - 極簡主義（Minimalist）
   - 極繁主義（Maximalist）
   - 復古未來主義（Retro-Futuristic）
   - 粗獷主義（Brutalist）
   - 有機自然（Organic）
   - 科技感（Tech/Cyberpunk）
   - 手工質感（Handcrafted）

3. **CONSTRAINTS（限制）**
   - 技術限制（瀏覽器支援、效能要求）
   - 品牌規範（如果有）
   - 無障礙要求（WCAG 等級）

4. **DIFFERENTIATION（獨特性）**
   - 什麼讓這個設計令人難忘？
   - 用戶離開後會記得什麼？
   - 有什麼意想不到的元素？

## 🎨 前端美學五大支柱

### 1. 排版（Typography）
核心原則: 字體是設計的聲音，選擇要有意圖

```css
/* ❌ 避免：過度使用的字體 */
font-family: 'Inter', 'Roboto', 'Arial', sans-serif;

/* ✅ 推薦：獨特的字體組合 */
/* 科技感 */
font-family: 'JetBrains Mono', 'Fira Code', monospace;

/* 優雅感 */
font-family: 'Playfair Display', 'Cormorant Garamond', serif;

/* 現代感 */
font-family: 'Space Grotesk', 'DM Sans', sans-serif;

/* 實驗性 */
font-family: 'Archivo Black', 'Bebas Neue', sans-serif;
```

排版層次:
- 使用 2-3 種字體（標題 + 正文 + 可選的 accent）
- 建立明確的字體大小階梯（使用 clamp() 實現響應式）
- 字重對比強烈（400 vs 700+）
- 行高有呼吸感（1.5-1.75 用於正文）

### 2. 色彩與主題（Color & Theme）
核心原則: 凝聚的調色板，主導色 + 銳利點綴色

```css
/* ❌ 避免：AI 通用配色 */
--primary: #4F46E5;  /* 無處不在的紫藍色 */
--gradient: linear-gradient(to right, #667eea, #764ba2);

/* ✅ 推薦：有性格的調色板 */

/* 暗黑科技風 */
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #141414;
  --text-primary: #fafafa;
  --accent: #22d3ee;  /* 青色點綴 */
  --accent-glow: rgba(34, 211, 238, 0.3);
}

/* 溫暖自然風 */
:root {
  --bg-primary: #faf8f5;
  --bg-secondary: #f0ebe3;
  --text-primary: #2d2a26;
  --accent: #e07a5f;  /* 陶土橙 */
  --accent-muted: #f4a261;
}

/* 高對比極簡風 */
:root {
  --bg-primary: #ffffff;
  --text-primary: #000000;
  --accent: #ff3366;  /* 唯一的顏色 */
}
```

### 3. 動效（Motion）
核心原則: 動效用於高影響力時刻，而非裝飾

```css
/* ❌ 避免：無意義的動效 */
transition: all 0.3s ease;  /* 懶惰的全局過渡 */

/* ✅ 推薦：意圖明確的動效 */

/* 微互動：按鈕懸停 */
.btn {
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.btn:hover {
  transform: translateY(-2px) scale(1.02);
}

/* 入場動畫：驚喜時刻 */
@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.card {
  animation: reveal 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: calc(var(--index) * 0.1s);
}

/* 載入狀態：吸引注意力 */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 20px var(--accent-glow); }
  50% { box-shadow: 0 0 40px var(--accent-glow); }
}
```

### 4. 空間構圖（Spatial Composition）
核心原則: 不對稱、意外、大膽使用負空間

```css
/* ❌ 避免：可預測的格線佈局 */
.container {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 24px;
}

/* ✅ 推薦：意外的構圖 */

/* 不對稱英雄區 */
.hero {
  display: grid;
  grid-template-columns: 1fr 0.8fr;  /* 不等分 */
  gap: 80px;  /* 大量留白 */
}

/* 重疊元素 */
.card-stack {
  position: relative;
}
.card-stack > * {
  position: absolute;
  transform: rotate(var(--rotation));
}

/* 對角流動 */
.diagonal-flow {
  clip-path: polygon(0 0, 100% 15%, 100% 100%, 0 85%);
}
```

### 5. 背景與視覺細節（Backgrounds & Visual Details）
核心原則: 大氣與深度，而非純色

```css
/* ❌ 避免：無聊背景 */
background: #ffffff;

/* ✅ 推薦：有意境的背景 */

/* 漸變網格 */
.bg-grid {
  background-image:
    linear-gradient(to right, var(--border-color) 1px, transparent 1px),
    linear-gradient(to bottom, var(--border-color) 1px, transparent 1px);
  background-size: 60px 60px;
}

/* 噪點紋理 */
.noise-bg::after {
  content: '';
  position: inset: 0;
  background-image: url("data:image/svg+xml,...");
  opacity: 0.03;
  pointer-events: none;
}

/* 徑向漸變光暈 */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(64px);
  background: radial-gradient(circle, var(--accent), transparent);
}
```

## 🔧 技術實現指南

### React 組件範例

```tsx
// 有靈魂的按鈕
function SoulfulButton({ children }: { children: React.ReactNode }) {
  const [ripples, setRipples] = useState<Array<{ id: number; x: number; y: number }>>([]);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setRipples(prev => [...prev, {
      id: Date.now(),
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== r.id.id)), 600);
  };

  return (
    <button onClick={handleClick} className="relative overflow-hidden group">
      <span className="relative z-10">{children}</span>
      {ripples.map(r => (
        <span key={r.id} className="absolute rounded-full bg-white/30 animate-ping"
          style={{ left: r.x, top: r.y, width: 20, height: 20, marginLeft: -10, marginTop: -10 }} />
      ))}
    </button>
  );
}

// 卡片入場動畫
function AnimatedCard({ children, index }: { children: React.ReactNode; index: number }) {
  return (
    <div style={{
      animation: `reveal 0.6s cubic-bezier(0.22, 1, 0.36, 1) ${index * 0.1}s both`,
    }}>
      {children}
    </div>
  );
}
```

## ⚠️ 重要約束

- **NEVER 使用通用 AI 美學**: 避免過度使用字體（Inter, Roboto, Arial）、陳腐配色（紫色漸變）、可預測佈局
- **每個設計都應獨特**: 不要在不同項目中收斂到相同選擇（如 Space Grotesk）
- **匹配實現複雜度與美學願景**: 極繁主義需要精緻的留白和排版，極簡主義需要大膽的色彩和動效
- **Claude 能做出非凡的創意工作**: 不要保守，展現跳出框架思考並完全投入獨特願景時能創造出什麼
