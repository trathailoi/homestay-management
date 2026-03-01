"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import api from "./api";
import type { User } from "./types";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if already authenticated on mount
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      // apiFetch returns the JSON response directly
      const response = await api.get<{ success: boolean; data: User }>("/auth/me");
      setUser(response.data);
    } catch {
      // Not authenticated or error - that's fine
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function login(username: string, password: string) {
    // POST to login endpoint
    await api.post("/auth/login", { username, password });
    // Fetch user info after successful login
    const response = await api.get<{ success: boolean; data: User }>("/auth/me");
    setUser(response.data);
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
