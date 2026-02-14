import axios, { AxiosError } from "axios";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:18000";

export const api = axios.create({
  baseURL,
  withCredentials: true,
});

const refreshClient = axios.create({
  baseURL,
  withCredentials: true,
});

export const setAccessToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as (AxiosError["config"] & { _retry?: boolean }) | undefined;
    if (!config || config._retry) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401) {
      config._retry = true;
      try {
        const refreshRes = await refreshClient.post("/auth/refresh");
        const newToken = (refreshRes.data as { access_token?: string })?.access_token;
        if (newToken) {
          localStorage.setItem("access_token", newToken);
          setAccessToken(newToken);
          config.headers.Authorization = `Bearer ${newToken}`;
          return api.request(config);
        }
      } catch {
        localStorage.removeItem("access_token");
        setAccessToken(null);
      }
    }

    return Promise.reject(error);
  }
);
