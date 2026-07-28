import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { ApiError, api } from '../api/client';
import { Notification, NotificationPreferences } from '../api/types';

// Intervalo de sondagem do sino de notificações - suficiente para um sinal
// de "há novidades" sem sobrecarregar a API (os alertas em si só são
// gerados uma vez por dia, ver app/services/alerts.py).
const POLL_INTERVAL_MS = 60_000;

interface NotificationContextValue {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
  error: string | null;
  preferences: NotificationPreferences | null;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  updatePreferences: (prefs: NotificationPreferences) => Promise<void>;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

// Estado do centro de notificações vive acima das rotas (ver App.tsx), tal como
// o AnalystChatContext, para que o sino no header (NavBar/SideNav) e a página
// /notifications partilhem a mesma contagem de não lidas sem duplicar pedidos.
export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const [list, prefs] = await Promise.all([
        api.get<Notification[]>('/notifications?limit=30'),
        api.get<NotificationPreferences>('/notifications/preferences'),
      ]);
      setNotifications(list);
      setPreferences(prefs);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar notificações');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function markRead(id: string) {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)));
    try {
      await api.put(`/notifications/${id}/read`);
    } catch {
      await refresh(); // repõe o estado real do servidor se o pedido falhar
    }
  }

  async function updatePreferences(prefs: NotificationPreferences) {
    const updated = await api.put<NotificationPreferences>('/notifications/preferences', prefs);
    setPreferences(updated);
  }

  const unreadCount = notifications.filter((n) => n.read_at === null).length;

  return (
    <NotificationContext.Provider
      value={{ notifications, unreadCount, loading, error, preferences, refresh, markRead, updatePreferences }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications deve ser usado dentro de NotificationProvider');
  return ctx;
}
