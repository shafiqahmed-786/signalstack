import { apiFetch, ApiClientError } from "@/lib/api";
import type {
  ReportDetail,
  ReportListResponse,
  ReportUpdatePayload,
} from "@/types/api";

export async function fetchReports(
  token: string,
  params: {
    page?: number;
    page_size?: number;
    status?: string;
    company?: string;
    pinned?: boolean;
  } = {}
): Promise<ReportListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.status) query.set("status", params.status);
  if (params.company) query.set("company", params.company);
  if (params.pinned) query.set("pinned", "true");

  return apiFetch<ReportListResponse>(
    `/api/v1/research?${query.toString()}`,
    { token }
  );
}

export async function fetchReport(
  token: string,
  reportId: string
): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/api/v1/research/${reportId}`, { token });
}

export async function fetchReportStatus(
  token: string,
  reportId: string
): Promise<{ report_id: string; status: string; processing_time_ms: number | null; error_message: string | null }> {
  return apiFetch(`/api/v1/research/${reportId}/status`, { token });
}

export async function updateReport(
  token: string,
  reportId: string,
  payload: ReportUpdatePayload
): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/api/v1/research/${reportId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload),
  });
}

export async function archiveReport(
  token: string,
  reportId: string
): Promise<void> {
  await apiFetch(`/api/v1/research/${reportId}`, {
    method: "DELETE",
    token,
  });
}