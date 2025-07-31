import axios, { AxiosInstance, AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor to handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401 && !error.config._retry) {
          error.config._retry = true; // Prevent infinite refresh loops
          
          try {
            await this.refreshToken();
            const token = localStorage.getItem('access_token');
            if (token) {
              error.config.headers.Authorization = `Bearer ${token}`;
              return this.client.request(error.config);
            }
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            this.logout();
            
            // Only redirect if not already on login page
            if (!window.location.pathname.includes('/auth/login')) {
              window.location.href = '/auth/login';
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  async refreshToken(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) throw new Error('No refresh token');

    // Backend expects refresh_token as a string parameter, not JSON
    const response = await this.client.post('/rag/auth/refresh', refreshToken, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const { access_token, refresh_token: newRefreshToken } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', newRefreshToken);
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  // Auth endpoints
  async register(data: { email: string; password: string; role?: string }) {
    return this.client.post('/rag/auth/register', {
      email: data.email,
      password: data.password,
      role: data.role || 'user'
    });
  }

  async login(data: { email: string; password: string }) {
    // Backend expects OAuth2PasswordRequestForm format (form data with username/password)
    const formData = new FormData();
    formData.append('username', data.email); // Use email as username
    formData.append('password', data.password);
    
    return this.client.post('/rag/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // Document endpoints
  async uploadDocument(file: File, onProgress?: (stage: string, progress?: number) => void) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.client.defaults.baseURL}/rag/upload/`, {
      method: 'POST',
      body: formData,
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.status && onProgress) {
                onProgress(data.status, data.progress);
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return { data: { success: true } };
  }

  async getDocuments() {
    return this.client.get('/rag/upload/');
  }

  async deleteDocument(id: string) {
    return this.client.delete(`/rag/upload/${id}`);
  }

  // Chat endpoints
  async sendMessage(data: { message: string; conversation_id?: string; max_chunks?: number }) {
    return this.client.post('/rag/chat/', data);
  }

  async getConversations() {
    return this.client.get('/rag/chat/conversations');
  }

  async getConversation(id: string) {
    return this.client.get(`/rag/chat/conversations/${id}`);
  }

  // User endpoints
  async getUserProfile() {
    return this.client.get('/rag/user/profile');
  }

  async updateUserProfile(data: { email?: string }) {
    return this.client.put('rag/user/profile', data);
  }

  async changePassword(data: { current_password: string; new_password: string }) {
    return this.client.post('/rag/user/change-password', data);
  }

  // Admin endpoints
  async getBackupStats() {
    return this.client.get('/rag/admin/vector/backup/stats');
  }

  async rebuildVectorStore(filters?: { user_filter?: string; document_filter?: string; batch_size?: number }) {
    const params = new URLSearchParams();
    if (filters?.user_filter) params.append('user_filter', filters.user_filter);
    if (filters?.document_filter) params.append('document_filter', filters.document_filter);
    if (filters?.batch_size) params.append('batch_size', filters.batch_size.toString());
    
    const url = `/rag/admin/vector/rebuild${params.toString() ? `?${params.toString()}` : ''}`;
    return this.client.post(url);
  }

  async rebuildVectorStoreWithProgress(
    filters?: { user_filter?: string; document_filter?: string; batch_size?: number },
    onProgress?: (data: {
      status: string;
      progress: number;
      message: string;
      total_chunks: number;
      processed_chunks: number;
      total_documents: number;
      processed_documents: number;
    }) => void
  ) {
    const params = new URLSearchParams();
    if (filters?.user_filter) params.append('user_filter', filters.user_filter);
    if (filters?.document_filter) params.append('document_filter', filters.document_filter);
    if (filters?.batch_size) params.append('batch_size', filters.batch_size.toString());
    
    const url = `/rag/admin/vector/rebuild/stream${params.toString() ? `?${params.toString()}` : ''}`;
    
    const response = await fetch(`${this.client.defaults.baseURL}${url}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    });

    if (!response.ok) {
      throw new Error(`Rebuild failed: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (onProgress) {
                onProgress(data);
              }
              
              // If completed or failed, break out
              if (data.status === 'completed' || data.status === 'failed') {
                return { success: data.status === 'completed', data };
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return { success: true, data: { status: 'completed' } };
  }
}

export const apiClient = new ApiClient();