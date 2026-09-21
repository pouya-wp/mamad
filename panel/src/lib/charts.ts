import { BarChart, LineChart, LinesChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { LegacyGridContainLabel } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

// Canvas, not SVG: glow (shadowBlur) and the moving comet repaint cheaply on canvas.
// ECharts 6 moved `grid.containLabel` into an opt-in feature.
use([CanvasRenderer, LineChart, LinesChart, BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, LegacyGridContainLabel])

export const CHART = {
  one: '#ff4f1a',
  oneSoft: 'rgba(255, 79, 26, 0.18)',
  bone: '#f5f2ec',
  grid: 'rgba(255, 255, 255, 0.05)',
  axis: '#6b6b74',
  palette: ['#ff4f1a', '#f5f2ec', '#ff9a73', '#9d9da6', '#b82f08', '#3a3a41'],
  font: 'Vazirmatn, sans-serif',
}

export const tooltipBase = {
  backgroundColor: '#141417',
  borderColor: 'rgba(255,255,255,0.08)',
  textStyle: { color: '#ececef', fontFamily: CHART.font, fontSize: 12 },
  extraCssText: 'border-radius:12px;box-shadow:0 12px 40px -12px #000;direction:rtl;',
}
