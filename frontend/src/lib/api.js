import axios from "axios";

const BASE_URL = `${process.env.REACT_APP_BACKEND_URL}/api/v1`;
const TOKEN_STORAGE_KEY = "ganaka.access_token";

let unauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

export const getAccessToken = () => sessionStorage.getItem(TOKEN_STORAGE_KEY);

export const setAccessToken = (token) => {
  if (token) sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
  else sessionStorage.removeItem(TOKEN_STORAGE_KEY);
};

export const api = axios.create({ baseURL: BASE_URL, withCredentials: true });

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshInFlight = null;

// Public auth endpoints authenticate the request themselves; a 401 from them is
// the real answer, so it must never be rewritten by the refresh retry below.
const NO_REFRESH_PATHS = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/forgot-password",
  "/auth/reset-password",
  "/auth/verify-email",
  "/auth/google",
];

const runRefresh = () => {
  if (!refreshInFlight) {
    refreshInFlight = axios
      .post(`${BASE_URL}/auth/refresh`, {}, { withCredentials: true })
      .then((response) => {
        setAccessToken(response.data.access_token);
        return response.data.access_token;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const code = error.response?.data?.code;
    const skipRefresh = NO_REFRESH_PATHS.some((path) => original.url?.includes(path));

    if (error.response?.status === 401 && !original._retried && !skipRefresh) {
      original._retried = true;
      try {
        await runRefresh();
        return api(original);
      } catch (refreshError) {
        setAccessToken(null);
        if (unauthorizedHandler) unauthorizedHandler();
        return Promise.reject(refreshError);
      }
    }
    if (error.response?.status === 401 && code && !skipRefresh) {
      setAccessToken(null);
      if (unauthorizedHandler) unauthorizedHandler();
    }
    return Promise.reject(error);
  },
);

export const refreshSession = runRefresh;

export const readError = (error) => {
  const data = error?.response?.data;
  if (!data) return { code: "NETWORK", message: "Unable to reach Ganaka. Check your connection." };
  return {
    code: data.code || "UNKNOWN-001",
    message: data.message || "Something went wrong.",
    details: data.details || [],
  };
};
