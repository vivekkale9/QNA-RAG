import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from './AuthContext'
import React from 'react'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    login: vi.fn(),
    register: vi.fn(),
    getUserProfile: vi.fn(),
    logout: vi.fn(),
  },
}))

import { apiClient } from '@/lib/api'

// Test component that uses the auth context
const TestComponent = () => {
  const { user, login, register, logout, isLoading, isAuthenticated } = useAuth()
  
  return (
    <div>
      <div data-testid="auth-state">
        {isLoading && <span>Loading...</span>}
        {isAuthenticated && user && <span>Logged in as {user.email}</span>}
        {!isAuthenticated && !isLoading && <span>Not logged in</span>}
      </div>
      
      <button
        onClick={() => login('test@example.com', 'password123')}
        data-testid="login-btn"
      >
        Login
      </button>
      
      <button
        onClick={() => register('new@example.com', 'password123')}
        data-testid="register-btn"
      >
        Register
      </button>
      
      <button
        onClick={logout}
        data-testid="logout-btn"
      >
        Logout
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('provides initial unauthenticated state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    expect(screen.getByText('Not logged in')).toBeInTheDocument()
    expect(screen.getByTestId('login-btn')).toBeInTheDocument()
    expect(screen.getByTestId('register-btn')).toBeInTheDocument()
  })

  it('handles successful login', async () => {
    const user = userEvent.setup()
    const mockLoginResponse = createMockAxiosResponse({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
    })

    const mockProfileResponse = createMockAxiosResponse({
      id: 'user-123',
      email: 'test@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    })

    vi.mocked(apiClient.login).mockResolvedValue(mockLoginResponse)
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(mockProfileResponse)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    const loginBtn = screen.getByTestId('login-btn')
    await user.click(loginBtn)
    
    await waitFor(() => {
      expect(screen.getByText('Logged in as test@example.com')).toBeInTheDocument()
    })
    
    expect(vi.mocked(apiClient.login)).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
    })
    expect(vi.mocked(apiClient.getUserProfile)).toHaveBeenCalled()
  })

  it('handles successful registration', async () => {
    const user = userEvent.setup()
    const mockRegisterResponse = createMockAxiosResponse({
      id: 'user-456',
      email: 'new@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    })

    const mockLoginResponse = createMockAxiosResponse({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
    })

    const mockProfileResponse = createMockAxiosResponse({
      id: 'user-456',
      email: 'new@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    })

    vi.mocked(apiClient.register).mockResolvedValue(mockRegisterResponse)
    vi.mocked(apiClient.login).mockResolvedValue(mockLoginResponse)
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(mockProfileResponse)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    const registerBtn = screen.getByTestId('register-btn')
    await user.click(registerBtn)
    
    await waitFor(() => {
      expect(screen.getByText('Logged in as new@example.com')).toBeInTheDocument()
    })
    
    expect(vi.mocked(apiClient.register)).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'password123',
      role: 'user',
    })
  })

  it('handles logout', async () => {
    const user = userEvent.setup()
    const mockLoginResponse = createMockAxiosResponse({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
    })

    const mockProfileResponse = createMockAxiosResponse({
      id: 'user-123',
      email: 'test@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    })

    vi.mocked(apiClient.login).mockResolvedValue(mockLoginResponse)
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(mockProfileResponse)
    vi.mocked(apiClient.logout).mockReturnValue(undefined)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    // First login
    const loginBtn = screen.getByTestId('login-btn')
    await user.click(loginBtn)
    
    await waitFor(() => {
      expect(screen.getByText('Logged in as test@example.com')).toBeInTheDocument()
    })
    
    // Then logout
    const logoutBtn = screen.getByTestId('logout-btn')
    await user.click(logoutBtn)
    
    await waitFor(() => {
      expect(screen.getByText('Not logged in')).toBeInTheDocument()
    })
    
    expect(vi.mocked(apiClient.logout)).toHaveBeenCalled()
  })

  it('persists token in localStorage on login', async () => {
    const user = userEvent.setup()
    const mockLoginResponse = createMockAxiosResponse({
      access_token: 'mock-token-123',
      refresh_token: 'mock-refresh-token-123',
      token_type: 'bearer',
    })

    const mockProfileResponse = createMockAxiosResponse({
      id: 'user-123',
      email: 'test@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 0,
      query_count: 0,
    })

    vi.mocked(apiClient.login).mockResolvedValue(mockLoginResponse)
    vi.mocked(apiClient.getUserProfile).mockResolvedValue(mockProfileResponse)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    const loginBtn = screen.getByTestId('login-btn')
    await user.click(loginBtn)
    
    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe('mock-token-123')
      expect(localStorage.getItem('refresh_token')).toBe('mock-refresh-token-123')
    })
  })

  it('loads user from stored token on mount', async () => {
    localStorage.setItem('access_token', 'stored-token')
    
    const mockUser = createMockAxiosResponse({
      id: 'user-123',
      email: 'stored@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 5,
      query_count: 10,
    })

    vi.mocked(apiClient.getUserProfile).mockResolvedValue(mockUser)

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    // Should show loading initially
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    
    // Then should load the user
    await waitFor(() => {
      expect(screen.getByText('Logged in as stored@example.com')).toBeInTheDocument()
    })
    
    expect(vi.mocked(apiClient.getUserProfile)).toHaveBeenCalled()
  })

  it('handles invalid stored token', async () => {
    localStorage.setItem('access_token', 'invalid-token')
    
    vi.mocked(apiClient.getUserProfile).mockRejectedValue(new Error('Unauthorized'))

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )
    
    // Should show loading initially
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    
    // Then should show not logged in and clear storage
    await waitFor(() => {
      expect(screen.getByText('Not logged in')).toBeInTheDocument()
    })
    
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('throws error when useAuth is used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    const TestComponentOutsideProvider = () => {
      useAuth()
      return <div>Test</div>
    }
    
    expect(() => {
      render(<TestComponentOutsideProvider />)
    }).toThrow('useAuth must be used within an AuthProvider')
    
    consoleSpy.mockRestore()
  })
}) 