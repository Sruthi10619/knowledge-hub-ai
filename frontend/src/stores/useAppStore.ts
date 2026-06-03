import { create } from "zustand";
import axios from "axios";

// Default configuration for axios calls
axios.defaults.baseURL = "/api/v1";

// Add JWT access token to axios requests if present
const token = localStorage.getItem("access_token");
if (token) {
  axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  avatar_url?: string;
  preferred_language: string;
}

export interface Folder {
  id: string;
  name: string;
  description?: string;
  icon: string;
  color: string;
  document_count: number;
}

interface AppState {
  token: string | null;
  user: User | null;
  folders: Folder[];
  currentFolder: Folder | null;
  theme: "dark" | "light";
  loading: boolean;
  
  // Auth operations
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
  
  // Folder operations
  fetchFolders: () => Promise<void>;
  createFolder: (name: string, description?: string, icon?: string, color?: string) => Promise<Folder>;
  deleteFolder: (folderId: string) => Promise<void>;
  setCurrentFolder: (folder: Folder | null) => void;
  
  // Theme
  toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  token: localStorage.getItem("access_token"),
  user: null,
  folders: [],
  currentFolder: null,
  theme: (localStorage.getItem("theme") as "dark" | "light") || "dark",
  loading: false,

  setToken: (token) => {
    if (token) {
      localStorage.setItem("access_token", token);
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
      localStorage.removeItem("access_token");
      delete axios.defaults.headers.common["Authorization"];
    }
    set({ token });
  },

  setUser: (user) => set({ user }),

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    delete axios.defaults.headers.common["Authorization"];
    set({ token: null, user: null, folders: [], currentFolder: null });
  },

  checkAuth: async () => {
    const activeToken = get().token;
    if (!activeToken) return false;

    try {
      set({ loading: true });
      const res = await axios.get("/auth/me");
      set({ user: res.data, loading: false });
      return true;
    } catch (e) {
      // Token is invalid/expired
      get().logout();
      set({ loading: false });
      return false;
    }
  },

  fetchFolders: async () => {
    try {
      const res = await axios.get("/folders");
      set({ folders: res.data });
    } catch (e) {
      console.error("Failed to load folders:", e);
    }
  },

  createFolder: async (name, description, icon, color) => {
    const res = await axios.post("/folders", { name, description, icon, color });
    const newFolder = res.data;
    set((state) => ({ folders: [newFolder, ...state.folders] }));
    return newFolder;
  },

  deleteFolder: async (folderId) => {
    await axios.delete(`/folders/${folderId}`);
    set((state) => ({
      folders: state.folders.filter((f) => f.id !== folderId),
      currentFolder: state.currentFolder?.id === folderId ? null : state.currentFolder
    }));
  },

  setCurrentFolder: (folder) => set({ currentFolder: folder }),

  toggleTheme: () => {
    const currentTheme = get().theme;
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", newTheme);
    
    // Update HTML class list
    const root = window.document.documentElement;
    root.classList.remove(currentTheme);
    root.classList.add(newTheme);
    
    set({ theme: newTheme });
  }
}));

// Token refresh on 401 (single-flight)
let isRefreshing = false;
type QueueItem = {
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
};
let refreshQueue: QueueItem[] = [];

function processRefreshQueue(error: unknown | null, token: string | null = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else if (token) resolve(token);
  });
  refreshQueue = [];
}

axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as { _retry?: boolean; url?: string; headers?: Record<string, string> };
    if (!originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }

    const isAuthEndpoint =
      originalRequest.url?.includes("/auth/login") ||
      originalRequest.url?.includes("/auth/signup") ||
      originalRequest.url?.includes("/auth/refresh");

    if (error.response?.status !== 401 || isAuthEndpoint) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      useAppStore.getState().logout();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        refreshQueue.push({ resolve, reject });
      }).then((newToken) => {
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return axios(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const res = await axios.post("/auth/refresh", { refresh_token: refreshToken });
      const newAccess = res.data.access_token as string;
      useAppStore.getState().setToken(newAccess);
      if (res.data.refresh_token) {
        localStorage.setItem("refresh_token", res.data.refresh_token);
      }
      processRefreshQueue(null, newAccess);
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return axios(originalRequest);
    } catch (refreshError) {
      processRefreshQueue(refreshError, null);
      useAppStore.getState().logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
