import { defineStore } from 'pinia'
import { ref } from 'vue'

import { get, post } from '@/lib/api'
import { sound } from '@/lib/sound'

export type ValueFormat = 'toman' | 'number' | 'percent' | 'date' | 'text'

export type MetricsBlock = {
  type: 'metrics'
  title?: string
  items: { label: string; value: number; format: ValueFormat; change?: number | null; hint?: string }[]
}

export type ListBlock = {
  type: 'list'
  title?: string
  items: { label: string; value: number | string; format?: ValueFormat; uom?: string; hint?: string; tone?: 'ok' | 'warn' | 'danger' }[]
}

export type ProposalBlock = {
  type: 'proposal'
  id: string
  title: string
  lines: { label: string; value: number | string; format?: ValueFormat; uom?: string }[]
  status: 'pending' | 'working' | 'done' | 'cancelled' | 'error'
  result?: string
}

export type AgentBlock = MetricsBlock | ListBlock | ProposalBlock

export type ChatMessage = {
  id: number
  role: 'user' | 'assistant'
  text: string
  blocks?: AgentBlock[]
  suggestions?: string[]
  pending?: boolean
  /** a reply that hasn't finished its typing animation yet */
  fresh?: boolean
}

type ChatReply = { text: string; blocks: AgentBlock[]; suggestions: string[]; mode: 'demo' | 'live' }

let nextId = 1

export const useAgent = defineStore('agent', () => {
  const open = ref(false)
  const busy = ref(false)
  const mode = ref<'demo' | 'live'>('demo')
  const suggestions = ref<string[]>([])
  const messages = ref<ChatMessage[]>([])
  /** Bumped whenever the agent changes data, so open pages can refresh. */
  const dataVersion = ref(0)

  async function loadStatus() {
    const s = await get<{ mode: 'demo' | 'live'; suggestions: string[] }>('cafe_app.api.agent.status').catch(() => null)
    if (s) {
      mode.value = s.mode
      suggestions.value = s.suggestions
    }
  }

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy.value) return
    open.value = true

    const history = messages.value
      .filter((m) => !m.pending && m.text)
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.text }))

    messages.value.push({ id: nextId++, role: 'user', text: message })
    const reply: ChatMessage = { id: nextId++, role: 'assistant', text: '', pending: true }
    messages.value.push(reply)
    busy.value = true

    try {
      const data = await post<ChatReply>('cafe_app.api.agent.chat', { message, history })
      mode.value = data.mode
      Object.assign(reply, { text: data.text, blocks: data.blocks, suggestions: data.suggestions, pending: false, fresh: true })
      sound.reply()
    } catch (error) {
      Object.assign(reply, { text: error instanceof Error ? error.message : 'خطایی رخ داد', pending: false, fresh: true })
    } finally {
      busy.value = false
      // the reply object inside the reactive array must be re-read to trigger updates
      messages.value = [...messages.value]
    }
  }

  async function confirm(block: ProposalBlock) {
    block.status = 'working'
    try {
      const result = await post<{ message: string; document: string }>('cafe_app.api.agent.confirm', { proposal_id: block.id })
      block.status = 'done'
      block.result = `${result.message} · ${result.document}`
      sound.stamp()
      dataVersion.value++
    } catch (error) {
      block.status = 'error'
      block.result = error instanceof Error ? error.message : 'ثبت نشد'
    }
  }

  async function cancel(block: ProposalBlock) {
    block.status = 'cancelled'
    sound.dismiss()
    await post('cafe_app.api.agent.cancel', { proposal_id: block.id }).catch(() => undefined)
  }

  function ask(text: string) {
    open.value = true
    return send(text)
  }

  return { open, busy, mode, suggestions, messages, dataVersion, loadStatus, send, confirm, cancel, ask }
})
