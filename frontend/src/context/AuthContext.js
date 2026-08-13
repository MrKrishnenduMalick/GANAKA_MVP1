import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getAccessToken, readError, refreshSession, setAccessToken, setUnauthorizedHandler } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [status, setStatus] = useState("loading");
  const [session, setSession] = useState(null);

  const loadMe = useCallback(async () => {
    const response = await api.get("/auth/me");
    setSession(response.data);
    setStatus("authenticated");
    return response.data;
  }, []);

  const signOutLocal = useCallback(() => {
    setAccessToken(null);
    setSession(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession(null);
      setStatus("anonymous");
    });
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        if (!getAccessToken()) await refreshSession();
        await loadMe();
      } catch {
        signOutLocal();
      }
    };
    bootstrap();
  }, [loadMe, signOutLocal]);

  const login = useCallback(
    async (email, password) => {
      const response = await api.post("/auth/login", { email, password });
      setAccessToken(response.data.access_token);
      await loadMe();
      return response.data;
    },
    [loadMe],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* the session is dropped locally regardless */
    }
    signOutLocal();
  }, [signOutLocal]);

  const switchWorkspace = useCallback(
    async (workspaceId) => {
      const response = await api.post(`/workspaces/${workspaceId}/switch`);
      setAccessToken(response.data.access_token);
      await loadMe();
    },
    [loadMe],
  );

  const value = useMemo(
    () => ({
      status,
      session,
      user: session?.user || null,
      workspace: session?.workspace || null,
      workspaces: session?.workspaces || [],
      role: session?.role || null,
      permissions: session?.permissions || [],
      can: (permission) => (session?.permissions || []).includes(permission),
      login,
      logout,
      loadMe,
      switchWorkspace,
      signOutLocal,
    }),
    [status, session, login, logout, loadMe, switchWorkspace, signOutLocal],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
};

export { readError };
