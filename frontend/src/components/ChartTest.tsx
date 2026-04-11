/**
 * 图表测试页面
 * 验证各类图表组件是否正常工作
 */
import { Card } from '../components/ui'
import { LineChart, BarChart, Heatmap, ResponsiveChart } from '../components/Charts'

const mockLineData = {
  xAxisData: ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06'],
  series: [
    {
      name: '策略收益',
      data: [0.05, 0.08, 0.12, 0.15, 0.18, 0.22],
      color: '#2563eb',
    },
    {
      name: '基准收益',
      data: [0.03, 0.05, 0.07, 0.09, 0.11, 0.13],
      color: '#16a34a',
    },
  ],
}

const mockBarData = [
  { name: '动量因子_5日', value: 0.85 },
  { name: '波动率_20日', value: 0.72 },
  { name: '换手率', value: 0.68 },
  { name: 'RSI_14', value: 0.55 },
  { name: 'MACD', value: 0.48 },
  { name: 'ATR', value: 0.42 },
  { name: '布林带位置', value: 0.38 },
  { name: '成交额', value: 0.35 },
]

const mockHeatmapData = [
  [0.05, 0.08, -0.02, 0.12, 0.15, 0.08, 0.10, 0.05, -0.03, 0.08, 0.12, 0.15],
  [0.03, 0.06, 0.04, 0.08, 0.10, 0.12, -0.05, 0.08, 0.06, 0.10, 0.08, 0.12],
  [0.08, 0.10, 0.06, -0.04, 0.12, 0.15, 0.08, 0.10, 0.05, 0.08, 0.12, 0.18],
  [0.02, 0.04, 0.08, 0.10, 0.06, 0.08, 0.12, 0.15, 0.10, 0.08, 0.06, 0.10],
]

const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
const years = ['2021', '2022', '2023', '2024']

function ChartTest() {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">图表组件测试</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card header="折线图 - 收益曲线">
          <LineChart
            xAxisData={mockLineData.xAxisData}
            series={mockLineData.series}
            title="策略收益对比"
            yAxisUnit="%"
            areaStyle
          />
        </Card>

        <Card header="条形图 - 特征重要性（横向）">
          <BarChart
            data={mockBarData}
            title="特征重要性 Top 8"
            horizontal
            showLabel
            sort="desc"
          />
        </Card>

        <Card header="条形图 - 特征重要性（纵向）">
          <BarChart
            data={mockBarData.slice(0, 5)}
            horizontal={false}
            showLabel
            sort="desc"
            height="300px"
          />
        </Card>

        <Card header="热力图 - 月度收益">
          <Heatmap
            data={mockHeatmapData}
            xLabels={months}
            yLabels={years}
            title="月度收益热力图"
            colorRange={[-0.1, 0.2]}
          />
        </Card>
      </div>

      <Card header="响应式图表测试">
        <p className="text-sm text-gray-500 mb-4">
          调整窗口大小，观察图表是否自适应
        </p>
        <ResponsiveChart height="300px">
          <LineChart
            xAxisData={mockLineData.xAxisData}
            series={[mockLineData.series[0]]}
            height="300px"
          />
        </ResponsiveChart>
      </Card>
    </div>
  )
}

export default ChartTest
