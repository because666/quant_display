/**
 * 状态管理测试组件
 * 用于验证Zustand store是否正常工作
 */
import { useAppStore } from '../store/useAppStore'

function StoreTest() {
  const { 
    selectedModel, 
    accountName, 
    setSelectedModel, 
    setAccountName 
  } = useAppStore()

  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      <h3 className="font-bold mb-2">状态管理测试</h3>
      <p>当前模型: {selectedModel}</p>
      <p>账户名: {accountName || '(未设置)'}</p>
      <div className="flex gap-2 mt-2">
        <button 
          onClick={() => setSelectedModel('lightgbm')}
          className="px-2 py-1 bg-blue-500 text-white rounded text-sm"
        >
          LightGBM
        </button>
        <button 
          onClick={() => setSelectedModel('xgboost')}
          className="px-2 py-1 bg-green-500 text-white rounded text-sm"
        >
          XGBoost
        </button>
        <button 
          onClick={() => setAccountName('测试账户')}
          className="px-2 py-1 bg-purple-500 text-white rounded text-sm"
        >
          设置账户
        </button>
      </div>
    </div>
  )
}

export default StoreTest
