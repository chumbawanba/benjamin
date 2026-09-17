import { useEffect, useState } from 'react';
import { ApiError, api } from '../api/client';
import { Projection } from '../api/types';
import ProjectionChart from '../components/ProjectionChart';

function toNum(v: number | string): number {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function money(v: number, currency?: string | null): string {
  return `${v.toFixed(0)} ${currency ?? ''}`.trim();
}

// Marcos mostrados na tabela abaixo do gráfico - todos os anos seria
// demasiada linha para um horizonte de 20-30 anos; estes pontos dão uma
// leitura rápida sem esconder o gráfico completo (que já mostra tudo).
function milestoneYears(years: number): number[] {
  const candidates = [0, 1, 5, 10, 15, 20, 25, 30, 40, 50, 60];
  return candidates.filter((y) => y <= years && (y === 0 || y === years || y % 5 === 0));
}

export default function ProjectionPage() {
  const [years, setYears] = useState('20');
  const [annualReturnPct, setAnnualReturnPct] = useState('5');
  const [data, setData] = useState<Projection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(y: string, r: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<Projection>(`/projection?years=${y}&annual_return_pct=${r}`);
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao calcular projeção');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(years, annualReturnPct);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void load(years, annualReturnPct);
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-1">Projeção de património</h1>
      <p className="text-xs text-gray-400 dark:text-slate-500 mb-4">
        Extrapolação simples a partir dos dados de hoje: o portfolio cresce à rentabilidade que indicares
        abaixo, cada outro ativo (imóveis, outros - ver separador Património) cresce à sua própria taxa
        esperada, e cada empréstimo desce pela sua prestação mensal x 12 por ano até chegar a zero. Não é
        aconselhamento financeiro nem uma previsão - é só para teres uma ideia de tendência.
      </p>

      <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 flex flex-wrap items-end gap-3">
        <label className="text-xs text-gray-500 dark:text-slate-400">
          Horizonte (anos)
          <input
            value={years}
            onChange={(e) => setYears(e.target.value)}
            inputMode="numeric"
            className="block w-24 mt-1 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
          />
        </label>
        <label className="text-xs text-gray-500 dark:text-slate-400">
          Rentabilidade anual assumida (%)
          <input
            value={annualReturnPct}
            onChange={(e) => setAnnualReturnPct(e.target.value)}
            inputMode="decimal"
            className="block w-32 mt-1 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          {loading ? '…' : 'Simular'}
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {data && (
        <>
          <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xs text-gray-400 dark:text-slate-500">Portfolio hoje</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
                {money(toNum(data.starting_portfolio_value), data.currency)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 dark:text-slate-500">Outros ativos hoje</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
                {money(toNum(data.starting_other_assets_value), data.currency)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 dark:text-slate-500">Em dívida hoje</p>
              <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
                {money(toNum(data.starting_loans_balance), data.currency)}
              </p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-3">
              Património líquido projetado ({data.currency})
            </p>
            <ProjectionChart points={data.points} />
          </div>

          <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-400 dark:text-slate-500 border-b border-gray-100 dark:border-slate-800">
                  <th className="text-left font-medium px-4 py-2">Ano</th>
                  <th className="text-right font-medium px-4 py-2">Portfolio</th>
                  <th className="text-right font-medium px-4 py-2">Outros ativos</th>
                  <th className="text-right font-medium px-4 py-2">Dívida</th>
                  <th className="text-right font-medium px-4 py-2">Património líquido</th>
                </tr>
              </thead>
              <tbody>
                {milestoneYears(data.years).map((y) => {
                  const point = data.points[y];
                  if (!point) return null;
                  return (
                    <tr key={y} className="border-b border-gray-50 dark:border-slate-800/50 last:border-0">
                      <td className="px-4 py-2 text-gray-500 dark:text-slate-400">{y === 0 ? 'Hoje' : `+${y}`}</td>
                      <td className="px-4 py-2 text-right text-gray-900 dark:text-slate-100">
                        {money(toNum(point.portfolio_value), data.currency)}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-900 dark:text-slate-100">
                        {money(toNum(point.other_assets_value), data.currency)}
                      </td>
                      <td className="px-4 py-2 text-right text-gray-900 dark:text-slate-100">
                        {money(toNum(point.loans_balance), data.currency)}
                      </td>
                      <td className="px-4 py-2 text-right font-semibold text-gray-900 dark:text-slate-100">
                        {money(toNum(point.net_worth), data.currency)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
