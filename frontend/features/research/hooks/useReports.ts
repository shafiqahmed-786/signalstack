"use client";

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  archiveReport,
  fetchReport,
  fetchReports,
  updateReport,
} from "../api/client";

import type { ReportUpdatePayload } from "@/types/api";

export const reportKeys = {
  all: ["reports"] as const,

  lists: () => [...reportKeys.all, "list"] as const,

  list: (params: {
    page?: number;
    page_size?: number;
    status?: string;
    pinned?: boolean;
  }) => [...reportKeys.lists(), params] as const,

  details: () => [...reportKeys.all, "detail"] as const,

  detail: (id: string) => [...reportKeys.details(), id] as const,
};

type ReportsParams = {
  page?: number;
  page_size?: number;
  status?: string;
  pinned?: boolean;
};

export function useReports(params: ReportsParams = {}) {
  const { getToken, isLoaded, userId } = useAuth();

  return useQuery({
    queryKey: reportKeys.list(params),

    enabled: isLoaded && !!userId,

    queryFn: async () => {
      const token = await getToken();

      if (!token) {
        throw new Error("Authentication token unavailable");
      }

      return fetchReports(token, params);
    },

    staleTime: 30_000,

    retry: 1,

    refetchOnWindowFocus: false,
  });
}

export function useReport(reportId: string | null) {
  const { getToken, isLoaded, userId } = useAuth();

  return useQuery({
    queryKey: reportKeys.detail(reportId ?? ""),

    enabled: isLoaded && !!userId && !!reportId,

    queryFn: async () => {
      if (!reportId) {
        throw new Error("Missing report ID");
      }

      const token = await getToken();

      if (!token) {
        throw new Error("Authentication token unavailable");
      }

      return fetchReport(token, reportId);
    },

    staleTime: 60_000,

    retry: 1,

    refetchOnWindowFocus: false,
  });
}

export function useUpdateReport() {
  const { getToken } = useAuth();

  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: ReportUpdatePayload;
    }) => {
      const token = await getToken();

      if (!token) {
        throw new Error("Authentication token unavailable");
      }

      return updateReport(token, id, payload);
    },

    onSuccess: (updatedReport) => {
      queryClient.setQueryData(
        reportKeys.detail(updatedReport.id),
        updatedReport
      );

      queryClient.invalidateQueries({
        queryKey: reportKeys.lists(),
      });
    },
  });
}

export function useArchiveReport() {
  const { getToken } = useAuth();

  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reportId: string) => {
      const token = await getToken();

      if (!token) {
        throw new Error("Authentication token unavailable");
      }

      return archiveReport(token, reportId);
    },

    onSuccess: (_, reportId) => {
      queryClient.removeQueries({
        queryKey: reportKeys.detail(reportId),
      });

      queryClient.invalidateQueries({
        queryKey: reportKeys.lists(),
      });
    },
  });
}