import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';
import { formatRelativeTime } from '../utils/format';

// Rótulo curto por tipo de notificação (ver app/models/notification.py::kind) -
// o texto completo já vem em message, isto é só um selo visual rápido.
const KIND_LABELS: Record<string, string> = {
  price_buy: 'Preço de compra',
  price_sell: 'Preço de venda',
  signal_buy: 'Sinal de compra',
  signal_sell: 'Sinal de venda',
  weekly_report: 'Resumo semanal',
};

const KIND_STYLES: Record<string, string> = {
  price_buy: 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  signal_buy: 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  price_sell: 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400',
  signal_sell: 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400',
  weekly_report: 'bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400',
};

export default function Notifications() {
  const { notifications, loading, error, preferences, markRead, updatePreferences } = useNotifications();
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [prefsError, setPrefsError] = useState<string | null>(null);

  async function togglePref(key: 'email_reports_enabled' | 'email_alerts_enabled') {
    if (!preferences) return;
    setSavingPrefs(true);
    setPrefsError(null);
    try {
      await updatePreferences({ ...preferences, [key]: !preferences[key] });
    } catch {
      setPrefsError('Erro ao gravar preferências');
    } finally {
      setSavingPrefs(false);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Notificações</h1>

      <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3">Preferências de email</h2>
        {preferences ? (
          <div className="space-y-3">
            <label className="flex items-center justify-between gap-3 text-sm">
              <span className="text-gray-700 dark:text-slate-300">
                Resumo semanal por email
                <span className="block text-xs text-gray-400 dark:text-slate-500">
                  Recomendações da tua watchlist, uma vez por semana.
                </span>
              </span>
              <input
                type="checkbox"
                checked={preferences.email_reports_enabled}
                disabled={savingPrefs}
                onChange={() => togglePref('email_reports_enabled')}
                className="w-4 h-4 accent-navy-600 shrink-0"
              />
            </label>
            <label className="flex items-center justify-between gap-3 text-sm">
              <span className="text-gray-700 dark:text-slate-300">
                Alertas por email
                <span className="block text-xs text-gray-400 dark:text-slate-500">
                  Preço-alvo atingido ou mudança de sinal de compra/venda.
                </span>
              </span>
              <input
                type="checkbox"
                checked={preferences.email_alerts_enabled}
                disabled={savingPrefs}
                onChange={() => togglePref('email_alerts_enabled')}
                className="w-4 h-4 accent-navy-600 shrink-0"
              />
            </label>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
        )}
        {prefsError && <p className="text-sm text-red-600 dark:text-rose-400 mt-2">{prefsError}</p>}
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-3">
          Podes cancelar a subscrição de emails a qualquer momento a partir do link no rodapé de cada email recebido.
        </p>
      </div>

      <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2">
        Configura preço-alvo e alertas de sinal por ação em{' '}
        <Link to="/workspace" className="text-navy-600 dark:text-navy-400">
          cada página de detalhe
        </Link>
        .
      </h2>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : notifications.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não tens notificações.</p>
      ) : (
        <ul className="space-y-2">
          {notifications.map((n) => (
            <li
              key={n.id}
              onClick={() => !n.read_at && markRead(n.id)}
              className={`bg-white dark:bg-slate-900 border rounded-xl shadow-sm p-4 flex items-start justify-between gap-2 ${
                n.read_at
                  ? 'border-gray-100 dark:border-slate-800'
                  : 'border-navy-200 dark:border-navy-500/40 cursor-pointer'
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      KIND_STYLES[n.kind] ?? 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400'
                    }`}
                  >
                    {KIND_LABELS[n.kind] ?? n.kind}
                  </span>
                  {!n.read_at && <span className="w-2 h-2 rounded-full bg-navy-600 dark:bg-navy-400 shrink-0" />}
                </div>
                <p className="text-sm text-gray-900 dark:text-slate-100">{n.message}</p>
                <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">{formatRelativeTime(n.created_at)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
