'use client'

import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import Link from 'next/link'
import { ArrowLeft, Send, CheckCircle, XCircle } from 'lucide-react'
import { chatApi, ChatMessage, ChatResponse } from '@/lib/api'

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<ChatResponse['pending_action'] | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: async (content: string) => {
      return chatApi.send(content, sessionId || undefined)
    },
    onSuccess: (response) => {
      // Update session ID
      if (!sessionId) {
        setSessionId(response.session_id)
      }

      // Add assistant message
      setMessages((prev) => [...prev, response.message])

      // Handle pending action
      if (response.requires_confirmation && response.pending_action) {
        setPendingAction(response.pending_action)
      }
    },
  })

  // Confirm action mutation
  const confirmMutation = useMutation({
    mutationFn: async ({ confirmed }: { confirmed: boolean }) => {
      if (!sessionId || !pendingAction) return
      return chatApi.confirm(sessionId, pendingAction.action_id, confirmed)
    },
    onSuccess: (response, variables) => {
      setPendingAction(null)

      // Add confirmation result message
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant' as const,
          content: variables.confirmed
            ? 'Actie uitgevoerd.'
            : 'Actie geannuleerd.',
          created_at: new Date().toISOString(),
        },
      ])
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || sendMutation.isPending) return

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])

    // Send to API
    sendMutation.mutate(input)
    setInput('')
  }

  const handleConfirm = (confirmed: boolean) => {
    confirmMutation.mutate({ confirmed })
  }

  // Example prompts
  const examplePrompts = [
    'Hoeveel omzet hebben we gepland voor Q1?',
    'Kan Nienke volgende week dinsdag?',
    'Welke workshops zitten nog niet vol?',
    'Plan een BWS in voor maart in Utrecht',
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center">
            <Link href="/" className="mr-4 text-gray-500 hover:text-gray-700">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI Assistent</h1>
              <p className="text-sm text-gray-500">
                Stel vragen of geef opdrachten in natuurlijke taal
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Chat container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 lg:px-8 flex flex-col">
        {/* Messages */}
        <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Hoe kan ik je helpen?
                </h3>
                <p className="text-gray-500 mb-6">
                  Stel een vraag of kies een voorbeeld
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg mx-auto">
                  {examplePrompts.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(prompt)}
                      className="text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 text-sm text-gray-700"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'ml-auto bg-primary-500 text-white'
                      : 'mr-auto bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs mt-2 opacity-70">
                    {new Date(message.created_at).toLocaleTimeString('nl-NL', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              ))
            )}

            {/* Loading indicator */}
            {sendMutation.isPending && (
              <div className="mr-auto bg-gray-100 rounded-lg p-4">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            )}

            {/* Pending action confirmation */}
            {pendingAction && (
              <div className="mr-auto bg-amber-50 border border-amber-200 rounded-lg p-4 max-w-[80%]">
                <p className="font-medium text-amber-800 mb-2">
                  Bevestiging vereist
                </p>
                <p className="text-amber-700 mb-4">{pendingAction.description}</p>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleConfirm(true)}
                    disabled={confirmMutation.isPending}
                    className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4 mr-1" />
                    Ja, uitvoeren
                  </button>
                  <button
                    onClick={() => handleConfirm(false)}
                    disabled={confirmMutation.isPending}
                    className="inline-flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    <XCircle className="h-4 w-4 mr-1" />
                    Nee, annuleren
                  </button>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t p-4">
            <div className="flex space-x-4">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Typ een bericht..."
                disabled={sendMutation.isPending}
                className="flex-1 rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 disabled:bg-gray-100"
              />
              <button
                type="submit"
                disabled={!input.trim() || sendMutation.isPending}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}
