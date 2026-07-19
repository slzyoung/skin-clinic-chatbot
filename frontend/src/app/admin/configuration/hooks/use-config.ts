import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/axios";
import { getErrorMessage } from "@/lib/utils";
import { configKeys } from "../api/keys";
import type { ConfigResponse, ConfigUpdate } from "../api/types";

export const useConfigs = () => {
  return useQuery({
    queryKey: configKeys.lists(),
    queryFn: async (): Promise<ConfigResponse[]> => {
      const response = await api.get('/config/');
      return response.data;
    },
  });
};

export const useUpdateConfig = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ key, data }: { key: string, data: ConfigUpdate }) => {
      const response = await api.put(`/config/${key}`, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Settings updated successfully!");
      queryClient.invalidateQueries({ queryKey: configKeys.lists() });
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, "Failed to update settings."));
    }
  });
};
