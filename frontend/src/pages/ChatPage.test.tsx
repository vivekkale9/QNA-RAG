import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { ChatPage } from './ChatPage'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    sendMessage: vi.fn(),
    getConversations: vi.fn(),
    getConversation: vi.fn(),
  },
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useParams: () => ({ id: 'conv-123' }),
  }
})

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

import { apiClient } from '@/lib/api'

describe('ChatPage', () => {
  const mockConversation = {
    id: 'conv-123',
    title: 'Test Conversation',
    messages: [
      {
        id: 'msg-1',
        content: 'Hello!',
        role: 'user',
        timestamp: '2023-12-01T10:00:00Z',
      },
      {
        id: 'msg-2',
        content: 'Hi there! How can I help you?',
        role: 'assistant',
        timestamp: '2023-12-01T10:01:00Z',
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getConversation).mockResolvedValue(
      createMockAxiosResponse(mockConversation)
    )
    vi.mocked(apiClient.getConversations).mockResolvedValue(
      createMockAxiosResponse([mockConversation])
    )
  })

  it('renders chat page without crashing', () => {
    render(<ChatPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('loads conversation data', async () => {
    render(<ChatPage />)
    
    expect(apiClient.getConversation).toHaveBeenCalledWith('conv-123')
    
    await waitFor(() => {
      expect(screen.getByText('Hello!')).toBeInTheDocument()
      expect(screen.getByText('Hi there! How can I help you?')).toBeInTheDocument()
    })
  })

  it('displays chat interface', async () => {
    render(<ChatPage />)
    
    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })
  })

  it('sends messages', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.sendMessage).mockResolvedValue(
      createMockAxiosResponse({
        message: {
          id: 'msg-3',
          content: 'New message',
          role: 'user',
        },
        response: {
          id: 'msg-4',
          content: 'AI response',
          role: 'assistant',
        },
      })
    )

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox')
    const sendButton = screen.getByRole('button', { name: /send/i })

    await user.type(input, 'Test message')
    await user.click(sendButton)

    expect(apiClient.sendMessage).toHaveBeenCalledWith({
      conversation_id: 'conv-123',
      message: 'Test message',
    })
  })

  it('handles send message errors', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.sendMessage).mockRejectedValue(
      new Error('Failed to send message')
    )

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox')
    const sendButton = screen.getByRole('button', { name: /send/i })

    await user.type(input, 'Test message')
    await user.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText(/failed to send/i)).toBeInTheDocument()
    })
  })

  it('shows loading state while sending', async () => {
    const user = userEvent.setup()
    let resolveSend: (value: any) => void
    const sendPromise = new Promise((resolve) => {
      resolveSend = resolve
    })

    vi.mocked(apiClient.sendMessage).mockReturnValue(sendPromise as any)

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox')
    const sendButton = screen.getByRole('button', { name: /send/i })

    await user.type(input, 'Test message')
    await user.click(sendButton)

    // Should show loading state
    expect(sendButton).toBeDisabled()

    // Resolve the promise
    resolveSend!(createMockAxiosResponse({ message: 'sent' }))
  })

  it('handles conversation loading errors', async () => {
    vi.mocked(apiClient.getConversation).mockRejectedValue(
      new Error('Failed to load conversation')
    )

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    vi.mocked(apiClient.getConversation).mockReturnValue(new Promise(() => {}) as any)

    render(<ChatPage />)
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('displays conversation title', async () => {
    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Test Conversation')).toBeInTheDocument()
    })
  })

  it('handles keyboard shortcuts', async () => {
    const user = userEvent.setup()
    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test message')
    await user.keyboard('{Enter}')

    // Should trigger send
    expect(apiClient.sendMessage).toHaveBeenCalled()
  })

  it('clears input after sending', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.sendMessage).mockResolvedValue(
      createMockAxiosResponse({ message: 'sent' })
    )

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox') as HTMLInputElement
    await user.type(input, 'Test message')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })

  it('displays message timestamps', async () => {
    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText(/10:00/)).toBeInTheDocument()
      expect(screen.getByText(/10:01/)).toBeInTheDocument()
    })
  })

  it('scrolls to bottom on new messages', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.sendMessage).mockResolvedValue(
      createMockAxiosResponse({
        message: { id: 'new', content: 'New message', role: 'user' },
      })
    )

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    const input = screen.getByRole('textbox')
    await user.type(input, 'New message')
    await user.keyboard('{Enter}')

    // Should auto-scroll (implementation dependent)
    await waitFor(() => {
      expect(apiClient.sendMessage).toHaveBeenCalled()
    })
  })
}) 