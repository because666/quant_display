/**
 * 回测与模型分析API服务
 * 对接后端回测结果查询、模型分析数据接口
 */
import { api } from './api'
import type { FeatureImportance } from '../types'

/** 回测指标 */
export interface BacktestMetricsData {
  annualized_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  cumulative_return?: number
  win_rate?: number
  turnover_rate?: number
  drawdown_peak_date?: string
  drawdown_trough_date?: string
}

/** 回测结果项 */
export interface BacktestResultItem {
  id: number
  model_type: string
  created_at: string | null
  metrics: BacktestMetricsData
}

/** 净值数据点 */
export interface NavPoint {
  date: string
  nav: number
  benchmark_nav?: number
}

/** 最新回测数据 */
export interface LatestBacktestData {
  id: number
  metrics: BacktestMetricsData
  nav_points: NavPoint[]
  created_at: string | null
}

/** 模型分析数据 */
export interface ModelAnalysisData {
  feature_importance: Array<{ feature: string; importance: number }>
  metrics: Record<string, unknown>
}

/** 模型信息响应 */
export interface ModelInfoFullResponse {
  lightgbm: ModelAnalysisData
  xgboost: ModelAnalysisData
  evaluation?: Record<string, unknown>
}

/**
 * 获取回测结果列表
 * @param modelType 模型类型筛选
 * @param limit 返回条数
 */
export async function getBacktestResults(
  modelType?: 'lightgbm' | 'xgboost',
  limit: number = 10
): Promise<{ results: BacktestResultItem[]; count: number }> {
  const params: Record<string, string | number> = { limit }
  if (modelType) params.model_type = modelType
  return api.get('/backtest/results', params)
}

/**
 * 获取最新回测数据（含净值曲线）
 */
export async function getLatestBacktest(): Promise<Record<string, LatestBacktestData>> {
  return api.get('/backtest/latest')
}

/**
 * 获取双模型对比数据
 */
export async function getBacktestComparison(): Promise<{
  comparison: Record<string, unknown>
  nav_comparison: Record<string, unknown>
}> {
  return api.get('/backtest/comparison')
}

/**
 * 获取模型分析数据（特征重要性、NDCG等）
 */
export async function getModelAnalysis(): Promise<ModelInfoFullResponse> {
  return api.get('/backtest/model-info')
}

/**
 * 获取特征重要性列表
 * @param modelType 模型类型
 */
export async function getFeatureImportance(
  modelType: 'lightgbm' | 'xgboost' = 'xgboost'
): Promise<FeatureImportance[]> {
  const data = await getModelAnalysis()
  const modelData = data[modelType]
  if (!modelData?.feature_importance) return []
  return modelData.feature_importance
    .map((fi) => ({
      feature: fi.feature,
      importance: fi.importance,
    }))
    .sort((a, b) => b.importance - a.importance)
}

/** 回测与模型服务对象 */
export const backtestService = {
  getBacktestResults,
  getLatestBacktest,
  getBacktestComparison,
  getModelAnalysis,
  getFeatureImportance,
}

export default backtestService
