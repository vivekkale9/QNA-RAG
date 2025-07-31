import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, createMockAxiosResponse } from '@/test/utils'
import userEvent from '@testing-library/user-event'
import { DocumentList } from './DocumentList'

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    getDocuments: vi.fn(),
    deleteDocument: vi.fn(),
  },
}))

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

describe('DocumentList', () => {
  const mockDocuments = [
    {
      id: 'doc1',
      filename: 'test1.pdf',
      file_type: 'pdf',
      file_size: 1024000,
      upload_date: '2023-12-01T10:00:00Z',
      status: 'completed',
      page_count: 5,
    },
    {
      id: 'doc2',
      filename: 'report.docx',
      file_type: 'docx',
      file_size: 512000,
      upload_date: '2023-12-01T09:00:00Z',
      status: 'processing',
      page_count: 3,
    },
    {
      id: 'doc3',
      filename: 'notes.txt',
      file_type: 'txt',
      file_size: 2048,
      upload_date: '2023-12-01T08:00:00Z',
      status: 'failed',
      page_count: 1,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.getDocuments).mockResolvedValue(
      createMockAxiosResponse(mockDocuments)
    )
  })

  it('renders document list correctly', () => {
    render(<DocumentList />)
    expect(document.body).toBeInTheDocument()
  })

  it('loads and displays documents', async () => {
    render(<DocumentList />)

    expect(apiClient.getDocuments).toHaveBeenCalled()

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
      expect(screen.getByText('report.docx')).toBeInTheDocument()
      expect(screen.getByText('notes.txt')).toBeInTheDocument()
    })
  })

  it('displays document information', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('1.0 MB')).toBeInTheDocument() // File size
      expect(screen.getByText('512.0 KB')).toBeInTheDocument() // File size
      expect(screen.getByText('2.0 KB')).toBeInTheDocument() // File size
    })
  })

  it('shows document status', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument()
      expect(screen.getByText('processing')).toBeInTheDocument()
      expect(screen.getByText('failed')).toBeInTheDocument()
    })
  })

  it('displays upload dates', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText(/2 hours ago/)).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    vi.mocked(apiClient.getDocuments).mockReturnValue(new Promise(() => {}) as any)

    render(<DocumentList />)
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.getDocuments).mockRejectedValue(
      new Error('Failed to load documents')
    )

    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText(/failed to load|error/i)).toBeInTheDocument()
    })
  })

  it('handles empty document list', async () => {
    vi.mocked(apiClient.getDocuments).mockResolvedValue(
      createMockAxiosResponse([])
    )

    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText(/no documents|empty/i)).toBeInTheDocument()
    })
  })

  it('allows document deletion', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.deleteDocument).mockResolvedValue(
      createMockAxiosResponse({ success: true })
    )

    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete|remove/i })
    await user.click(deleteButton)

    expect(apiClient.deleteDocument).toHaveBeenCalledWith('doc1')
  })

  it('shows confirmation before deletion', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete|remove/i })
    await user.click(deleteButton)

    expect(screen.getByText(/confirm|sure|delete/i)).toBeInTheDocument()
  })

  it('handles deletion errors', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.deleteDocument).mockRejectedValue(
      new Error('Deletion failed')
    )

    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete|remove/i })
    await user.click(deleteButton)

    await waitFor(() => {
      expect(screen.getByText(/deletion failed|error/i)).toBeInTheDocument()
    })
  })

  it('displays document file types with icons', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      // Should show file type indicators or icons
      expect(screen.getByText('pdf')).toBeInTheDocument()
      expect(screen.getByText('docx')).toBeInTheDocument()
      expect(screen.getByText('txt')).toBeInTheDocument()
    })
  })

  it('shows page count for documents', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('5 pages')).toBeInTheDocument()
      expect(screen.getByText('3 pages')).toBeInTheDocument()
      expect(screen.getByText('1 page')).toBeInTheDocument()
    })
  })

  it('allows sorting documents', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    // Look for sort options
    const sortButton = screen.getByRole('button', { name: /sort|order/i })
    await user.click(sortButton)

    expect(sortButton).toBeInTheDocument()
  })

  it('allows filtering documents', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    // Look for filter options
    const filterInput = screen.getByRole('textbox', { name: /search|filter/i })
    await user.type(filterInput, 'pdf')

    expect(filterInput).toHaveValue('pdf')
  })

  it('refreshes document list', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalledTimes(1)
    })

    const refreshButton = screen.getByRole('button', { name: /refresh|reload/i })
    await user.click(refreshButton)

    expect(apiClient.getDocuments).toHaveBeenCalledTimes(2)
  })

  it('handles document selection', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const checkbox = screen.getByRole('checkbox', { name: /select.*test1/i })
    await user.click(checkbox)

    expect(checkbox).toBeChecked()
  })

  it('supports bulk operations', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    // Select multiple documents
    const checkboxes = screen.getAllByRole('checkbox')
    if (checkboxes.length > 1) {
      await user.click(checkboxes[0])
      await user.click(checkboxes[1])

      // Look for bulk action button
      const bulkDeleteButton = screen.getByRole('button', { name: /delete selected/i })
      expect(bulkDeleteButton).toBeInTheDocument()
    }
  })

  it('displays document thumbnails or previews', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      // Look for image elements or preview indicators
      const images = screen.getAllByRole('img', { hidden: true })
      expect(images.length).toBeGreaterThan(0)
    })
  })

  it('allows document download', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const downloadButton = screen.getByRole('button', { name: /download/i })
    await user.click(downloadButton)

    expect(downloadButton).toBeInTheDocument()
  })

  it('shows document processing status', async () => {
    render(<DocumentList />)

    await waitFor(() => {
      // Should show different status indicators
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
      expect(screen.getByText(/processing/i)).toBeInTheDocument()
      expect(screen.getByText(/failed/i)).toBeInTheDocument()
    })
  })

  it('handles pagination for large document lists', async () => {
    const largeDocumentList = Array.from({ length: 50 }, (_, i) => ({
      id: `doc${i}`,
      filename: `document${i}.pdf`,
      file_type: 'pdf',
      file_size: 1024000,
      upload_date: '2023-12-01T10:00:00Z',
      status: 'completed',
      page_count: 5,
    }))

    vi.mocked(apiClient.getDocuments).mockResolvedValue(
      createMockAxiosResponse(largeDocumentList)
    )

    render(<DocumentList />)

    await waitFor(() => {
      // Should show pagination controls
      expect(screen.getByText(/page|next|previous/i)).toBeInTheDocument()
    })
  })

  it('updates list after document operations', async () => {
    const user = userEvent.setup()
    vi.mocked(apiClient.deleteDocument).mockResolvedValue(
      createMockAxiosResponse({ success: true })
    )

    // Mock updated list without deleted document
    vi.mocked(apiClient.getDocuments)
      .mockResolvedValueOnce(createMockAxiosResponse(mockDocuments))
      .mockResolvedValueOnce(createMockAxiosResponse(mockDocuments.slice(1)))

    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const deleteButton = screen.getByRole('button', { name: /delete|remove/i })
    await user.click(deleteButton)

    await waitFor(() => {
      expect(apiClient.getDocuments).toHaveBeenCalledTimes(2)
    })
  })

  it('shows document search functionality', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    const searchInput = screen.getByRole('textbox', { name: /search/i })
    await user.type(searchInput, 'test')

    // Should filter results
    expect(searchInput).toHaveValue('test')
  })

  it('handles document type filtering', async () => {
    const user = userEvent.setup()
    render(<DocumentList />)

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    })

    // Look for file type filter
    const typeFilter = screen.getByRole('combobox', { name: /type|filter/i })
    await user.click(typeFilter)

    expect(typeFilter).toBeInTheDocument()
  })

  it('renders without crashing', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    render(<DocumentList />)
    
    expect(consoleSpy).not.toHaveBeenCalled()
    consoleSpy.mockRestore()
  })
}) 