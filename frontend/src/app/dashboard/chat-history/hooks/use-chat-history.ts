import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/axios";
import { chatHistoryKeys } from "../api/keys";
import type { ChatHistoryResponse, ChatStatsResponse } from "../api/types";

export function useChatHistories(doctor_id?: string) {
  return useQuery<ChatHistoryResponse[]>({
    queryKey: doctor_id ? chatHistoryKeys.list({ doctor_id }) : chatHistoryKeys.lists(),
    queryFn: async () => {
      const params = doctor_id ? { doctor_id } : undefined;
      const response = await api.get("/chats/", { params });
      return response.data;
    },
  });
}

export function useChatStats(doctor_id?: string) {
  return useQuery<ChatStatsResponse>({
    queryKey: chatHistoryKeys.stats(doctor_id),
    queryFn: async () => {
      const params = doctor_id ? { doctor_id } : undefined;
      const response = await api.get("/chats/stats", { params });
      return response.data;
    },
  });
}

export function useChatHistoryDetail(sessionId?: string | null) {
  return useQuery<ChatHistoryResponse>({
    queryKey: sessionId ? chatHistoryKeys.detail(sessionId) : ["chat-history", "detail", "empty"],
    queryFn: async () => {
      const response = await api.get(`/chats/${sessionId}`);
      return response.data;
    },
    enabled: !!sessionId,
  });
}

