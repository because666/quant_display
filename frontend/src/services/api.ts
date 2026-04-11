/**
 * Axios API 服务封装
 * 统一请求处理和错误处理
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type AxiosError } from 'axios'
import type { ApiResponse } from '../types'

/** 创建Axios实例 */
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** 请求拦截器 */
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

/** 响应拦截器 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError<ApiResponse<unknown>>) => {
    const errorMessage = error.response?.data?.error || error.message || '请求失败'
    
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    
    console.error('[API Error]', errorMessage)
    
    return Promise.reject(new Error(errorMessage))
  }
)

/**
 * GET 请求
 * @param url 请求路径
 * @param config 请求配置
 */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, config)
  return response.data.data
}

/**
 * POST 请求
 * @param url 请求路径
 * @param data 请求数据
 * @param config 请求配置
 */
export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.post<ApiResponse<T>>(url, data, config)
  return response.data.data
}

/**
 * PUT 请求
 * @param url 请求路径
 * @param data 请求数据
 * @param config 请求配置
 */
export async function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.put<ApiResponse<T>>(url, data, config)
  return response.data.data
}

/**
 * DELETE 请求
 * @param url 请求路径
 * @param config 请求配置
 */
export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.delete<ApiResponse<T>>(url, config)
  return response.data.data
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ status: string; version: string }> {
  const response = await axios.get('/api/health')
  return response.data
}

/** API服务对象 */
export const api = {
  get,
  post,
  put,
  delete: del,
  healthCheck,
  client: apiClient,
}

export default api
