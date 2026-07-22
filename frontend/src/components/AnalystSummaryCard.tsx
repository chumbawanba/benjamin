import { useEffect, useState } from 'react';
import { ApiError, api } from '../api/client';
import { AnalystPrompt, AnalystSummary } from '../api/types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' });
}

// Resumo estilo analista (Benjamin) gerado por IA (watchlist + mercado geral) —
// substitui os cartões de contagem Comprar/Vender/Manter no topo do Overview.
// Atualização é sempre manual (botão), nunca automática — ver backend/app/services/analyst.py.
// O prompt de sistema usado para gerar o resumo é editável (botão "Editar prompt").
// Nota: o chat "Perguntar ao Benjamin" já não vive aqui — passou a ser global (painel
// lateral no desktop, botão flutuante no mobile), ver Layout.tsx e AnalystChatContext.tsx.
export default function AnalystSummaryCard() {
  const [data, setData] = useState<AnalystSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [editorOpen, setEditorOpen] = useState(false);
  const [promptDraft, setPromptDraft] = useState('');
  const [promptIsDefault, setPromptIsDefault] = useState(true);
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptError, setPromptError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const result = await api.get<AnalystSummary>('/analyst/summary');
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar resumo');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      const result = await api.post<AnalystSummary>('/analyst/summary/refresh');
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao gerar resumo');
    } finally {
      setRefreshing(false);
    }
  }

  async function openEditor() {
    setEditorOpen(true);
    setPromptError(null);
    setPromptLoading(true);
    try {
      const result = await api.get<AnalystPrompt>('/analyst/prompt');
      setPromptDraft(result.prompt);
      setPromptIsDefault(result.is_default);
    } catch (err) {
      setPromptError(err instanceof ApiError ? err.message : 'Erro ao carregar prompt');
    } finally {
      setPromptLoading(false);
    }
  }

  async function savePrompt(prompt: string | null) {
    setPromptSaving(true);
    setPromptError(null);
    try {
      const result = await api.put<AnalystPrompt>('/analyst/prompt', { prompt });
      setPromptDraft(result.prompt);
      setPromptIsDefault(result.is_default);
      setEditorOpen(false);
    } catch (err) {
      setPromptError(err instanceof ApiError ? err.message : 'Erro ao guardar prompt');
    } finally {
      setPromptSaving(false);
    }
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">Resumo do Benjamin</h2>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => (editorOpen ? setEditorOpen(false) : openEditor())}
            className="text-xs font-medium text-gray-500 dark:text-slate-400"
          >
            {editorOpen ? 'Fechar' : 'Editar prompt'}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            className="text-xs font-medium text-navy-600 dark:text-navy-400 disabled:opacity-50"
          >
            {refreshing ? 'A gerar…' : data?.summary ? 'Atualizar análise' : 'Gerar análise'}
          </button>
        </div>
      </div>

      {editorOpen && (
        <div className="mb-3 pb-3 border-b border-gray-100 dark:border-slate-800">
          {promptLoading ? (
            <p className="text-xs text-gray-400 dark:text-slate-500">A carregar prompt…</p>
          ) : (
            <>
              <textarea
                value={promptDraft}
                onChange={(e) => setPromptDraft(e.target.value)}
                rows={6}
                className="w-full text-xs bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-800 dark:text-slate-200 rounded-lg px-3 py-2 font-mono"
              />
              {promptError && <p className="text-xs text-red-600 dark:text-rose-400 mt-1">{promptError}</p>}
              <div className="flex items-center gap-3 mt-2 text-xs font-medium">
                <button
                  onClick={() => savePrompt(promptDraft)}
                  disabled={promptSaving}
                  className="text-navy-600 dark:text-navy-400 disabled:opacity-50"
                >
                  {promptSaving ? 'A guardar…' : 'Guardar'}
                </button>
                {!promptIsDefault && (
                  <button
                    onClick={() => savePrompt(null)}
                    disabled={promptSaving}
                    className="text-gray-500 dark:text-slate-400 disabled:opacity-50"
                  >
                    Repor predefinição
                  </button>
                )}
                <button
                  onClick={() => setEditorOpen(false)}
                  disabled={promptSaving}
                  className="text-gray-400 dark:text-slate-500 disabled:opacity-50"
                >
                  Cancelar
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="text-xs text-red-600 dark:text-rose-400 mb-2">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-400 dark:text-slate-500">A carregar…</p>
      ) : data?.summary ? (
        <>
          <p className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-line">{data.summary}</p>
          <p className="text-[11px] text-gray-400 dark:text-slate-500 mt-2 leading-snug">
            Gerado por IA — pode conter erros. Não é aconselhamento financeiro; a decisão de
            investir é sempre tua.
          </p>
          {data.generated_at && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              Gerado em {formatDate(data.generated_at)}
            </p>
          )}
        </>
      ) : (
        <p className="text-sm text-gray-400 dark:text-slate-500">
          Ainda não há um resumo. Clica em "Gerar análise" para pedir um resumo ao Benjamin com base na tua watchlist
          e no mercado geral.
        </p>
      )}
    </div>
  );
}
