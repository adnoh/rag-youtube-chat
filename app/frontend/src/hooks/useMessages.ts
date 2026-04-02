import { useState, useEffect } from 'react'
import { getConversation, type Message } from '../lib/api'

export function useMessages(conversationId: string | null) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      return
    }
    setLoading(true)
    setError(null)
    getConversation(conversationId)
      .then((data) => setMessages(data.messages))
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load messages'))
      .finally(() => setLoading(false))
  }, [conversationId])

  return { messages, setMessages, loading, error }
}
