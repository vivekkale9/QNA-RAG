import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { ProfilePage } from './ProfilePage'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getUserProfile: vi.fn(),
    updateUserProfile: vi.fn(),
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

import { apiClient } from '@/lib/api'

describe('ProfilePage', () => {
  const mockUserProfile = {
    id: 'user-123',
    email: 'test@example.com',
    role: 'user',
    created_at: '2023-12-01T00:00:00Z',
    document_count: 5,
    query_count: 25,
    llm_config: {
      provider: 'openai',
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 2000,
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(
      createMockAxiosResponse(mockUserProfile)
    )
  })

  it('renders profile page without crashing', () => {
    render(<ProfilePage />)
    expect(document.body).toBeInTheDocument()
  })

  it('loads and displays user profile data', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    expect(apiClient.getUserProfile).toHaveBeenCalled()
  })

  it('displays user statistics', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // document count
      expect(screen.getByText('25')).toBeInTheDocument() // query count
    })
  })

  it('allows editing profile information', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.updateUserProfile).mockResolvedValue(
      createMockAxiosResponse({ message: 'Profile updated successfully' })
    )

    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    expect(apiClient.updateUserProfile).toHaveBeenCalled()
  })

  it('handles profile update errors', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.updateUserProfile).mockRejectedValue(
      new Error('Update failed')
    )

    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/update failed/i)).toBeInTheDocument()
    })
  })

  it('displays profile settings', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    // Check for profile sections
    expect(screen.getByText(/profile/i)).toBeInTheDocument()
  })

  it('displays user statistics section', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('25')).toBeInTheDocument()
    })
  })

  it('has interactive elements', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    // Test that buttons exist and are clickable
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)

    if (buttons.length > 0) {
      await user.click(buttons[0])
      expect(buttons[0]).toBeInTheDocument()
    }
  })

  it('shows loading state initially', () => {
    vi.mocked(apiClient.getUserProfile).mockReturnValue(new Promise(() => {}) as any)

    render(<ProfilePage />)
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.getUserProfile).mockRejectedValue(
      new Error('Failed to load profile')
    )

    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })

  it('validates form inputs', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    // Clear email field
    const emailInput = screen.getByDisplayValue('test@example.com')
    await user.clear(emailInput)

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    })
  })

  it('renders form elements correctly', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    // Check that form has inputs
    const inputs = screen.getAllByRole('textbox')
    expect(inputs.length).toBeGreaterThan(0)

    // Check that form has buttons
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })
}) 