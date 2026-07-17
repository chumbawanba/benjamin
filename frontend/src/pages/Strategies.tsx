import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { StrategyTemplate } from '../api/types';

export default function Strategies() {
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<StrategyTemplate[]>('/strategies');
      setTemplates(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar estratégias');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.post('/strategies', { name: name.trim() });
      setName('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao criar estratégia');
    }
  }

  async function toggleActive(t: StrategyTemplate) {
    try {
      await api.put(`/strategies/${t.id}`, {
        name: t.name,
        description: t.description,
        is_active: !t.is_active,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao atualizar estratégia');
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Apagar esta estratégia e todos os seus critérios?')) return;
    try {
      await api.delete(`/strategies/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao apagar estratégia');
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Estratégias</h1>

      <form onSubmit={handleCreate} className="flex gap-2 mb-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nome da nova estratégia"
          className="flex-1 bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
        />
        <button type="submit" className="bg-petrol-600 text-white rounded-lg px-4 py-2 text-sm font-semibold">
          Criar
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : templates.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não tens estratégias.</p>
      ) : (
        <ul className="space-y-2">
          {templates.map((t) => (
            <li key={t.id} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{t.name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t.items.length} critério(s)</p>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    t.is_active
                      ? 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400'
                      : 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-500'
                  }`}
                >
                  {t.is_active ? 'Ativa' : 'Inativa'}
                </span>
              </div>
              <div className="flex gap-3 mt-3 text-sm font-medium">
                <Link to={`/strategies/${t.id}`} className="text-petrol-600 dark:text-petrol-400">
                  Editar
                </Link>
                <button onClick={() => toggleActive(t)} className="text-gray-600 dark:text-slate-400">
                  {t.is_active ? 'Desativar' : 'Ativar'}
                </button>
                <button onClick={() => handleDelete(t.id)} className="text-red-500 dark:text-rose-400">
                  Apagar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
