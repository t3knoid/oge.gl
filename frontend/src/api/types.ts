export type SortField = "transaction_date" | "filing_date" | "filer_name" | "description" | "amount_min";
export type SortOrder = "asc" | "desc";
export type IngestionRunMode = "incremental";

export interface TransactionListQuery {
  filer_name?: string;
  description?: string;
  trade_type?: string;
  transaction_date?: string;
  transaction_date_from?: string;
  transaction_date_to?: string;
  amount_text?: string;
  amount_min?: number;
  amount_max?: number;
  page?: number;
  page_size?: number;
  sort?: SortField;
  order?: SortOrder;
}

export interface TransactionItem {
  id: string;
  filing_id: string;
  filer_name: string;
  filer_title: string | null;
  agency: string | null;
  description: string;
  issuer_name: string | null;
  trade_type: string;
  trade_type_raw: string | null;
  transaction_date: string | null;
  transaction_date_raw: string | null;
  amount_text: string | null;
  amount_min: number | null;
  amount_max: number | null;
  filing_date: string | null;
  source_pdf_url: string;
}

export interface TransactionRecord {
  row_number: number;
  description: string;
  issuer_name: string | null;
  trade_type: string;
  trade_type_raw: string | null;
  transaction_date: string | null;
  transaction_date_raw: string | null;
  amount_text: string | null;
  amount_min: number | null;
  amount_max: number | null;
  raw_text: string;
  confidence_score: number | null;
}

export interface FilingRecord {
  id: string;
  external_id: string | null;
  filer_name: string;
  filer_title: string | null;
  agency: string | null;
  filing_date: string | null;
  report_period_start: string | null;
  report_period_end: string | null;
  source_page_url: string;
  source_pdf_url: string;
  ingest_status: string;
  transaction_count: number | null;
}

export interface IngestionRunRequest {
  mode: IngestionRunMode;
  limit: number;
}

export interface IngestionRunAcceptedResponse {
  job_id: string;
  status: string;
  accepted_at: string;
}

export interface IngestionJobItem {
  id: string;
  job_type: string;
  status: string;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  discovered_count: number;
  downloaded_count: number;
  ingested_count: number;
  warning_count: number;
  error_count: number;
}

export interface IngestionJobListResponse {
  items: IngestionJobItem[];
}

export interface TransactionListResponse {
  items: TransactionItem[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
  sort: string;
  order: string;
}

export interface TransactionDetailResponse {
  id: string;
  filing: FilingRecord;
  transaction: TransactionRecord;
}

export type FilingDetailResponse = FilingRecord;
