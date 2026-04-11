/**
 * 影子账户API服务
 * 对接后端影子账户CRUD接口
 */
import { api } from './api'

/** 持仓项 */
export interface AccountHolding {
  stock_code: string
  stock_name?: string
  quantity: number
  cost_price: number
}

/** 账户详情 */
export interface AccountDetail {
  id: number
  account_name: string
  holdings: AccountHolding[]
  backtest_start: string | null
  backtest_end: string | null
  prediction_start: string | null
  prediction_end: string | null
  created_at: string
}

/** 账户列表项 */
export interface AccountListItem {
  id: number
  account_name: string
  holding_count: number
  created_at: string
}

/** AI建议记录 */
export interface AdviceRecord {
  id: number
  request_time: string
  advice_markdown: string
  top_stocks: Array<{ code: string; score: number }>
}

/**
 * 获取所有账户列表
 */
export async function getAccounts(): Promise<AccountListItem[]> {
  const res = await api.get<{ accounts: AccountListItem[] }>('/account/')
  return res.accounts || []
}

/**
 * 获取账户详情
 * @param accountId 账户ID
 */
export async function getAccount(accountId: number): Promise<AccountDetail> {
  return api.get<AccountDetail>(`/account/${accountId}`)
}

/**
 * 创建新账户
 * @param name 账户名称
 */
export async function createAccount(name: string): Promise<AccountDetail> {
  return api.post<AccountDetail>('/account/', { account_name: name })
}

/**
 * 更新账户持仓
 * @param accountId 账户ID
 * @param holdings 持仓列表
 */
export async function updateHoldings(
  accountId: number,
  holdings: AccountHolding[]
): Promise<AccountDetail> {
  return api.put<AccountDetail>(`/account/${accountId}/holdings`, { holdings })
}

/**
 * 更新账户时间范围
 * @param accountId 账户ID
 * @param backtestStart 回测起始日期
 * @param backtestEnd 回测结束日期
 * @param predictionStart 预测起始日期
 * @param predictionEnd 预测结束日期
 */
export async function updateTimeRange(
  accountId: number,
  backtestStart?: string,
  backtestEnd?: string,
  predictionStart?: string,
  predictionEnd?: string
): Promise<AccountDetail> {
  const body: Record<string, string> = {}
  if (backtestStart) body.backtest_start = backtestStart
  if (backtestEnd) body.backtest_end = backtestEnd
  if (predictionStart) body.prediction_start = predictionStart
  if (predictionEnd) body.prediction_end = predictionEnd
  return api.put<AccountDetail>(`/account/${accountId}/time-range`, body)
}

/**
 * 删除账户
 * @param accountId 账户ID
 */
export async function deleteAccount(accountId: number): Promise<void> {
  await api.delete(`/account/${accountId}`)
}

/**
 * 获取账户AI建议历史
 * @param accountId 账户ID
 */
export async function getAdviceHistory(accountId: number): Promise<AdviceRecord[]> {
  const res = await api.get<{ advices: AdviceRecord[] }>(`/account/${accountId}/advices`)
  return res.advices || []
}

/** 影子账户服务对象 */
export const accountService = {
  getAccounts,
  getAccount,
  createAccount,
  updateHoldings,
  updateTimeRange,
  deleteAccount,
  getAdviceHistory,
}

export default accountService
