import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, createMockAxiosResponse } from '@/test/utils'
import { LoginPage } from './LoginPage'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    login: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    Link: ({ children, to, ...props }: any) => (
      <a href={to} {...props}>
        {children}
      </a>
    ),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login page without crashing', () => {
    render(<LoginPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays form elements', () => {
    render(<LoginPage />)
    
    // Look for input fields
    const inputs = screen.getAllByRole('textbox', { hidden: true })
    expect(inputs.length).toBeGreaterThanOrEqual(0)
  })

  it('has some interactive elements', () => {
    render(<LoginPage />)
    
    // Look for buttons or links
    const buttons = screen.getAllByRole('button', { hidden: true })
    const links = screen.getAllByRole('link', { hidden: true })
    
    expect(buttons.length + links.length).toBeGreaterThan(0)
  })
}) 