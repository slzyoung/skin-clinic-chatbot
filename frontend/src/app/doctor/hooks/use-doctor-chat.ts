import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/axios";
import { doctorChatKeys } from "../api/keys";
import type { 
  ChatSessionResponse, 
  ChatHistoryResponse, 
  ChatMessageResponse
} from "../api/types";
import { getErrorMessage } from "@/lib/utils";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export const useChatSessions = () => {
  return useQuery({
    queryKey: doctorChatKeys.sessions(),
    queryFn: async (): Promise<ChatHistoryResponse[]> => {
      const response = await api.get("/chats/");
      return response.data;
    },
  });
};

export const useCreateChatSession = () => {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: async ({ 
      branch_id, 
      initialMessageFormData 
    }: { 
      branch_id?: string | null, 
      initialMessageFormData?: FormData 
    }): Promise<ChatSessionResponse> => {
      const response = await api.post("/chats/", { branch_id });
      const session = response.data;

      if (initialMessageFormData) {
        await api.post(`/chats/${session.id}/messages`, initialMessageFormData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
      }

      return session;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: doctorChatKeys.sessions() });
      router.push(`/doctor/chat/${data.id}`);
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, "Failed to start chat session"));
    },
  });
};

export const useChatMessages = (sessionId: string) => {
  return useQuery({
    queryKey: doctorChatKeys.messages(sessionId),
    queryFn: async (): Promise<ChatMessageResponse[]> => {
      const response = await api.get(`/chats/${sessionId}/messages`);
      return response.data;
    },
    enabled: !!sessionId,
  });
};

import { useState } from "react";

export const useSendMessage = (sessionId: string) => {
  const queryClient = useQueryClient();
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const mutation = useMutation({
    mutationFn: async (formData: FormData): Promise<void> => {
      setIsStreaming(true);
      setStreamingText("");
      
      const baseURL = api.defaults.baseURL || "http://localhost:8000/api";
      
      const response = await fetch(`${baseURL}/chats/${sessionId}/messages`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "token") {
                setStreamingText((prev) => prev + data.content);
              } else if (data.type === "done") {
                // finished
              }
            } catch (e) {
              console.error("Error parsing SSE data", e);
            }
          }
        }
      }
    },
    onSuccess: () => {
      setIsStreaming(false);
      queryClient.invalidateQueries({ queryKey: doctorChatKeys.messages(sessionId) });
      queryClient.invalidateQueries({ queryKey: doctorChatKeys.sessions() });
    },
    onError: (error: unknown) => {
      setIsStreaming(false);
      toast.error(getErrorMessage(error, "Failed to send message"));
    },
  });

  return {
    ...mutation,
    streamingText,
    isStreaming,
  };
};
