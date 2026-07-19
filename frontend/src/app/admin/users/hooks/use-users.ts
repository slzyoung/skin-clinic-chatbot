import { api } from "@/lib/axios";
import { getErrorMessage } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { userKeys } from "../api/keys";
import type {
	DoctorUpdate,
	StaffUpdate,
	UserCreateDoctor,
	UserCreateStaff,
	UserResponse,
} from "../api/types";

export const useUsers = (type?: string) => {
	return useQuery({
		queryKey: userKeys.list(type),
		queryFn: async (): Promise<UserResponse[]> => {
			const response = await api.get("/users/", { params: { type } });
			return response.data;
		},
	});
};

export const useCreateStaff = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (newStaff: UserCreateStaff) => {
			const response = await api.post("/users/staff", newStaff);
			return response.data;
		},
		onSuccess: () => {
			toast.success("Staff user created successfully!");
			queryClient.invalidateQueries({ queryKey: userKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to create staff user."));
		},
	});
};

export const useCreateDoctor = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async (newDoctor: UserCreateDoctor) => {
			const response = await api.post("/users/doctors", newDoctor);
			return response.data;
		},
		onSuccess: () => {
			toast.success("Doctor user created successfully!");
			queryClient.invalidateQueries({ queryKey: userKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to create doctor user."));
		},
	});
};

export const useUpdateDoctorAccess = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async ({ userId, data }: { userId: string; data: DoctorUpdate }) => {
			const response = await api.put(`/users/${userId}`, data);
			return response.data;
		},
		onSuccess: () => {
			toast.success("Doctor access updated successfully!");
			queryClient.invalidateQueries({ queryKey: userKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to update doctor access."));
		},
	});
};

export const useUpdateStaffDetails = () => {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: async ({ userId, data }: { userId: string; data: StaffUpdate }) => {
			const response = await api.put(`/users/${userId}`, data);
			return response.data;
		},
		onSuccess: () => {
			toast.success("Staff details updated successfully!");
			queryClient.invalidateQueries({ queryKey: userKeys.lists() });
		},
		onError: (error: unknown) => {
			toast.error(getErrorMessage(error, "Failed to update staff details."));
		},
	});
};
