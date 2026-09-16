import { FormEvent, useState } from 'react';
import { ApiError, adminGet } from '../api/client';
import type { AdminStats as AdminStatsData } from '../api/types';

// Página de admin simples (sem papel de admin no modelo User - ver
// CLAUDE.md/backend/app/security.py::require_admin): autentica com uma
// chave partilhada (X-Admin-Key), pedida aqui e nunca guardada (só em
// memória do componente), e mostra as contagens de GET /admin/stats.
// Rota não listada no NavBar/SideNav - acede-se digitando /admin.
export default function AdminStats() {
  const [adminKey, setAdminKey] = useState('');
  const [stats, setStats] = useState<AdminStatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setStats(null);
    try {
      const data = await adminGet<AdminStatsData>('/admin/stats', adminKey);
      setStats(data);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? 'Chave inválida' : 'Falha ao obter estatísticas');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 p-6 rounded-xl shadow-sm">
          <h1 className="text-xl font-bold text-navy-600 dark:text-navy-400 mb-1">Benjamin — Admin</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">Estatísticas de registos</p>

          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1" htmlFor="admin-key">
            Chave de admin
          </label>
          <input
            id="admin-key"
            type="password"
            autoComplete="off"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 mb-4 text-sm"
          />

          {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-navy-600 text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
          >
            {loading ? 'A consultar…' : 'Ver estatísticas'}
          </button>
        </form>

        {stats && (
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-navy-600 dark:text-navy-400">{stats.users_total}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Registos na app</p>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-navy-600 dark:text-navy-400">{stats.waitlist_total}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Inscrições na waitlist (email)</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
