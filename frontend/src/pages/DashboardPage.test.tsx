import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, createMockAxiosResponse } from '@/test/utils'
import { DashboardPage } from './DashboardPage'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getDocuments: vi.fn(),
    getConversations: vi.fn(),
    getUserProfile: vi.fn(),
  },
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 hours ago'),
  format: vi.fn((date) => '2023-12-01 10:00 AM'),
}))

import { apiClient } from '@/lib/api'

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getDocuments).mockResolvedValue(createMockAxiosResponse([]))
    vi.mocked(apiClient.getConversations).mockResolvedValue(createMockAxiosResponse([]))
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(createMockAxiosResponse({
      id: 'user-123',
      email: 'test@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    }))
  })

  it('renders dashboard page without crashing', () => {
    render(<DashboardPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays some content', () => {
    render(<DashboardPage />)
    
    // Look for any content in the dashboard
    const content = document.body.textContent || ''
    expect(content.length).toBeGreaterThan(0)
  })

  it('makes API calls', () => {
    render(<DashboardPage />)
    
    // Verify that API calls are made
    expect(apiClient.getDocuments).toHaveBeenCalled()
    expect(apiClient.getConversations).toHaveBeenCalled()
    expect(apiClient.getUserProfile).toHaveBeenCalled()
  })
}) 