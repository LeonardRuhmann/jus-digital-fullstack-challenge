export type DocumentStatus = "PROCESSING" | "COMPLETED" | "FAILED";

export interface User {
  id: string;
  google_id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  title: string;
  instruction: string;
  ai_response: string | null;
  status: DocumentStatus;
  error_message: string | null;
  file_name: string;
  file_extension: string;
  content_type: string;
  file_size: number;
  created_at: string;
  updated_at: string;
  presigned_url: string | null;
}

export interface DocumentListResponse {
  total: number;
  items: DocumentItem[];
}

export interface BulkDeleteResponse {
  deleted_count: number;
  deleted_ids: string[];
}

export interface ApiErrorPayload {
  error?: string;
  message?: string;
  detail?: string;
}
