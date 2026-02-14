import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:18000";

export const api = axios.create({
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
