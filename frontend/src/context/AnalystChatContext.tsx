import { createContext, ReactNode, useContext, useState } from 'react';
import { ApiError, api } from '../api/client';
import { AnalystAskResponse, AnalystChatMessage } from '../api/types';

// Espelha AnalystAskIn.history em app/schemas/common.py (max_length=20) - sem isto,
// uma conversa longa seria rejeitada com 422 a partir da 21ª mensagem.
const MAX_HISTORY_SENT = 20;

interface AnalystChatContextValue {
  messages: AnalystChatMessage[];
  questionDraft: string;
  setQuestionDraft: (value: string) => void;
  asking: boolean;
  askError: string | null;
  ask: () => Promise<void>;
  clear: () => void;
}

const AnalystChatContext = createContext<AnalystChatContextValue | null>(null);

// Estado do chat "Perguntar ao Benjamin" vive acima das rotas (ver App.tsx) para que a
// conversa persista ao navegar entre páginas - o painel lateral fixo (desktop, em
// Layout.tsx) e o botão flutuante (mobile, AskBenjaminFab.tsx) partilham o mesmo estado,
// não são duas conversas separadas. Sem tabela na BD - a conversa perde-se ao dar refresh
// à página, tal como já era antes desta ficar global (ver backend/app/services/analyst.py).
export function AnalystChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<AnalystChatMessage[]>([]);
  const [questionDraft, setQuestionDraft] = useState('');
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  async function ask() {
    const question = questionDraft.trim();
    if (!question || asking) return;
    setAsking(true);
    setAskError(null);
    const history = messages.slice(-MAX_HISTORY_SENT);
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setQuestionDraft('');
    try {
      const result = await api.post<AnalystAskResponse>('/analyst/ask', { question, history });
      setMessages((prev) => [...prev, { role: 'assistant', content: result.answer }]);
    } catch (err) {
      setAskError(err instanceof ApiError ? err.message : 'Erro ao perguntar ao Benjamin');
    } finally {
      setAsking(false);
    }
  }

  function clear() {
    setMessages([]);
    setAskError(null);
  }

  return (
    <AnalystChatContext.Provider
      value={{ messages, questionDraft, setQuestionDraft, asking, askError, ask, clear }}
    >
      {children}
    </AnalystChatContext.Provider>
  );
}

export function useAnalystChat(): AnalystChatContextValue {
  const ctx = useContext(AnalystChatContext);
  if (!ctx) throw new Error('useAnalystChat deve ser usado dentro de AnalystChatProvider');
  return ctx;
}
