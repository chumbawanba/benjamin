// Conversão dia-da-semana/hora entre UTC (como é guardado, ver
// User.report_day_of_week/report_hour no backend - CLAUDE.md exige tudo em
// UTC) e a hora local do browser (como o utilizador escolhe/vê na página de
// Notificações). Convenção 0=segunda ... 6=domingo (datetime.weekday()).
//
// Nota: soma milissegundos fixos a um instante âncora - não lida com o salto
// de DST ao segundo exato em que muda (o horário do resumo semanal pode
// ficar 1h desviado nessa semana específica), o que é aceitável para um
// resumo semanal informativo - evita puxar uma biblioteca de fusos horários
// só para isto (CLAUDE.md: sem abstrações para o futuro).

const MS_PER_HOUR = 3600_000;
const MS_PER_DAY = 24 * MS_PER_HOUR;

// 2024-01-01 é uma segunda-feira (data-calendário, independente de fuso).
const MONDAY_ANCHOR_UTC = Date.UTC(2024, 0, 1, 0, 0, 0);
const MONDAY_ANCHOR_LOCAL = new Date(2024, 0, 1, 0, 0, 0).getTime();

export function utcToLocalSchedule(dayUtc: number, hourUtc: number): { day: number; hour: number } {
  const instant = MONDAY_ANCHOR_UTC + dayUtc * MS_PER_DAY + hourUtc * MS_PER_HOUR;
  const d = new Date(instant);
  const day = (d.getDay() + 6) % 7; // getDay(): 0=domingo -> convertido para 0=segunda
  return { day, hour: d.getHours() };
}

export function localToUtcSchedule(dayLocal: number, hourLocal: number): { day: number; hour: number } {
  const instant = MONDAY_ANCHOR_LOCAL + dayLocal * MS_PER_DAY + hourLocal * MS_PER_HOUR;
  const d = new Date(instant);
  const day = (d.getUTCDay() + 6) % 7;
  return { day, hour: d.getUTCHours() };
}

export const WEEKDAY_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
