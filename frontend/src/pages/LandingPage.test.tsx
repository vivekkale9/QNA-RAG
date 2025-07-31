import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@/test/utils'
import { LandingPage } from './LandingPage'

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

describe('LandingPage', () => {
  it('renders landing page without crashing', () => {
    render(<LandingPage />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays main content', () => {
    render(<LandingPage />)
    
    // Look for common landing page elements
    const headings = screen.getAllByRole('heading')
    expect(headings.length).toBeGreaterThan(0)
  })

  it('has navigation links', () => {
    render(<LandingPage />)
    
    // Look for links
    const links = screen.getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
  })
}) 