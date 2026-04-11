/**
 * 全局状态管理 Store
 * 使用 Zustand 管理应用状态
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { BacktestResult, ShadowAccount, AIAdvice } from '../types'

type ModelType = 'lightgbm' | 'xgboost'
type ThemeMode = 'light' | 'dark' | 'system'

interface AppState {
  /** 当前选择的模型 */
  selectedModel: ModelType
  /** 影子账户名 */
  accountName: string
  /** 回测数据缓存 */
  backtestData: {
    lightgbm: BacktestResult | null
    xgboost: BacktestResult | null
  }
  /** 影子账户数据 */
  accountData: ShadowAccount | null
  /** AI建议历史 */
  adviceHistory: AIAdvice[]
  /** 侧边栏折叠状态 */
  sidebarCollapsed: boolean
  /** 全局加载状态 */
  globalLoading: boolean
  /** 主题模式 */
  theme: ThemeMode
  /** 移动端菜单展开状态 */
  mobileMenuOpen: boolean
}

interface AppActions {
  /** 设置当前模型 */
  setSelectedModel: (model: ModelType) => void
  /** 设置账户名 */
  setAccountName: (name: string) => void
  /** 设置回测数据 */
  setBacktestData: (model: ModelType, data: BacktestResult) => void
  /** 清除回测数据 */
  clearBacktestData: () => void
  /** 设置影子账户数据 */
  setAccountData: (data: ShadowAccount | null) => void
  /** 添加AI建议到历史 */
  addAdviceToHistory: (advice: AIAdvice) => void
  /** 清除AI建议历史 */
  clearAdviceHistory: () => void
  /** 切换侧边栏折叠 */
  toggleSidebar: () => void
  /** 设置全局加载状态 */
  setGlobalLoading: (loading: boolean) => void
  /** 设置主题模式 */
  setTheme: (theme: ThemeMode) => void
  /** 切换移动端菜单 */
  setMobileMenuOpen: (open: boolean) => void
  /** 重置所有状态 */
  reset: () => void
}

const initialState: AppState = {
  selectedModel: 'lightgbm',
  accountName: '',
  backtestData: {
    lightgbm: null,
    xgboost: null,
  },
  accountData: null,
  adviceHistory: [],
  sidebarCollapsed: false,
  globalLoading: false,
  theme: 'system',
  mobileMenuOpen: false,
}

export const useAppStore = create<AppState & AppActions>()(
  persist(
    (set) => ({
      ...initialState,

      setSelectedModel: (model) =>
        set({ selectedModel: model }),

      setAccountName: (name) =>
        set({ accountName: name }),

      setBacktestData: (model, data) =>
        set((state) => ({
          backtestData: {
            ...state.backtestData,
            [model]: data,
          },
        })),

      clearBacktestData: () =>
        set({
          backtestData: {
            lightgbm: null,
            xgboost: null,
          },
        }),

      setAccountData: (data) =>
        set({ accountData: data }),

      addAdviceToHistory: (advice) =>
        set((state) => ({
          adviceHistory: [advice, ...state.adviceHistory].slice(0, 50),
        })),

      clearAdviceHistory: () =>
        set({ adviceHistory: [] }),

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setGlobalLoading: (loading) =>
        set({ globalLoading: loading }),

      setTheme: (theme) =>
        set({ theme }),

      setMobileMenuOpen: (open) =>
        set({ mobileMenuOpen: open }),

      reset: () => set(initialState),
    }),
    {
      name: 'quant-stock-storage',
      partialize: (state) => ({
        selectedModel: state.selectedModel,
        accountName: state.accountName,
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
)

export type { AppState, AppActions, ModelType, ThemeMode }
