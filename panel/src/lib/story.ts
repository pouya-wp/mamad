import { faNumber, toman } from '@/lib/format'

/**
 * Draws the café's numbers as a 1080×1920 Instagram story, in the brand's own
 * language: pure black, bone type, the orange "1". Straight canvas so it can be
 * downloaded or copied without any library.
 */
export type StoryData = {
  label: string
  date: string
  revenue: number
  orders: number
  topItem?: string
  topQty?: number
  peakHour?: number
  margin?: number
}

const W = 1080
const H = 1920
const BONE = '#f5f2ec'
const MUTED = '#9d9da6'
const ONE = '#ff4f1a'

const font = (weight: number, size: number) => `${weight} ${size}px Vazirmatn, sans-serif`

/** "ONe" with the orange 1 standing in for the stem, centred on x. */
function wordmark(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
  ctx.textAlign = 'left'
  ctx.direction = 'ltr'
  ctx.font = font(200, size)
  const parts: [string, string][] = [
    ['ON', BONE],
    ['1', ONE],
    ['E', BONE],
  ]
  const total = parts.reduce((sum, [text]) => sum + ctx.measureText(text).width, 0)
  let cursor = x - total / 2
  for (const [text, color] of parts) {
    ctx.fillStyle = color
    ctx.fillText(text, cursor, y)
    cursor += ctx.measureText(text).width
  }
}

/** label on the right, value on the left — the way the panel sets a row. */
function row(ctx: CanvasRenderingContext2D, y: number, label: string, value: string) {
  ctx.direction = 'rtl'
  ctx.textAlign = 'right'
  ctx.font = font(400, 34)
  ctx.fillStyle = MUTED
  ctx.fillText(label, W - 110, y)

  ctx.textAlign = 'left'
  ctx.font = font(600, 40)
  ctx.fillStyle = BONE
  ctx.fillText(value, 110, y)

  ctx.strokeStyle = 'rgba(255,255,255,0.08)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(110, y + 34)
  ctx.lineTo(W - 110, y + 34)
  ctx.stroke()
}

export async function drawStory(canvas: HTMLCanvasElement, data: StoryData) {
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  try {
    await document.fonts.ready
  } catch {
    // fonts not ready: the fallback family still draws
  }

  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, W, H)

  // the warm light the brand always has in the corner
  const glow = ctx.createRadialGradient(W * 0.86, H * 0.1, 0, W * 0.86, H * 0.1, W * 0.95)
  glow.addColorStop(0, 'rgba(255,79,26,0.3)')
  glow.addColorStop(1, 'rgba(255,79,26,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, H)

  // the big "O" of the logo, ghosted behind the numbers
  ctx.strokeStyle = 'rgba(255,79,26,0.22)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(W / 2, H * 0.47, 380, 0, Math.PI * 2)
  ctx.stroke()
  ctx.strokeStyle = 'rgba(255,255,255,0.05)'
  ctx.beginPath()
  ctx.arc(W / 2, H * 0.47, 470, 0, Math.PI * 2)
  ctx.stroke()

  wordmark(ctx, W / 2, 300, 120)
  ctx.direction = 'ltr'
  ctx.textAlign = 'center'
  ctx.font = font(400, 30)
  ctx.letterSpacing = '14px'
  ctx.fillStyle = MUTED
  ctx.fillText('ONE CAFE · YAZD', W / 2, 360)
  ctx.letterSpacing = '0px'

  // the headline number
  ctx.direction = 'rtl'
  ctx.font = font(400, 38)
  ctx.fillStyle = MUTED
  ctx.fillText(data.label, W / 2, 780)

  ctx.font = font(200, 150)
  ctx.fillStyle = BONE
  ctx.fillText(toman(data.revenue), W / 2, 930)

  ctx.font = font(400, 40)
  ctx.fillStyle = ONE
  ctx.fillText('تومان', W / 2, 1000)

  // the rest of the day
  let y = 1210
  row(ctx, y, 'سفارش‌ها', faNumber(data.orders))
  if (data.topItem) row(ctx, (y += 120), 'پرفروش‌ترین', `${data.topItem}${data.topQty ? ` (${faNumber(data.topQty)})` : ''}`)
  if (data.peakHour !== undefined) row(ctx, (y += 120), 'شلوغ‌ترین ساعت', `${faNumber(data.peakHour)}:۰۰`)
  if (data.margin !== undefined) row(ctx, (y += 120), 'حاشیه سود', `${faNumber(Math.round(data.margin))}٪`)

  // footer
  ctx.direction = 'rtl'
  ctx.textAlign = 'center'
  ctx.font = font(400, 32)
  ctx.fillStyle = MUTED
  ctx.fillText(data.date, W / 2, H - 230)

  ctx.direction = 'ltr'
  ctx.font = font(600, 44)
  ctx.fillStyle = ONE
  ctx.fillText('@one1cafe', W / 2, H - 150)

  ctx.direction = 'ltr'
  ctx.font = font(300, 26)
  ctx.letterSpacing = '6px'
  ctx.fillStyle = 'rgba(245,242,236,0.45)'
  ctx.fillText('ONE GOOD COFFEE, ONE GOOD CAFE', W / 2, H - 90)
  ctx.letterSpacing = '0px'

  grain(ctx)
}

/** Film grain, the same texture the panel wears. Drawn as a tiled pattern, because
 *  putImageData would replace the pixels underneath instead of sitting on top of them. */
function grain(ctx: CanvasRenderingContext2D) {
  const tile = document.createElement('canvas')
  tile.width = tile.height = 140
  const paint = tile.getContext('2d')
  if (!paint) return
  const noise = paint.createImageData(tile.width, tile.height)
  for (let i = 0; i < noise.data.length; i += 4) {
    const value = (Math.random() * 255) | 0
    noise.data[i] = noise.data[i + 1] = noise.data[i + 2] = value
    noise.data[i + 3] = 255
  }
  paint.putImageData(noise, 0, 0)

  const pattern = ctx.createPattern(tile, 'repeat')
  if (!pattern) return
  ctx.save()
  ctx.globalAlpha = 0.045
  ctx.globalCompositeOperation = 'overlay'
  ctx.fillStyle = pattern
  ctx.fillRect(0, 0, W, H)
  ctx.restore()
}

export const storyBlob = (canvas: HTMLCanvasElement) =>
  new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
