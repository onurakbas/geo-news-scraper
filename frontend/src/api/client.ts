/**
 * Central Axios instance for all API calls.
 * All request/response interceptors go here – keep endpoints in dedicated modules.
 */
import axios from "axios";

const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Response error normalisation
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error.response?.data?.detail ?? error.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  },
);

export default apiClient;
