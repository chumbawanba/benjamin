import { ReactNode, createContext, useCallback, useContext, useState } from 'react';
import { api, getToken, setToken } from '../api/client';

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, acceptedTerms: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!getToken());

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<{ access_token: string }>('/auth/login', { email, password });
    setToken(res.access_token);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string, acceptedTerms: boolean) => {
    const res = await api.post<{ access_token: string }>('/auth/register', {
      name, email, password, accepted_terms: acceptedTerms,
    });
    setToken(res.access_token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setIsAuthenticated(false);
  }, []);

  return <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>');
  return ctx;
}
