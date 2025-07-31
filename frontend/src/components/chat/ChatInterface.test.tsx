import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { ChatInterface } from './ChatInterface'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    sendMessage: vi.fn(),
    getConversation: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 minutes ago'),
}))

import { apiClient } from '@/lib/api'

describe('ChatInterface', () => {
  const mockOnConversationCreated = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chat interface with input and send button', () => {
    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    expect(screen.getByPlaceholderText(/ask a question about your documents/i)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
    expect(screen.getByText(/ai assistant/i)).toBeInTheDocument()
  })

  it('enables send button when input has text', async () => {
    const user = userEvent.setup()
    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    expect(sendButton).toBeDisabled()
    
    await user.type(input, 'What is this document about?')
    expect(sendButton).toBeEnabled()
  })

  it('sends message and displays response', async () => {
    const user = userEvent.setup()
    const mockResponse = createMockAxiosResponse({
      message_id: 'msg-123',
      message: 'This document is about testing.',
      conversation_id: 'conv-123',
      sources: [
        {
          document_id: 'doc-123',
          document_name: 'test.pdf',
          chunk_id: 'chunk-123',
          content: 'Test content',
          similarity_score: 0.95,
          page_number: 1,
        },
      ],
      model_used: 'gpt-3.5-turbo',
    })

    vi.mocked(apiClient.sendMessage).mockResolvedValue(mockResponse)

    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    await user.type(input, 'What is this document about?')
    await user.click(sendButton)
    
    // Check that user message is displayed
    expect(screen.getByText('What is this document about?')).toBeInTheDocument()
    
    // Wait for AI response
    await waitFor(() => {
      expect(screen.getByText('This document is about testing.')).toBeInTheDocument()
    })
    
    // Check that sources are displayed
    expect(screen.getByText(/test\.pdf.*Score: 0\.95/)).toBeInTheDocument()
    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('shows loading state while processing message', async () => {
    const user = userEvent.setup()
    let resolvePromise: (value: any) => void
    const pendingPromise = new Promise<any>((resolve) => {
      resolvePromise = resolve
    })

    vi.mocked(apiClient.sendMessage).mockReturnValue(pendingPromise as any)

    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    await user.type(input, 'Test message')
    await user.click(sendButton)
    
    // Check loading state
    expect(screen.getByText(/analyzing documents and generating response/i)).toBeInTheDocument()
    expect(sendButton).toBeDisabled()
    
    // Resolve the promise
    resolvePromise!(createMockAxiosResponse({
      message_id: 'msg-123',
      message: 'Response',
      conversation_id: 'conv-123',
      sources: [],
      model_used: 'gpt-3.5-turbo',
    }))
    
    await waitFor(() => {
      expect(screen.queryByText(/analyzing documents and generating response/i)).not.toBeInTheDocument()
    })
  })

  it('loads conversation history when conversationId is provided', async () => {
    const mockConversation = createMockAxiosResponse({
      id: 'conv-123',
      title: 'Test Conversation',
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Previous question',
          timestamp: new Date().toISOString(),
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Previous answer',
          sources: [],
          timestamp: new Date().toISOString(),
        },
      ],
    })

    vi.mocked(apiClient.getConversation).mockResolvedValue(mockConversation)

    render(
      <ChatInterface 
        conversationId="conv-123"
        onConversationCreated={mockOnConversationCreated} 
      />
    )
    
    await waitFor(() => {
      expect(screen.getByText('Previous question')).toBeInTheDocument()
      expect(screen.getByText('Previous answer')).toBeInTheDocument()
    })
  })

  it('calls onConversationCreated for new conversations', async () => {
    const user = userEvent.setup()
    const mockResponse = createMockAxiosResponse({
      message_id: 'msg-123',
      message: 'Response',
      conversation_id: 'conv-new-123',
      sources: [],
      model_used: 'gpt-3.5-turbo',
    })

    vi.mocked(apiClient.sendMessage).mockResolvedValue(mockResponse)

    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    await user.type(input, 'First message')
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(mockOnConversationCreated).toHaveBeenCalledWith('conv-new-123')
    })
  })

  it('handles send message with Enter key', async () => {
    const user = userEvent.setup()
    const mockResponse = createMockAxiosResponse({
      message_id: 'msg-123',
      message: 'Response',
      conversation_id: 'conv-123',
      sources: [],
      model_used: 'gpt-3.5-turbo',
    })

    vi.mocked(apiClient.sendMessage).mockResolvedValue(mockResponse)

    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    
    await user.type(input, 'Test message')
    await user.keyboard('{Enter}')
    
    expect(vi.mocked(apiClient.sendMessage)).toHaveBeenCalledWith({
      message: 'Test message',
      conversation_id: undefined,
      max_chunks: 5,
    })
  })

  it('prevents sending empty messages', async () => {
    const user = userEvent.setup()
    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    await user.type(input, '   ')  // Only whitespace
    expect(sendButton).toBeDisabled()
    
    await user.clear(input)
    await user.keyboard('{Enter}')  // Try to send empty message
    
    expect(vi.mocked(apiClient.sendMessage)).not.toHaveBeenCalled()
  })

  it('displays sources in the sources panel', async () => {
    const user = userEvent.setup()
    const mockResponse = createMockAxiosResponse({
      message_id: 'msg-123',
      message: 'Response with sources',
      conversation_id: 'conv-123',
      sources: [
        {
          document_id: 'doc-123',
          document_name: 'document1.pdf',
          chunk_id: 'chunk-123',
          content: 'Source content 1',
          similarity_score: 0.95,
          page_number: 1,
        },
        {
          document_id: 'doc-456',
          document_name: 'document2.pdf',
          chunk_id: 'chunk-456',
          content: 'Source content 2',
          similarity_score: 0.88,
          page_number: 2,
        },
      ],
      model_used: 'gpt-3.5-turbo',
    })

    vi.mocked(apiClient.sendMessage).mockResolvedValue(mockResponse)

    render(<ChatInterface onConversationCreated={mockOnConversationCreated} />)
    
    const input = screen.getByPlaceholderText(/ask a question about your documents/i)
    const sendButton = screen.getByRole('button')
    
    await user.type(input, 'Show me sources')
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText(/document1\.pdf.*Score: 0\.95/)).toBeInTheDocument()
      expect(screen.getByText(/document2\.pdf.*Score: 0\.88/)).toBeInTheDocument()
      expect(screen.getByText('Source content 1')).toBeInTheDocument()
      expect(screen.getByText('Source content 2')).toBeInTheDocument()
    })
  })
}) 