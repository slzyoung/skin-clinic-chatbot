import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/axios";
import { getErrorMessage } from "@/lib/utils";
import { userKeys } from "../api/keys";
import type { UserResponse, UserCreateStaff, UserCreateDoctor, UserUpdate } from "../api/types";

export const useUsers = (type?: string) => {
  return useQuery({
    queryKey: userKeys.list(type),
    queryFn: async (): Promise<UserResponse[]> => {
      const response = await api.get('/users/', { params: { type } });
      return response.data;
    },
  });
};

export const useCreateStaff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (newStaff: UserCreateStaff) => {
      const response = await api.post('/users/staff', newStaff);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Staff user created successfully!");
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, "Failed to create staff user."));
    }
  });
};

export const useCreateDoctor = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (newDoctor: UserCreateDoctor) => {
      const response = await api.post('/users/doctors', newDoctor);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Doctor user created successfully!");
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, "Failed to create doctor user."));
    }
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ userId, data }: { userId: string, data: UserUpdate }) => {
      const response = await api.put(`/users/${userId}`, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success("User updated successfully!");
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
    onError: (error: any) => {
      toast.error(getErrorMessage(error, "Failed to update user."));
    }
  });
};
