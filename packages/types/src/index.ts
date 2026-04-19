/** Shared API response shapes (mirror FastAPI where useful). */

export type CompanyRow = { name: string };

export type TokenResponse = {
  teambition_access_token: string;
  tenant_id: string;
  company_name: string;
  session_jwt?: string | null;
};

export type ApiConfigRow = {
  name: string;
  description?: string;
  method: string;
  endpoint: string;
  default_params?: Record<string, unknown> | string;
  resolvers?: Record<string, string> | string;
  response_key?: string;
  pagination?: boolean;
};

export type DebugLogEntry = {
  timestamp?: string;
  method?: string;
  endpoint?: string;
  full_url?: string;
  headers?: Record<string, string>;
  headers_full?: Record<string, string>;
  params?: Record<string, unknown>;
  http_status?: number;
  status?: string | number;
  response_code?: number | null;
  error_message?: string;
  response_json?: unknown;
};
