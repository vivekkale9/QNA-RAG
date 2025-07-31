import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Define handlers for API endpoints
export const handlers = [
  // Auth endpoints
  http.post('/rag/auth/register', () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      user: {
        id: 'user-123',
        email: 'test@example.com',
        role: 'user',
        created_at: new Date().toISOString(),
        document_count: 0,
        query_count: 0,
      },
    })
  }),

  http.post('/rag/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      user: {
        id: 'user-123',
        email: 'test@example.com',
        role: 'user',
        created_at: new Date().toISOString(),
        document_count: 2,
        query_count: 5,
      },
    })
  }),

  http.get('/rag/auth/me', () => {
    return HttpResponse.json({
      id: 'user-123',
      email: 'test@example.com',
      role: 'user',
      created_at: new Date().toISOString(),
      document_count: 2,
      query_count: 5,
    })
  }),

  // Chat endpoints
  http.post('/rag/chat/send', () => {
    return HttpResponse.json({
      message_id: 'msg-123',
      message: 'This is a mock AI response for testing purposes.',
      conversation_id: 'conv-123',
      sources: [
        {
          document_id: 'doc-123',
          document_name: 'test.pdf',
          chunk_id: 'chunk-123',
          content: 'This is a test document chunk.',
          similarity_score: 0.95,
          page_number: 1,
        },
      ],
      model_used: 'gpt-3.5-turbo',
      created_at: new Date().toISOString(),
    })
  }),

  http.get('/rag/chat/conversations', () => {
    return HttpResponse.json([
      {
        id: 'conv-123',
        title: 'Test Conversation',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 4,
      },
    ])
  }),

  http.get('/rag/chat/conversations/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      title: 'Test Conversation',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      messages: [
        {
          id: 'msg-1',
          role: 'user',
          content: 'What is this document about?',
          created_at: new Date().toISOString(),
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'This document appears to be about testing.',
          sources: [],
          created_at: new Date().toISOString(),
        },
      ],
    })
  }),

  // Document endpoints
  http.get('/rag/documents', () => {
    return HttpResponse.json([
      {
        id: 'doc-123',
        name: 'test.pdf',
        file_size: 1024,
        file_type: 'pdf',
        status: 'completed',
        chunk_count: 5,
        query_count: 3,
        uploaded_at: new Date().toISOString(),
        processed_at: new Date().toISOString(),
      },
    ])
  }),

  // Fallback for unhandled requests
  http.all('*', ({ request }) => {
    console.warn(`Unhandled ${request.method} ${request.url}`)
    return new HttpResponse(null, { status: 404 })
  }),
]

// Setup the server
export const server = setupServer(...handlers) 