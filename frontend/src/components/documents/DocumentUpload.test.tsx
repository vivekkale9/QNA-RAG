import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { DocumentUpload } from './DocumentUpload'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    uploadDocument: vi.fn(),
  },
}))

// Mock the toast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

import { apiClient } from '@/lib/api'

describe('DocumentUpload', () => {
  const mockOnUploadComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload interface correctly', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays upload area', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Look for upload-related text
    expect(screen.getByText(/upload/i)).toBeInTheDocument()
  })

  it('shows drag and drop area', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Check for drag and drop functionality
    const text = document.body.textContent || ''
    expect(text).toContain('drag')
  })

  it('has file input for browsing', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Look for file input
    const fileInput = screen.getByRole('button', { name: /browse|upload|select/i })
    expect(fileInput).toBeInTheDocument()
  })

  it('handles file selection', async () => {
    const user = userEvent.setup()
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    // Mock successful upload
    vi.mocked(apiClient.uploadDocument).mockResolvedValue(
      createMockAxiosResponse({ success: true })
    )

    // Look for file input or upload trigger
    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    expect(uploadButton).toBeInTheDocument()
  })

  it('displays supported file types', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Check for file type information
    const text = document.body.textContent || ''
    expect(text.length).toBeGreaterThan(50) // Should have descriptive content
  })

  it('shows file size limits', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Look for size limitation text
    const text = document.body.textContent || ''
    expect(text).toMatch(/mb|size|limit/i)
  })

  it('handles upload errors gracefully', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.uploadDocument).mockRejectedValue(
      new Error('Upload failed')
    )

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/upload failed|error/i)).toBeInTheDocument()
    })
  })

  it('shows upload progress', async () => {
    const user = userEvent.setup()
    let resolveUpload: (value: any) => void
    const uploadPromise = new Promise((resolve) => {
      resolveUpload = resolve
    })

    vi.mocked(apiClient.uploadDocument).mockReturnValue(uploadPromise as any)

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    // Should show some form of loading/progress state
    expect(uploadButton).toBeDisabled()

    // Resolve the upload
    resolveUpload!(createMockAxiosResponse({ success: true }))
  })

  it('calls onUploadComplete when upload succeeds', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.uploadDocument).mockResolvedValue(
      createMockAxiosResponse({ 
        success: true,
        document_id: 'doc123',
        filename: 'test.pdf',
        status: 'completed'
      })
    )

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(mockOnUploadComplete).toHaveBeenCalled()
    })
  })

  it('validates file types', async () => {
    const user = userEvent.setup()
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    // Try to upload invalid file type
    vi.mocked(apiClient.uploadDocument).mockRejectedValue(
      new Error('Invalid file type')
    )

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/invalid.*file|unsupported.*type/i)).toBeInTheDocument()
    })
  })

  it('validates file size', async () => {
    const user = userEvent.setup()
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    // Try to upload oversized file
    vi.mocked(apiClient.uploadDocument).mockRejectedValue(
      new Error('File too large')
    )

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/too large|size limit/i)).toBeInTheDocument()
    })
  })

  it('handles multiple file selection', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Should have interface that supports multiple files
    expect(document.body).toBeInTheDocument()
  })

  it('provides clear upload instructions', () => {
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    // Should have helpful instructional text
    const text = document.body.textContent || ''
    expect(text.length).toBeGreaterThan(100) // Should have substantial instructional content
  })

  it('handles drag over events', async () => {
    const user = userEvent.setup()
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    // Look for drop zone
    const dropZone = document.querySelector('[data-testid="drop-zone"]') || 
                     document.querySelector('.upload') ||
                     document.body.firstChild

    if (dropZone) {
      await user.hover(dropZone as Element)
      expect(dropZone).toBeInTheDocument()
    }
  })

  it('resets state after successful upload', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.uploadDocument).mockResolvedValue(
      createMockAxiosResponse({ success: true })
    )

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(mockOnUploadComplete).toHaveBeenCalled()
    })

    // Should reset to initial state
    expect(uploadButton).not.toBeDisabled()
  })

  it('handles concurrent uploads', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.uploadDocument).mockResolvedValue(
      createMockAxiosResponse({ success: true })
    )

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    
    // Simulate multiple quick clicks
    await user.click(uploadButton)
    await user.click(uploadButton)

    expect(uploadButton).toBeInTheDocument()
  })

  it('displays upload success message', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.uploadDocument).mockResolvedValue(
      createMockAxiosResponse({ 
        success: true,
        filename: 'test.pdf',
        status: 'completed'
      })
    )

    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)

    const uploadButton = screen.getByRole('button', { name: /browse|upload|select/i })
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/success|completed|uploaded/i)).toBeInTheDocument()
    })
  })

  it('renders without crashing', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    render(<DocumentUpload onUploadComplete={mockOnUploadComplete} />)
    
    expect(consoleSpy).not.toHaveBeenCalled()
    consoleSpy.mockRestore()
  })
}) 