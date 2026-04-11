/**
 * 选股池相关API服务
 * 连接后端获取股票列表、模型排序结果、截面日期
 */
import { api } from './api'
import type { FeatureImportance } from '../types'

/** 股票列表项 */
export interface StockItem {
  /** 股票代码 */
  code: string
  /** 股票名称 */
  name: string
}

/** 排序股票项 */
export interface RankedStock {
  /** 排名 */
  rank: number
  /** 股票代码 */
  code: string
  /** 模型得分 */
  score: number
}

/** 股票列表响应 */
export interface StockListResponse {
  stocks: StockItem[]
  total: number
  page: number
  page_size: number
}

/** 排序结果响应 */
export interface RankResponse {
  ranked_stocks: RankedStock[]
  feature_importance_top20: Array<{ feature: string; importance: number }>
  model_type: string
  timestamp: string
  total_pool_size: number
}

/** 截面日期响应 */
export interface DatesResponse {
  dates: string[]
  total: number
  latest: string | null
}

/** 模型信息响应 */
export interface ModelInfoResponse {
  model_type: string
  trained_at: string | null
  feature_importance: Record<string, number>
  feature_importance_list: Array<{ feature: string; importance: number }>
}

/**
 * 获取可用截面日期列表
 */
export async function getAvailableDates(): Promise<DatesResponse> {
  return api.get<DatesResponse>('/stockpool/dates')
}

/**
 * 获取股票列表（分页）
 * @param page 页码
 * @param pageSize 每页数量
 * @param keyword 搜索关键词
 */
export async function getStockList(
  page: number = 1,
  pageSize: number = 100,
  keyword?: string
): Promise<StockListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (keyword) params.keyword = keyword
  return api.get<StockListResponse>('/stockpool/list', params)
}

/**
 * 获取股票池总数
 */
export async function getStockCount(): Promise<{ total: number }> {
  return api.get<{ total: number }>('/stockpool/count')
}

/**
 * 使用模型对股票池排序
 * @param topN 返回排名前N只股票
 * @param modelType 模型类型
 * @param stockCodes 自定义股票池（为空则全量）
 * @param date 截面日期 YYYY-MM-DD
 */
export async function rankStocks(
  topN: number = 50,
  modelType: 'lightgbm' | 'xgboost' = 'xgboost',
  stockCodes?: string[],
  date?: string
): Promise<RankResponse> {
  const body: Record<string, unknown> = {
    model_type: modelType,
    top_n: topN,
  }
  if (stockCodes && stockCodes.length > 0) {
    body.stock_codes = stockCodes
  }
  if (date) {
    body.date = date
  }
  return api.post<RankResponse>('/stockpool/rank', body, { timeout: 120000 })
}

/**
 * 获取模型信息
 * @param model 模型类型
 */
export async function getModelInfo(
  model: 'lightgbm' | 'xgboost' = 'xgboost'
): Promise<ModelInfoResponse> {
  return api.get<ModelInfoResponse>(`/model/info?model_type=${model}`)
}

/**
 * 获取特征重要性列表
 * @param model 模型类型
 */
export async function getFeatureImportance(
  model: 'lightgbm' | 'xgboost' = 'xgboost'
): Promise<FeatureImportance[]> {
  const info = await getModelInfo(model)
  const fi = info.feature_importance || {}

  return Object.entries(fi)
    .map(([feature, importance]) => ({
      feature,
      importance: importance as number,
    }))
    .sort((a, b) => b.importance - a.importance)
}

/** 选股池服务对象 */
export const stockPoolService = {
  getAvailableDates,
  getStockList,
  getStockCount,
  rankStocks,
  getModelInfo,
  getFeatureImportance,
}

export default stockPoolService
