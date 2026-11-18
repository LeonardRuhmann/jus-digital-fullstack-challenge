import type {
  ApiErrorPayload,
  BulkDeleteResponse,
  DocumentItem,
  DocumentListResponse,
  User,
} from "../types";

export const API_BASE_URL = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly errorCode: string;

  constructor(message: string, status: number, errorCode = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include", // Always include HttpOnly session cookie
  });

  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const payload = (data || {}) as ApiErrorPayload;
    const message =
      payload.message ||
      payload.detail ||
      `Erro inesperado na requisição (${response.status}).`;
    const code = payload.error || "API_ERROR";
    throw new ApiClientError(message, response.status, code);
  }

  return data as T;
}

export const authApi = {
  /** URL that starts the server-side Google OAuth 2.0 flow */
  getGoogleLoginUrl(): string {
    return `${API_BASE_URL}/api/auth/google/login`;
  },

  /** Fetch the currently authenticated user profile from the HttpOnly cookie */
  getMe(): Promise<User> {
    return request<User>("/api/auth/me");
  },

  /** Clear the HttpOnly session cookie */
  logout(): Promise<void> {
    return request<void>("/api/auth/logout", { method: "POST" });
  },
};

export const documentsApi = {
  /** List all documents belonging to the current user */
  list(): Promise<DocumentListResponse> {
    return request<DocumentListResponse>("/api/documents");
  },

  /** Get a single document with its AI analysis and fresh S3 presigned URL */
  getById(documentId: string): Promise<DocumentItem> {
    return request<DocumentItem>(`/api/documents/${documentId}`);
  },

  /** Upload a file with title and AI instruction (Multipart Form) */
  upload(
    file: File,
    title: string,
    instruction: string
  ): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    formData.append("instruction", instruction);

    return request<DocumentItem>("/api/documents", {
      method: "POST",
      body: formData,
    });
  },

  /** Retry OpenAI GPT-4o-mini analysis for a failed document */
  retry(documentId: string): Promise<DocumentItem> {
    return request<DocumentItem>(`/api/documents/${documentId}/retry`, {
      method: "POST",
    });
  },

  /** Delete a single document */
  deleteOne(documentId: string): Promise<BulkDeleteResponse> {
    return request<BulkDeleteResponse>(`/api/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  /** Delete multiple selected documents at once */
  bulkDelete(documentIds: string[]): Promise<BulkDeleteResponse> {
    return request<BulkDeleteResponse>("/api/documents/bulk-delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    });
  },
};

/** Format file size in bytes to match Figma card format (e.g. "34 KB", "1.2 MB") */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${Math.max(1, Math.round(kb))} KB`;
  }
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

/** Format ISO date to Brazilian format matching Figma card ("26/05/2025") */
export function formatDateBR(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}
