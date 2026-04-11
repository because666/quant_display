/**
 * AI推荐页面
 * 实现流式Markdown渲染的AI建议展示
 * 
 * @author 量化策略系统
 * @version 2.0
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { fetchStreamingAdvice } from '../services/sse'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AIAdvice } from '../types'

type StreamingStatus = 'idle' | 'streaming' | 'completed' | 'error'

/**
 * 毛玻璃卡片样式
 */
const glassCardStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.85)',
  backdropFilter: 'blur(20px)',
  WebkitBackdropFilter: 'blur(20px)',
  borderRadius: '24px',
  border: '1px solid rgba(255, 255, 255, 0.5)',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.03), 0 6px 12px rgba(0, 0, 0, 0.02)',
  transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
}

/**
 * 按钮样式
 */
const buttonStyle = (variant: 'primary' | 'secondary' = 'primary'): React.CSSProperties => ({
  padding: '12px 24px',
  borderRadius: '980px',
  fontSize: '14px',
  fontWeight: 500,
  border: 'none',
  cursor: 'pointer',
  transition: 'all 0.4s cubic-bezier(0.25, 0.1, 0.25, 1)',
  background: variant === 'primary' ? '#0071E3' : 'rgba(0, 0, 0, 0.04)',
  color: variant === 'primary' ? '#FFFFFF' : '#86868B',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '8px',
})

function AIRecommendation() {
  const { accountName, adviceHistory, addAdviceToHistory } = useAppStore()
  const [streamingContent, setStreamingContent] = useState('')
  const [status, setStatus] = useState<StreamingStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [selectedHistory, setSelectedHistory] = useState<AIAdvice | null>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const contentRef = useRef('')

  const isStreaming = status === 'streaming'
  const hasContent = streamingContent.length > 0

  const handleFetchAdvice = useCallback(() => {
    if (!accountName) {
      setError('请先在影子账户页面创建账户')
      return
    }

    setStreamingContent('')
    contentRef.current = ''
    setStatus('streaming')
    setError(null)
    setSelectedHistory(null)

    const abort = fetchStreamingAdvice(
      accountName,
      (chunk) => {
        contentRef.current += chunk
        setStreamingContent(contentRef.current)
      },
      () => {
        setStatus('completed')
        const finalContent = contentRef.current
        if (finalContent) {
          const newAdvice: AIAdvice = {
            content: finalContent,
            timestamp: new Date().toISOString(),
            recommendedStocks: [],
          }
          addAdviceToHistory(newAdvice)
        }
      },
      (err) => {
        setStatus('error')
        setError(err.message)
      }
    )

    abortRef.current = abort
  }, [accountName, addAdviceToHistory])

  const handleStopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setStatus('completed')
  }, [])

  const handleRetry = useCallback(() => {
    handleFetchAdvice()
  }, [handleFetchAdvice])

  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current()
      }
    }
  }, [])

  if (!accountName) {
    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '60px 24px 80px' }}>
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontSize: '40px', fontWeight: 600, color: '#1D1D1F', marginBottom: '8px', letterSpacing: '-0.02em' }}>
            AI智能推荐
          </h1>
          <p style={{ fontSize: '15px', color: '#86868B' }}>
            基于模型预测的个性化投资建议
          </p>
        </div>
        
        <div style={{ maxWidth: '640px' }}>
          {/* 主提示框 */}
          <div style={{ ...glassCardStyle, padding: '32px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#1D1D1F', marginBottom: '12px' }}>
                  开启AI智能投资助手
                </h3>
                <p style={{ fontSize: '14px', color: '#86868B', lineHeight: 1.7, marginBottom: '20px' }}>
                  创建影子账户后，AI将基于您的持仓和市场数据，提供个性化的投资建议和买卖时机分析
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button
                    onClick={() => window.location.href = '/shadow-account'}
                    style={{
                      ...buttonStyle('primary'),
                      boxShadow: '0 4px 20px rgba(0, 113, 227, 0.3)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.02)'
                      e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 113, 227, 0.4)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)'
                      e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 113, 227, 0.3)'
                    }}
                  >
                    创建影子账户
                  </button>
                  <button
                    onClick={() => window.location.href = '/strategy'}
                    style={{
                      ...buttonStyle('secondary'),
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.08)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)'
                    }}
                  >
                    先了解投资策略 →
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* 功能特点 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {[
              { num: '01', title: '智能分析', desc: '实时市场数据' },
              { num: '02', title: '个性化建议', desc: '基于持仓定制' },
              { num: '03', title: '实时更新', desc: '动态调整策略' },
            ].map((item) => (
              <div
                key={item.num}
                style={{
                  ...glassCardStyle,
                  padding: '20px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 500, color: '#86868B', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
                  {item.num}
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#1D1D1F', marginBottom: '4px' }}>
                  {item.title}
                </div>
                <div style={{ fontSize: '13px', color: '#86868B' }}>
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '60px 24px 80px' }}>
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '40px', fontWeight: 600, color: '#1D1D1F', marginBottom: '8px', letterSpacing: '-0.02em' }}>
          AI智能推荐
        </h1>
        <p style={{ fontSize: '15px', color: '#86868B' }}>
          当前账户：<span style={{ fontWeight: 600, color: '#0071E3' }}>{accountName}</span>
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '24px' }}>
        {/* 左侧：AI建议主区域 */}
        <div style={glassCardStyle}>
          <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>AI建议</span>
            <div style={{ display: 'flex', gap: '12px' }}>
              {isStreaming ? (
                <button
                  onClick={handleStopStreaming}
                  style={buttonStyle('secondary')}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255, 59, 48, 0.1)'; e.currentTarget.style.color = '#FF3B30' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(0, 0, 0, 0.04)'; e.currentTarget.style.color = '#86868B' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                  </svg>
                  停止生成
                </button>
              ) : (
                <>
                  <button
                    onClick={handleFetchAdvice}
                    style={buttonStyle('primary')}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.02)'
                      e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 113, 227, 0.4)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)'
                      e.currentTarget.style.boxShadow = 'none'
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 5v14M5 12h14"/>
                    </svg>
                    {hasContent ? '重新生成' : '获取最新建议'}
                  </button>
                  {status === 'error' && (
                    <button
                      onClick={handleRetry}
                      style={buttonStyle('secondary')}
                    >
                      重试
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          <div style={{ padding: '32px' }}>
            {error && (
              <div style={{ marginBottom: '20px', padding: '16px 20px', background: 'rgba(255, 59, 48, 0.08)', borderRadius: '12px', color: '#FF3B30', fontSize: '14px' }}>
                {error}
              </div>
            )}

            <div style={{ minHeight: '400px' }}>
              {!hasContent && !isStreaming && !selectedHistory ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '400px', color: '#86868B' }}>
                  <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginBottom: '16px', opacity: 0.3 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <p style={{ fontSize: '16px', marginBottom: '8px' }}>点击"获取最新建议"开始</p>
                  <p style={{ fontSize: '14px', opacity: 0.7 }}>AI将基于您的持仓和市场数据生成投资建议</p>
                </div>
              ) : (
                <div style={{ fontSize: '14px', lineHeight: 1.8, color: '#1D1D1F' }}>
                  {selectedHistory ? (
                    <MarkdownContent content={selectedHistory.content} />
                  ) : (
                    <MarkdownContent content={streamingContent} />
                  )}
                  {isStreaming && <TypingCursor />}
                </div>
              )}
            </div>

            {isStreaming && (
              <div style={{ marginTop: '24px', display: 'flex', alignItems: 'center', fontSize: '14px', color: '#0071E3' }}>
                <svg style={{ animation: 'spin 1s linear infinite', marginRight: '8px' }} width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                正在生成建议...
              </div>
            )}
          </div>
        </div>

        {/* 右侧：历史建议 + 使用说明 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* 历史建议 */}
          <div style={glassCardStyle}>
            <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
              历史建议
            </div>
            <div style={{ padding: '24px 32px' }}>
              {adviceHistory.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px 0', color: '#86868B', fontSize: '14px' }}>
                  暂无历史建议
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '400px', overflowY: 'auto' }}>
                  {adviceHistory.map((advice, index) => (
                    <HistoryItem
                      key={advice.timestamp}
                      advice={advice}
                      index={index}
                      total={adviceHistory.length}
                      isSelected={selectedHistory?.timestamp === advice.timestamp}
                      onClick={() => {
                        setSelectedHistory(advice)
                        setStreamingContent('')
                        setStatus('completed')
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 使用说明 */}
          <div style={glassCardStyle}>
            <div style={{ padding: '24px 32px', borderBottom: '1px solid rgba(0, 0, 0, 0.05)', fontWeight: 600, fontSize: '17px', color: '#1D1D1F' }}>
              使用说明
            </div>
            <div style={{ padding: '24px 32px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '14px', color: '#86868B' }}>
                {[
                  '点击"获取最新建议"按钮，AI将分析您的持仓和市场数据',
                  '建议内容将实时流式显示，包含买入/卖出区间推荐',
                  '可随时停止生成，或重新生成新的建议',
                  '历史建议保存在右侧列表，可随时查看',
                ].map((text, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <span style={{ color: '#0071E3', fontWeight: 600, flexShrink: 0 }}>{i + 1}.</span>
                    <span>{text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '16px', color: '#1D1D1F', letterSpacing: '-0.01em' }}>{children}</h1>,
        h2: ({ children }) => <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '12px', marginTop: '24px', color: '#1D1D1F' }}>{children}</h2>,
        h3: ({ children }) => <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', marginTop: '16px', color: '#1D1D1F' }}>{children}</h3>,
        p: ({ children }) => <p style={{ marginBottom: '12px', color: '#86868B', lineHeight: 1.8 }}>{children}</p>,
        ul: ({ children }) => <ul style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ul>,
        ol: ({ children }) => <ol style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ol>,
        li: ({ children }) => <li style={{ color: '#86868B', marginBottom: '4px' }}>{children}</li>,
        strong: ({ children }) => <strong style={{ fontWeight: 600, color: '#1D1D1F' }}>{children}</strong>,
        code: ({ className, children }) => {
          const isInline = !className
          if (isInline) {
            return <code style={{ background: '#F5F5F7', padding: '2px 6px', borderRadius: '4px', fontSize: '13px', color: '#AF52DE', fontFamily: "'JetBrains Mono', monospace" }}>{children}</code>
          }
          return (
            <pre style={{ background: '#1D1D1F', color: '#F5F5F7', padding: '16px', borderRadius: '12px', fontSize: '13px', overflowX: 'auto', marginBottom: '16px' }}>
              <code>{children}</code>
            </pre>
          )
        },
        blockquote: ({ children }) => (
          <blockquote style={{ borderLeft: '3px solid #0071E3', paddingLeft: '16px', marginBottom: '16px', color: '#86868B' }}>
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div style={{ overflowX: 'auto', marginBottom: '16px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead style={{ background: '#F5F5F7' }}>{children}</thead>,
        th: ({ children }) => (
          <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, color: '#1D1D1F', borderBottom: '1px solid #E8E8ED' }}>{children}</th>
        ),
        td: ({ children }) => (
          <td style={{ padding: '12px 16px', color: '#86868B', borderBottom: '1px solid #F5F5F7' }}>{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

function TypingCursor() {
  return (
    <span style={{ display: 'inline-block', width: '2px', height: '20px', background: '#0071E3', marginLeft: '4px', animation: 'blink 1s infinite' }} />
  )
}

function HistoryItem({
  advice,
  index,
  total,
  isSelected,
  onClick,
}: {
  advice: AIAdvice
  index: number
  total: number
  isSelected: boolean
  onClick: () => void
}) {
  const date = new Date(advice.timestamp)
  const timeStr = date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  const preview = advice.content.slice(0, 50).replace(/[#*`]/g, '')

  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        textAlign: 'left',
        padding: '16px',
        borderRadius: '12px',
        transition: 'all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1)',
        background: isSelected ? 'rgba(0, 113, 227, 0.08)' : '#F5F5F7',
        border: isSelected ? '1px solid rgba(0, 113, 227, 0.2)' : '1px solid transparent',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = '#E8E8ED'
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = '#F5F5F7'
        }
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontSize: '12px', color: '#86868B' }}>#{total - index}</span>
        <span style={{ fontSize: '12px', color: '#86868B' }}>{timeStr}</span>
      </div>
      <p style={{ fontSize: '13px', color: '#1D1D1F', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
        {preview}...
      </p>
    </button>
  )
}

export default AIRecommendation
