import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useIsMobile } from './use-mobile'

const mockMatchMedia = vi.fn()

describe('useIsMobile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: mockMatchMedia,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should return true when screen is mobile size', () => {
    const mockAddEventListener = vi.fn()
    const mockRemoveEventListener = vi.fn()
    
    mockMatchMedia.mockReturnValue({
      matches: true,
      addEventListener: mockAddEventListener,
      removeEventListener: mockRemoveEventListener,
    })

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(true)
    expect(mockMatchMedia).toHaveBeenCalledWith('(max-width: 767px)')
    expect(mockAddEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('should return false when screen is desktop size', () => {
    const mockAddEventListener = vi.fn()
    const mockRemoveEventListener = vi.fn()
    
    mockMatchMedia.mockReturnValue({
      matches: false,
      addEventListener: mockAddEventListener,
      removeEventListener: mockRemoveEventListener,
    })

    const { result } = renderHook(() => useIsMobile())

    expect(result.current).toBe(false)
    expect(mockMatchMedia).toHaveBeenCalledWith('(max-width: 767px)')
  })

  it('should cleanup event listener on unmount', () => {
    const mockAddEventListener = vi.fn()
    const mockRemoveEventListener = vi.fn()
    
    mockMatchMedia.mockReturnValue({
      matches: false,
      addEventListener: mockAddEventListener,
      removeEventListener: mockRemoveEventListener,
    })

    const { unmount } = renderHook(() => useIsMobile())
    
    unmount()

    expect(mockRemoveEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })
}) 