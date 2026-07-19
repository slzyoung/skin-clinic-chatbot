import { api } from "@/lib/axios";
import { getErrorMessage } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { knowledgeKeys } from "../api/keys";
import type { KnowledgeResponse, KnowledgeStatus } from "../api/types";

export const useKnowledgeBaseList = (type?: string) => {
	return useQuery({
		queryKey: knowledgeKeys.list({ type }),
		queryFn: async (): Promise<KnowledgeResponse[]> => {
			const response = await api.get("/knowledge/", { params: { type } });
			return response.data;
		},
	});
};

export const useUploadKnowledge = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (formData: FormData) => {
			// Sending multipart/form-data
			const response = await api.post("/knowledge/upload", formData, {
				headers: {
					"Content-Type": "multipart/form-data",
				},
			});
			return response.data;
		},
		onSuccess: () => {
			toast.success("Files uploaded successfully!");
			queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to upload knowledge files."));
		},
	});
};

export const useUpdateKnowledgeStatus = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async ({ id, status }: { id: string; status: KnowledgeStatus }) => {
			const response = await api.patch(`/knowledge/${id}/status`, { status });
			return response.data;
		},
		onSuccess: () => {
			toast.success("Status updated successfully!");
			queryClient.invalidateQueries({ queryKey: knowledgeKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to update status."));
		},
	});
};
