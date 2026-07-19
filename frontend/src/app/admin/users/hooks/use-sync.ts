import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/axios";
import { getErrorMessage } from "@/lib/utils";
import { userKeys } from "../api/keys";

export const useSyncCIS = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const response = await api.post('/sync/cis');
      return response.data;
    },
    onSuccess: () => {
      toast.success("Sync with CIS completed successfully!");
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error, "Failed to sync with CIS."));
    }
  });
};
