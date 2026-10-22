/** Деньги приходят строками ("2000000.00"). Форматируем без потери копеек на больших суммах. */
export function money(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return `${n.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽`;
}

export function rate(value: string | null | undefined): string {
  if (!value) return "—";
  return `${Number(value).toLocaleString("ru-RU")}% годовых`;
}

/** 1 месяц / 6 месяцев / 24 месяца */
export function months(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const last = value % 10;
  const tens = value % 100;
  let word = "месяцев";
  if (last === 1 && tens !== 11) word = "месяц";
  else if (last >= 2 && last <= 4 && (tens < 12 || tens > 14)) word = "месяца";
  return `${value} ${word}`;
}

/**
 * Бэкенд отдаёт время БЕЗ таймзоны ("2026-10-22T17:39:00"), а значения в нём
 * UTC-шные. Без суффикса браузер прочитал бы их как локальное время и показал
 * сдвиг на несколько часов, поэтому дописываем Z сами.
 *
 * Костыль: правильнее попросить бэкенд отдавать время с таймзоной.
 */
function parseUtc(iso: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

export function dateTime(iso: string): string {
  const d = parseUtc(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function date(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("ru-RU");
}
