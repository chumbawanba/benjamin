import { AdminDailyRegistrations } from '../api/types';

interface Props {
  daily: AdminDailyRegistrations[];
  width?: number;
  height?: number;
}

// Gráfico de linhas simples (users vs waitlist, acumulados), sem dependências
// externas - segue o mesmo padrão do Sparkline.tsx (só SVG à mão). `daily` já
// vem ordenado por data (services/admin.py) com contagens por dia; a soma
// acumulada é feita aqui para mostrar crescimento total ao longo do tempo.
export default function AdminRegistrationsChart({ daily, width = 600, height = 160 }: Props) {
  if (daily.length === 0) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 dark:text-slate-500" style={{ width: '100%', height }}>
        Ainda sem registos para mostrar.
      </div>
    );
  }

  let usersAcc = 0;
  let waitlistAcc = 0;
  const usersCumulative = daily.map((d) => (usersAcc += d.users));
  const waitlistCumulative = daily.map((d) => (waitlistAcc += d.waitlist));

  const max = Math.max(...usersCumulative, ...waitlistCumulative, 1);
  const stepX = daily.length > 1 ? width / (daily.length - 1) : 0;
  const toPoints = (series: number[]) =>
    series.map((v, i) => `${i * stepX},${height - (v / max) * height}`).join(' ');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
        <polyline points={toPoints(waitlistCumulative)} fill="none" strokeWidth={2} strokeDasharray="5 4" className="stroke-amber-500 dark:stroke-amber-400" />
        <polyline points={toPoints(usersCumulative)} fill="none" strokeWidth={2} className="stroke-navy-600 dark:stroke-navy-400" />
      </svg>
      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-slate-500 mt-1">
        <span>{new Date(daily[0].date).toLocaleDateString('pt-PT')}</span>
        <span>{new Date(daily[daily.length - 1].date).toLocaleDateString('pt-PT')}</span>
      </div>
      <div className="flex items-center gap-4 mt-1.5 text-xs text-gray-500 dark:text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-0.5 bg-navy-600 dark:bg-navy-400" />
          Registos na app ({usersAcc})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-0 border-t-2 border-dashed border-amber-500 dark:border-amber-400" />
          Waitlist ({waitlistAcc})
        </span>
      </div>
    </div>
  );
}
