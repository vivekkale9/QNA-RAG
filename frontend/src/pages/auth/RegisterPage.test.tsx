import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { RegisterPage } from './RegisterPage'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    register: vi.fn(),
  },
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    Link: ({ children, to, ...props }: any) => (
      <a href={to} {...props}>
        {children}
      </a>
    ),
  }
})

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

import { apiClient } from '@/lib/api'

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders register page without crashing', () => {
    render(<RegisterPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays registration form', () => {
    render(<RegisterPage />)
    
    expect(screen.getByRole('heading')).toBeInTheDocument()
  })

  it('has email and password inputs', () => {
    render(<RegisterPage />)
    
    // Check for form inputs
    const inputs = screen.getAllByRole('textbox')
    expect(inputs.length).toBeGreaterThan(0)
  })

  it('has a register button', () => {
    render(<RegisterPage />)
    
    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    expect(registerButton).toBeInTheDocument()
  })

  it('handles successful registration', async () => {
    const user = userEvent.setup()
    const mockRegisterResponse = createMockAxiosResponse({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 'user-123',
        email: 'test@example.com',
        role: 'user',
      },
    })

    vi.mocked(apiClient.register).mockResolvedValue(mockRegisterResponse)

    render(<RegisterPage />)

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(apiClient.register).toHaveBeenCalled()
    })
  })

  it('handles registration errors', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.register).mockRejectedValue(
      new Error('Registration failed')
    )

    render(<RegisterPage />)

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByText(/registration failed/i)).toBeInTheDocument()
    })
  })

  it('shows loading state during registration', async () => {
    const user = userEvent.setup()
    let resolveRegister: (value: any) => void
    const registerPromise = new Promise((resolve) => {
      resolveRegister = resolve
    })

    vi.mocked(apiClient.register).mockReturnValue(registerPromise as any)

    render(<RegisterPage />)

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    // Should show loading state
    expect(registerButton).toBeDisabled()

    // Resolve the promise
    resolveRegister!(createMockAxiosResponse({ access_token: 'token' }))
  })

  it('validates form inputs', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    // Should show validation errors for empty form
    await waitFor(() => {
      expect(screen.getByText(/required/i)).toBeInTheDocument()
    })
  })

  it('validates email format', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    // Try to enter invalid email
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    await user.type(emailInput, 'invalid-email')

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument()
    })
  })

  it('validates password strength', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    // Try to enter weak password
    const passwordInput = screen.getByLabelText(/password/i)
    await user.type(passwordInput, '123')

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByText(/password.*strong/i)).toBeInTheDocument()
    })
  })

  it('confirms password match', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    // Enter different passwords
    const passwordInput = screen.getByLabelText(/^password/i)
    const confirmInput = screen.getByLabelText(/confirm/i)
    
    await user.type(passwordInput, 'password123')
    await user.type(confirmInput, 'different123')

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByText(/passwords.*match/i)).toBeInTheDocument()
    })
  })

  it('navigates to login page', () => {
    render(<RegisterPage />)
    
    const loginLink = screen.getByRole('link', { name: /sign in|login/i })
    expect(loginLink).toHaveAttribute('href', '/auth/login')
  })

  it('handles keyboard navigation', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)
    
    // Test tab navigation through form
    await user.tab()
    expect(document.activeElement).toBeTruthy()
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    const toggleButton = screen.getByRole('button', { name: /toggle.*password/i })
    const passwordInput = screen.getByLabelText(/^password/i) as HTMLInputElement

    // Initially password should be hidden
    expect(passwordInput.type).toBe('password')

    // Click to show password
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('text')

    // Click to hide password again
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('password')
  })

  it('accepts terms and conditions', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    const termsCheckbox = screen.getByRole('checkbox', { name: /terms/i })
    expect(termsCheckbox).not.toBeChecked()

    await user.click(termsCheckbox)
    expect(termsCheckbox).toBeChecked()
  })

  it('prevents registration without accepting terms', async () => {
    const user = userEvent.setup()
    render(<RegisterPage />)

    // Fill form but don't check terms
    const emailInput = screen.getByRole('textbox', { name: /email/i })
    await user.type(emailInput, 'test@example.com')

    const registerButton = screen.getByRole('button', { name: /register|sign up/i })
    await user.click(registerButton)

    await waitFor(() => {
      expect(screen.getByText(/accept.*terms/i)).toBeInTheDocument()
    })
  })

  it('displays privacy policy link', () => {
    render(<RegisterPage />)
    
    const privacyLink = screen.getByRole('link', { name: /privacy/i })
    expect(privacyLink).toBeInTheDocument()
  })
}) 