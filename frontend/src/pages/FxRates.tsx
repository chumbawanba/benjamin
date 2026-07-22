import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { FxRate } from '../api/types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-PT', { dateStyle: 'medium' });
}

// Página de referência: mostra as taxas de câmbio atualmente usadas para
// converter o portfolio (só as moedas que o utilizador realmente tem, contra
// a moeda preferida - ver GET /portfolio/fx-rates). Existe para tirar dúvidas
// sobre um valor convertido, não para consulta geral de câmbio.
export default function FxRates() {
  const [rates, setRates] = useState<FxRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await api.get<FxRate[]>('/portfolio/fx-rates');
        setRates(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Erro ao carregar taxas de câmbio');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Link to="/portfolio" className="text-sm text-navy-600 dark:text-navy-400 font-medium">
          ← Portfolio
        </Link>
      </div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-1">Taxas de câmbio</h1>
      <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">
        Usadas para converter as posições do teu portfolio para a moeda que escolheste.
      </p>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : rates.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Sem conversões a mostrar — ou não tens posições ainda, ou todas já estão na moeda que escolheste.
        </p>
      ) : (
        <ul className="space-y-2">
          {rates.map((r) => (
            <li
              key={`${r.base_currency}-${r.quote_currency}`}
              className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 flex items-center justify-between"
            >
              <div>
                <p className="font-semibold text-gray-900 dark:text-slate-100">
                  1 {r.base_currency} = {Number(r.rate).toFixed(4)} {r.quote_currency}
                </p>
                <p className="text-xs text-gray-400 dark:text-slate-500">Atualizado em {formatDate(r.date)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
