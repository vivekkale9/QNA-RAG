export interface User {
  id: string;
  email: string;
  role: 'user' | 'admin';
  created_at: string;
  document_count: number;
  query_count: number;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Document {
  id: string;
  name: string;
  description?: string;
  file_size: number;
  file_type: 'pdf' | 'txt' | 'md';
  status: 'uploading' | 'processing' | 'completed' | 'failed' | 'deleted';
  chunk_count: number;
  query_count: number;
  uploaded_at: string;
  processed_at?: string;
  user_id: string;
  file_path: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: DocumentSource[];
  metadata?: {
    [key: string]: any;
  };
}

export interface DocumentSource {
  document_id: string;
  document_name: string;
  chunk_id: string;
  page_number?: number;
  content: string;
  similarity_score: number;
  start_char?: number;
  end_char?: number;
}

export interface Conversation {
  id: string;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  document_ids?: number[];
  max_chunks?: number;
  max_sources?: number;
  temperature?: number;
  stream?: boolean;
  include_sources?: boolean;
}

export interface ChatResponse {
  message: string;
  sources: DocumentSource[];
  conversation_id: string;
  message_id: string;
  tokens_used?: number;
  model_used: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}