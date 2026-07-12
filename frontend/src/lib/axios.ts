import axios from "axios";

// Determine the base URL. If NEXT_PUBLIC_API_URL is set, use it. Otherwise, default to local FastAPI dev server.
const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const api = axios.create({
  baseURL,
  // Ensure cookies are sent with every request (important for JWT HTTP-only cookies)
  withCredentials: true,
});

// Request interceptor to add any needed headers (e.g., CSRF tokens if you have them, though HTTP-only cookies handle auth)
api.interceptors.request.use(
  (config) => {
    // You can attach custom headers here if needed.
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling global errors (like 401 Unauthorized)
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    // Check if error is 401 Unauthorized
    if (error.response && error.response.status === 401) {
      // The user is not authenticated or their token expired.
      // Depending on your auth flow, you might attempt to call a refresh endpoint here.
      // For now, we will just redirect to the login page.
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
