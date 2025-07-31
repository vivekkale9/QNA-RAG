import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { apiClient } from './api'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock window.location
const mockLocation = {
  href: 'http://localhost:3000',
  pathname: '/dashboard',
}
Object.defineProperty(window, 'location', { value: mockLocation })

describe('ApiClient', () => {
  let mockAxios: MockAdapter

  beforeEach(() => {
    vi.clearAllMocks()
    mockAxios = new MockAdapter((apiClient as any).client)
    localStorageMock.getItem.mockReturnValue(null)
  })

  afterEach(() => {
    mockAxios.restore()
  })

  describe('Authentication Methods', () => {
    it('should register a new user successfully', async () => {
      const userData = {
        access_token: 'token123',
        refresh_token: 'refresh123',
        user: {
          id: 'user1',
          email: 'test@example.com',
          role: 'user',
        },
      }

      mockAxios.onPost('/rag/auth/register').reply(200, userData)

      const result = await apiClient.register({
        email: 'test@example.com',
        password: 'password123',
      })

      expect(result.data).toEqual(userData)
      expect(mockAxios.history.post[0].data).toContain('test@example.com')
      expect(mockAxios.history.post[0].data).toContain('password123')
      expect(mockAxios.history.post[0].data).toContain('user') // default role
    })

    it('should register user with custom role', async () => {
      mockAxios.onPost('/rag/auth/register').reply(200, {})

      await apiClient.register({
        email: 'admin@example.com',
        password: 'password123',
        role: 'admin',
      })

      expect(mockAxios.history.post[0].data).toContain('admin')
    })

    it('should login user successfully', async () => {
      const loginData = {
        access_token: 'token123',
        refresh_token: 'refresh123',
      }

      mockAxios.onPost('/rag/auth/login').reply(200, loginData)

      const result = await apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      })

      expect(result.data).toEqual(loginData)
      // Check that form data was sent
      expect(mockAxios.history.post[0].headers?.['Content-Type']).toContain('multipart/form-data')
    })

    it('should get user profile', async () => {
      const userProfile = {
        id: 'user1',
        email: 'test@example.com',
        role: 'user',
      }

      localStorageMock.getItem.mockReturnValue('valid-token')
      mockAxios.onGet('/rag/user/profile').reply(200, userProfile)

      const result = await apiClient.getUserProfile()

      expect(result.data).toEqual(userProfile)
      expect(mockAxios.history.get[0].headers?.Authorization).toBe('Bearer valid-token')
    })

    it('should update user profile', async () => {
      const updateData = { email: 'newemail@example.com' }
      localStorageMock.getItem.mockReturnValue('valid-token')
      mockAxios.onPut('rag/user/profile').reply(200, updateData)

      const result = await apiClient.updateUserProfile(updateData)

      expect(result.data).toEqual(updateData)
      expect(JSON.parse(mockAxios.history.put[0].data)).toEqual(updateData)
    })

    it('should change password', async () => {
      const passwordData = {
        current_password: 'oldpass',
        new_password: 'newpass'
      }
      localStorageMock.getItem.mockReturnValue('valid-token')
      mockAxios.onPost('/rag/user/change-password').reply(200, { message: 'Password changed' })

      const result = await apiClient.changePassword(passwordData)

      expect(result.data).toEqual({ message: 'Password changed' })
      expect(JSON.parse(mockAxios.history.post[0].data)).toEqual(passwordData)
    })

    it('should logout user locally', () => {
      apiClient.logout()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('user')
    })
  })

  describe('Token Refresh', () => {
    it('should refresh token successfully', async () => {
      const newTokens = {
        access_token: 'new-token',
        refresh_token: 'new-refresh-token',
      }

      localStorageMock.getItem.mockReturnValue('old-refresh-token')
      mockAxios.onPost('/rag/auth/refresh').reply(200, newTokens)

      await apiClient.refreshToken()

      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new-token')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'new-refresh-token')
    })

    it('should throw error when no refresh token available', async () => {
      localStorageMock.getItem.mockReturnValue(null)

      await expect(apiClient.refreshToken()).rejects.toThrow('No refresh token')
    })

    it('should handle 401 errors with token refresh', async () => {
      localStorageMock.getItem
        .mockReturnValueOnce('expired-token') // First call for auth header
        .mockReturnValueOnce('refresh-token') // Second call for refresh
        .mockReturnValueOnce('new-token') // Third call for retry

      // First request fails with 401
      mockAxios.onGet('/rag/user/profile').replyOnce(401, { message: 'Unauthorized' })
      
      // Refresh token succeeds
      mockAxios.onPost('/rag/auth/refresh').reply(200, {
        access_token: 'new-token',
        refresh_token: 'new-refresh-token',
      })

      // Retry succeeds
      mockAxios.onGet('/rag/user/profile').reply(200, { id: 'user1' })

      const result = await apiClient.getUserProfile()

      expect(result.data).toEqual({ id: 'user1' })
      expect(mockAxios.history.get).toHaveLength(2) // Original + retry
      expect(mockAxios.history.post).toHaveLength(1) // Refresh token
    })

    it('should handle refresh failure and redirect to login', async () => {
      localStorageMock.getItem
        .mockReturnValueOnce('expired-token')
        .mockReturnValueOnce('invalid-refresh-token')

      // First request fails
      mockAxios.onGet('/rag/user/profile').replyOnce(401)
      
      // Refresh fails
      mockAxios.onPost('/rag/auth/refresh').reply(401, { message: 'Invalid refresh token' })

      await expect(apiClient.getUserProfile()).rejects.toThrow()

      // Should have attempted logout
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
    })
  })

  describe('Chat Methods', () => {
    beforeEach(() => {
      localStorageMock.getItem.mockReturnValue('valid-token')
    })

    it('should send message successfully', async () => {
      const messageData = { message: 'Hello', conversation_id: 'conv1' }
      const responseData = {
        message_id: 'msg1',
        message: 'Response',
        conversation_id: 'conv1',
      }

      mockAxios.onPost('/rag/chat/').reply(200, responseData)

      const result = await apiClient.sendMessage(messageData)

      expect(result.data).toEqual(responseData)
      expect(JSON.parse(mockAxios.history.post[0].data)).toEqual(messageData)
    })

    it('should get conversations', async () => {
      const conversations = [
        { id: 'conv1', title: 'Chat 1' },
        { id: 'conv2', title: 'Chat 2' },
      ]

      mockAxios.onGet('/rag/chat/conversations').reply(200, conversations)

      const result = await apiClient.getConversations()

      expect(result.data).toEqual(conversations)
    })

    it('should get single conversation', async () => {
      const conversation = {
        id: 'conv1',
        title: 'Chat 1',
        messages: [{ id: 'msg1', content: 'Hello' }],
      }

      mockAxios.onGet('/rag/chat/conversations/conv1').reply(200, conversation)

      const result = await apiClient.getConversation('conv1')

      expect(result.data).toEqual(conversation)
    })
  })

  describe('Document Methods', () => {
    beforeEach(() => {
      localStorageMock.getItem.mockReturnValue('valid-token')
    })

    it('should get documents list', async () => {
      const documents = [
        { id: 'doc1', name: 'test.pdf', status: 'completed' },
        { id: 'doc2', name: 'doc.txt', status: 'processing' },
      ]

      mockAxios.onGet('/rag/upload/').reply(200, documents)

      const result = await apiClient.getDocuments()

      expect(result.data).toEqual(documents)
    })

    it('should delete document', async () => {
      mockAxios.onDelete('/rag/upload/doc1').reply(200, { message: 'Document deleted' })

      const result = await apiClient.deleteDocument('doc1')

      expect(result.data).toEqual({ message: 'Document deleted' })
    })

    it('should upload document with progress tracking', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const onProgress = vi.fn()

      // Mock the fetch API for file upload with SSE
      const mockResponse = {
        ok: true,
        body: {
          getReader: () => ({
            read: vi.fn()
              .mockResolvedValueOnce({
                done: false,
                value: new TextEncoder().encode('data: {"status": "processing", "progress": 50}\n'),
              })
              .mockResolvedValueOnce({
                done: false,
                value: new TextEncoder().encode('data: {"status": "completed", "progress": 100}\n'),
              })
              .mockResolvedValueOnce({ done: true }),
            releaseLock: vi.fn(),
          }),
        },
      }

      global.fetch = vi.fn().mockResolvedValue(mockResponse)

      const result = await apiClient.uploadDocument(mockFile, onProgress)

      expect(result).toEqual({ data: { success: true } })
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/rag/upload/',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
          headers: expect.objectContaining({
            Authorization: 'Bearer valid-token',
          }),
        })
      )
      expect(onProgress).toHaveBeenCalledWith('processing', 50)
      expect(onProgress).toHaveBeenCalledWith('completed', 100)
    })

    it('should handle upload failure', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        statusText: 'Bad Request',
      })

      await expect(apiClient.uploadDocument(mockFile)).rejects.toThrow('Upload failed: Bad Request')
    })

    it('should handle upload with no response body', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        body: null,
      })

      await expect(apiClient.uploadDocument(mockFile)).rejects.toThrow('No response body')
    })
  })

  describe('Admin Methods', () => {
    beforeEach(() => {
      localStorageMock.getItem.mockReturnValue('admin-token')
    })

    it('should get backup stats', async () => {
      const stats = { backup_count: 5, last_backup: '2023-01-01' }
      mockAxios.onGet('/rag/admin/vector/backup/stats').reply(200, stats)

      const result = await apiClient.getBackupStats()

      expect(result.data).toEqual(stats)
    })

    it('should rebuild vector store with default parameters', async () => {
      mockAxios.onPost('/rag/admin/vector/rebuild').reply(200, { message: 'Rebuild started' })

      const result = await apiClient.rebuildVectorStore()

      expect(result.data).toEqual({ message: 'Rebuild started' })
      expect(mockAxios.history.post[0].url).toBe('/rag/admin/vector/rebuild')
    })

    it('should rebuild vector store with filters', async () => {
      const filters = {
        user_filter: 'user123',
        document_filter: 'pdf',
        batch_size: 50,
      }

      mockAxios.onPost('/rag/admin/vector/rebuild').reply(200, { message: 'Rebuild started' })

      await apiClient.rebuildVectorStore(filters)

      expect(mockAxios.history.post[0].url).toBe('/rag/admin/vector/rebuild?user_filter=user123&document_filter=pdf&batch_size=50')
    })
  })

  describe('Request Interceptors', () => {
    it('should add auth token to requests when available', async () => {
      localStorageMock.getItem.mockReturnValue('test-token')
      mockAxios.onGet('/rag/user/profile').reply(200, {})

      await apiClient.getUserProfile()

      expect(mockAxios.history.get[0].headers?.Authorization).toBe('Bearer test-token')
    })

    it('should make requests without auth token when not available', async () => {
      localStorageMock.getItem.mockReturnValue(null)
      mockAxios.onPost('/rag/auth/register').reply(200, {})

      await apiClient.register({ email: 'test@example.com', password: 'pass' })

      expect(mockAxios.history.post[0].headers?.Authorization).toBeUndefined()
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockAxios.onGet('/rag/user/profile').networkError()

      await expect(apiClient.getUserProfile()).rejects.toThrow('Network Error')
    })

    it('should handle server errors', async () => {
      mockAxios.onGet('/rag/user/profile').reply(500, { message: 'Internal Server Error' })

      await expect(apiClient.getUserProfile()).rejects.toThrow()
    })

    it('should prevent infinite refresh loops', async () => {
      localStorageMock.getItem
        .mockReturnValueOnce('expired-token')
        .mockReturnValueOnce('refresh-token')

      // Mock the response interceptor behavior
      let requestCount = 0
      mockAxios.onGet('/rag/user/profile').reply((config) => {
        requestCount++
        if (requestCount === 1) {
          // First request fails
          return [401, { message: 'Unauthorized' }]
        } else if (requestCount === 2) {
          // Retry after refresh also fails, but should prevent infinite loop
          return [401, { message: 'Still unauthorized' }]
        }
        return [200, { id: 'user1' }]
      })

      // Mock successful refresh
      mockAxios.onPost('/rag/auth/refresh').reply(200, {
        access_token: 'new-token',
        refresh_token: 'new-refresh-token',
      })

      await expect(apiClient.getUserProfile()).rejects.toThrow()
      expect(requestCount).toBe(2) // Original + one retry only
    })
  })
}) 