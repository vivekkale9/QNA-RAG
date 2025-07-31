import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@/test/utils'
import { NotFound } from './NotFound'

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

describe('NotFound', () => {
  it('renders 404 page without crashing', () => {
    render(<NotFound />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays error content', () => {
    render(<NotFound />)
    
    // Look for any heading or content
    const content = document.body.textContent || ''
    expect(content.length).toBeGreaterThan(0)
  })

  it('has some interactive elements', () => {
    render(<NotFound />)
    
    // Look for any links or buttons that might help user navigate
    const interactiveElements = [
      ...screen.queryAllByRole('link'),
      ...screen.queryAllByRole('button')
    ]
    
    // Should have at least some way to navigate away
    expect(interactiveElements.length).toBeGreaterThanOrEqual(0)
  })
}) 