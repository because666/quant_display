/**
 * 全局TypeScript类型定义
 */

/** 股票基础信息 */
export interface Stock {
  /** 股票代码 */
  code: string
  /** 股票名称 */
  name: string
  /** 预测得分 */
  score: number
  /** 涨跌幅 */
  pctChg?: number
  /** 当前价格 */
  currentPrice?: number
}

/** 持仓信息 */
export interface Holding {
  /** 股票代码 */
  code: string
  /** 股票名称 */
  name: string
  /** 持仓数量 */
  quantity: number
  /** 成本价 */
  costPrice: number
  /** 当前价 */
  currentPrice: number
  /** 盈亏 */
  profit: number
  /** 收益率 */
  profitPercent: number
}

/** 回测指标 */
export interface BacktestMetrics {
  /** 年化收益率 */
  annualReturn: number
  /** 夏普比率 */
  sharpeRatio: number
  /** 最大回撤 */
  maxDrawdown: number
  /** 胜率 */
  winRate: number
  /** 换手率 */
  turnoverRate: number
  /** 总收益 */
  totalReturn: number
}

/** 回测结果 */
export interface BacktestResult {
  /** 模型名称 */
  model: 'lightgbm' | 'xgboost'
  /** 净值序列 */
  navSeries: Array<{ date: string; value: number }>
  /** 回测指标 */
  metrics: BacktestMetrics
  /** 持仓变动记录 */
  holdings: Array<{
    date: string
    stocks: string[]
  }>
}

/** 特征重要性 */
export interface FeatureImportance {
  /** 特征名称 */
  feature: string
  /** 重要性值 */
  importance: number
}

/** NDCG曲线数据 */
export interface NDCGCurve {
  /** K值 */
  k: number
  /** NDCG值 */
  ndcg: number
}

/** 模型评估结果 */
export interface ModelEvaluation {
  /** 模型名称 */
  model: 'lightgbm' | 'xgboost'
  /** 特征重要性列表 */
  featureImportance: FeatureImportance[]
  /** NDCG曲线数据 */
  ndcgCurve: NDCGCurve[]
  /** 训练参数 */
  params: Record<string, unknown>
}

/** 因子数据 */
export interface FactorData {
  /** 因子名称 */
  name: string
  /** 因子值 */
  value: number
  /** 日期 */
  date: string
  /** 股票代码 */
  stockCode: string
}

/** 因子统计 */
export interface FactorStats {
  /** 因子名称 */
  name: string
  /** 均值 */
  mean: number
  /** 标准差 */
  std: number
  /** IC均值 */
  icMean: number
  /** IC标准差 */
  icStd: number
  /** ICIR */
  icir: number
}

/** AI建议 */
export interface AIAdvice {
  /** 建议内容（Markdown格式） */
  content: string
  /** 生成时间 */
  timestamp: string
  /** 推荐股票列表 */
  recommendedStocks: Stock[]
}

/** 影子账户 */
export interface ShadowAccount {
  /** 账户名 */
  name: string
  /** 总资产 */
  totalAssets: number
  /** 持仓市值 */
  holdingValue: number
  /** 可用资金 */
  availableCash: number
  /** 总盈亏 */
  totalProfit: number
  /** 收益率 */
  returnRate: number
  /** 持仓列表 */
  holdings: Holding[]
  /** 回测时间范围 */
  backtestRange?: TimeRange
  /** 预测时间范围 */
  predictRange?: TimeRange
}

/** 时间范围 */
export interface TimeRange {
  /** 起始日期 */
  startDate: string
  /** 结束日期 */
  endDate: string
}

/** API响应通用格式 */
export interface ApiResponse<T> {
  /** 是否成功 */
  success: boolean
  /** 响应数据 */
  data: T
  /** 错误信息 */
  error?: string
  /** 时间戳 */
  timestamp: string
}

/** 分页请求参数 */
export interface PaginationParams {
  /** 页码 */
  page: number
  /** 每页数量 */
  pageSize: number
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  /** 数据列表 */
  items: T[]
  /** 总数 */
  total: number
  /** 当前页 */
  page: number
  /** 每页数量 */
  pageSize: number
  /** 总页数 */
  totalPages: number
}
