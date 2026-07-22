import { KeyboardEvent } from 'react';
import { useAnalystChat } from '../context/AnalystChatContext';

interface Props {
  // Só passado pelo modal fullscreen no mobile (AskBenjaminFab) - no painel fixo do
  // desktop não há nada para fechar, está sempre visível.
  onClose?: () => void;
}

// UI do chat "Perguntar ao Benjamin", partilhada entre o painel lateral fixo do desktop
// (ver Layout.tsx) e o modal fullscreen do mobile (ver AskBenjaminFab.tsx). O estado vem
// todo do AnalystChatContext - este componente é só a apresentação.
export default function AskBenjaminPanel({ onClose }: Props) {
  const { messages, questionDraft, setQuestionDraft, asking, askError, ask, clear } = useAnalystChat();

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void ask();
    }
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 flex flex-col">
      <div className="flex items-center justify-between gap-2 mb-1">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">Perguntar ao Benjamin</h2>
        {onClose && (
          <button onClick={onClose} className="text-xs font-medium text-gray-400 dark:text-slate-500">
            Fechar
          </button>
        )}
      </div>
      {/* Sempre visível, não só quando há mensagens - o utilizador deve ver isto antes
          de ler qualquer resposta gerada, não depois. Ver pedido: deixar claro que é IA,
          pode ter erros, não é aconselhamento, e a decisão é sempre do investidor. */}
      <p className="text-[11px] text-gray-400 dark:text-slate-500 mb-3 leading-snug">
        Respostas geradas por IA — podem conter erros. Não é aconselhamento financeiro; a
        decisão de investir é sempre tua.
      </p>

      <div className="flex-1 overflow-y-auto max-h-[55vh] space-y-2 mb-3 min-h-[80px]">
        {messages.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Pergunta sobre a tua watchlist, portfólio ou um sinal específico — ex: "porque não tenho compra na
            Microsoft?"
          </p>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              className={`text-xs rounded-lg px-3 py-2 whitespace-pre-line ${
                m.role === 'user'
                  ? 'bg-navy-50 text-navy-800 dark:bg-navy-500/15 dark:text-navy-300 ml-6'
                  : 'bg-gray-50 text-gray-700 dark:bg-slate-800 dark:text-slate-300 mr-6'
              }`}
            >
              {m.content}
            </div>
          ))
        )}
      </div>

      {askError && <p className="text-xs text-red-600 dark:text-rose-400 mb-2">{askError}</p>}

      <div className="flex items-end gap-2">
        <textarea
          value={questionDraft}
          onChange={(e) => setQuestionDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={asking}
          rows={2}
          placeholder="Pergunta ao Benjamin…"
          className="flex-1 text-xs bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-800 dark:text-slate-200 rounded-lg px-3 py-2 disabled:opacity-50"
        />
        <button
          onClick={() => void ask()}
          disabled={asking || !questionDraft.trim()}
          className="text-xs font-medium text-navy-600 dark:text-navy-400 disabled:opacity-50 shrink-0"
        >
          {asking ? 'A pensar…' : 'Enviar'}
        </button>
      </div>
      {messages.length > 0 && (
        <button
          onClick={clear}
          disabled={asking}
          className="text-xs text-gray-400 dark:text-slate-500 mt-2 self-start disabled:opacity-50"
        >
          Limpar conversa
        </button>
      )}
    </div>
  );
}
