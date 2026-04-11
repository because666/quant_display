/**
 * SSE 流式响应服务
 * 处理Server-Sent Events流式数据
 */

type OnChunkCallback = (chunk: string) => void
type OnCompleteCallback = () => void
type OnErrorCallback = (error: Error) => void

interface SSEOptions {
  /** 数据块回调 */
  onChunk: OnChunkCallback
  /** 完成回调 */
  onComplete: OnCompleteCallback
  /** 错误回调 */
  onError?: OnErrorCallback
  /** 重连次数 */
  maxRetries?: number
  /** 重连间隔（毫秒） */
  retryInterval?: number
}

/**
 * 创建SSE连接获取流式数据
 * @param url 请求URL
 * @param options SSE配置选项
 * @returns 返回一个abort函数用于中断连接
 */
export function createSSEConnection(
  url: string,
  options: SSEOptions
): () => void {
  const {
    onChunk,
    onComplete,
    onError,
    maxRetries = 3,
    retryInterval = 1000,
  } = options

  let retryCount = 0
  let aborted = false
  let eventSource: EventSource | null = null

  const connect = () => {
    if (aborted) return

    try {
      eventSource = new EventSource(url)

      eventSource.onmessage = (event) => {
        const data = event.data
        if (data === '[DONE]') {
          eventSource?.close()
          onComplete()
          return
        }
        try {
          const parsed = JSON.parse(data)
          if (parsed.done) {
            eventSource?.close()
            onComplete()
            return
          }
          if (parsed.content) {
            onChunk(parsed.content)
            return
          }
        } catch {
          // 非JSON格式，直接传递
        }
        onChunk(data)
      }

      eventSource.onerror = () => {
        eventSource?.close()

        if (!aborted && retryCount < maxRetries) {
          retryCount++
          console.log(`[SSE] 连接断开，${retryInterval * retryCount}ms后重连 (${retryCount}/${maxRetries})`)
          setTimeout(connect, retryInterval * retryCount)
        } else {
          const err = new Error('SSE连接失败，已达到最大重连次数')
          onError?.(err)
        }
      }

      eventSource.onopen = () => {
        retryCount = 0
        console.log('[SSE] 连接已建立')
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('SSE连接创建失败')
      onError?.(err)
    }
  }

  connect()

  return () => {
    aborted = true
    eventSource?.close()
    console.log('[SSE] 连接已断开')
  }
}

/**
 * 使用Fetch API处理流式响应
 * @param url 请求URL
 * @param options SSE配置选项
 * @returns 返回一个abort函数用于中断连接
 */
export async function fetchStreaming(
  url: string,
  options: SSEOptions & { body?: unknown; method?: string }
): Promise<() => void> {
  const {
    onChunk,
    onComplete,
    onError,
    body,
    method = 'POST',
  } = options

  const controller = new AbortController()
  const { signal } = controller

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP错误: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法获取响应流')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    const processStream = async () => {
      try {
        while (!signal.aborted) {
          const { done, value } = await reader.read()

          if (done) {
            if (buffer.trim()) {
              onChunk(buffer)
            }
            onComplete()
            break
          }

          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') {
                onComplete()
                return
              }
              if (data.trim()) {
                try {
                  const parsed = JSON.parse(data)
                  if (parsed.error) {
                    const errMsg = parsed.message || '未知错误'
                    onError?.(new Error(errMsg))
                    return
                  }
                  if (parsed.content) {
                    onChunk(parsed.content)
                    continue
                  }
                } catch {
                  // 非JSON格式
                }
                onChunk(data)
              }
            }
          }
        }
      } catch (error) {
        if (!signal.aborted) {
          const err = error instanceof Error ? error : new Error('流处理错误')
          onError?.(err)
        }
      }
    }

    processStream()
  } catch (error) {
    if (!signal.aborted) {
      const err = error instanceof Error ? error : new Error('请求失败')
      onError?.(err)
    }
  }

  return () => {
    controller.abort()
  }
}

/**
 * 获取实时AI建议
 * @param accountName 账户名
 * @param onChunk 数据块回调
 * @param onComplete 完成回调
 * @param onError 错误回调
 * @returns 返回abort函数
 */
export function fetchStreamingAdvice(
  accountName: string,
  onChunk: OnChunkCallback,
  onComplete: OnCompleteCallback,
  onError?: OnErrorCallback
): () => void {
  let abortFn: (() => void) | null = null

  fetchStreaming('/api/v1/realtime_advice', {
    method: 'POST',
    body: { account_name: accountName },
    onChunk,
    onComplete,
    onError,
  }).then((fn) => {
    abortFn = fn
  }).catch((err) => {
    onError?.(err instanceof Error ? err : new Error('请求失败'))
  })

  return () => {
    abortFn?.()
  }
}

/** SSE服务对象 */
export const sse = {
  createSSEConnection,
  fetchStreaming,
  fetchStreamingAdvice,
}

export default sse
