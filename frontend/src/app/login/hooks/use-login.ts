import { useMutation } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { api } from "@/lib/axios";
import type { LoginResponse } from "../api/types";
import type { ApiError, UserResponse } from "@/lib/types";

export const useLogin = () => {
  return useMutation<
    { loginResponse: LoginResponse, userProfile: UserResponse },
    AxiosError<ApiError>,
    URLSearchParams
  >({
    mutationFn: async (credentials) => {
      // 1. Perform login
      const loginRes = await api.post<LoginResponse>('/auth/login', credentials, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // 2. Fetch user profile
      const meRes = await api.get<UserResponse>('/users/me');
      
      return {
        loginResponse: loginRes.data,
        userProfile: meRes.data,
      };
    },
    onSuccess: () => {
      // Optionally cache the user profile
      // queryClient.setQueryData(authKeys.me(), data.userProfile);
    },
  });
};
