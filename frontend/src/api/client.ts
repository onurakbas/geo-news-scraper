import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL, 
  
  headers: {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message: string =
      error.response?.data?.detail ?? error.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  },
);

export default apiClient;