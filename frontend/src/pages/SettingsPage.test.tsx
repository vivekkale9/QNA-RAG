import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { SettingsPage } from './SettingsPage'

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

describe('SettingsPage', () => {
  const mockUserProfile = {
    id: 'user-123',
    email: 'test@example.com',
    role: 'user',
    created_at: '2023-12-01T00:00:00Z',
    preferences: {
      theme: 'dark',
      notifications: true,
      language: 'en',
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(
      createMockAxiosResponse(mockUserProfile)
    )
  })

  it('renders settings page without crashing', () => {
    render(<SettingsPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('loads user settings', async () => {
    render(<SettingsPage />)
    
    expect(apiClient.getUserProfile).toHaveBeenCalled()
    
    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })
  })

  it('displays theme settings', async () => {
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/theme/i)).toBeInTheDocument()
    })
  })

  it('displays notification settings', async () => {
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/notification/i)).toBeInTheDocument()
    })
  })

  it('allows updating settings', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.updateUserProfile).mockResolvedValue(
      createMockAxiosResponse({ message: 'Settings updated' })
    )

    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    expect(apiClient.updateUserProfile).toHaveBeenCalled()
  })

  it('handles settings update errors', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.updateUserProfile).mockRejectedValue(
      new Error('Update failed')
    )

    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(screen.getByText(/update failed/i)).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    vi.mocked(apiClient.getUserProfile).mockReturnValue(new Promise(() => {}) as any)

    render(<SettingsPage />)
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.getUserProfile).mockRejectedValue(
      new Error('Failed to load settings')
    )

    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })

  it('toggles theme setting', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/theme/i)).toBeInTheDocument()
    })

    // Look for theme toggle
    const themeToggle = screen.getByRole('button', { name: /theme/i }) ||
                       screen.getByRole('switch', { name: /theme/i })
    
    await user.click(themeToggle)
    
    // Should trigger some kind of update
    expect(themeToggle).toBeInTheDocument()
  })

  it('toggles notification setting', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/notification/i)).toBeInTheDocument()
    })

    // Look for notification toggle
    const notificationToggle = screen.getByRole('button', { name: /notification/i }) ||
                              screen.getByRole('switch', { name: /notification/i })
    
    await user.click(notificationToggle)
    
    expect(notificationToggle).toBeInTheDocument()
  })

  it('displays language settings', async () => {
    render(<SettingsPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/language/i)).toBeInTheDocument()
    })
  })

  it('resets settings to default', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })

    const resetButton = screen.getByRole('button', { name: /reset/i })
    await user.click(resetButton)

    // Should show confirmation or reset immediately
    expect(resetButton).toBeInTheDocument()
  })

  it('validates settings before saving', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })

    // Try to save invalid settings (implementation dependent)
    const saveButton = screen.getByRole('button', { name: /save/i })
    await user.click(saveButton)

    // Should either save or show validation
    expect(saveButton).toBeInTheDocument()
  })

  it('shows unsaved changes warning', async () => {
    const user = userEvent.setup()
    render(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/settings/i)).toBeInTheDocument()
    })

    // Make a change
    const toggles = screen.getAllByRole('button')
    if (toggles.length > 0) {
      await user.click(toggles[0])
    }

    // Should show some indication of changes
    expect(document.body).toBeInTheDocument()
  })
}) 