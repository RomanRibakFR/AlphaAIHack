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

/**
 * Ставка продукта диапазоном: «15—22% годовых».
 *
 * Нижняя граница у всех продуктов одинаковая — ключевая ставка плюс маржа
 * банка, — а расходятся они потолком. Одно число тут сказало бы неправду:
 * по нижней границе получит только заёмщик без риска.
 */
export function rateRange(from: string | null | undefined, to: string | null | undefined): string {
  if (!from) return "—";
  if (!to || Number(to) <= Number(from)) return rate(from);
  return `${Number(from).toLocaleString("ru-RU")}—${Number(to).toLocaleString("ru-RU")}% годовых`;
}

/**
 * Срок продукта: «6—36 мес.», а при фиксированном сроке — «12 мес.».
 * У овердрафта лимит ставится ровно на год, и «12—12» выглядело бы опиской.
 */
export function termRange(from: number, to: number): string {
  return from === to ? `${from} мес.` : `${from}—${to} мес.`;
}

/** Выбор формы слова по числу: 1 платёж, 2 платежа, 5 платежей. */
export function plural(n: number, one: string, few: string, many: string): string {
  const last = n % 10;
  const tens = n % 100;
  if (last === 1 && tens !== 11) return one;
  if (last >= 2 && last <= 4 && (tens < 12 || tens > 14)) return few;
  return many;
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

/**
 * Срок жизни бизнеса словами: «8 месяцев», «2 года 3 месяца».
 * В месяцах длинные сроки читаются плохо — «139 месяцев» никто не осмыслит.
 */
export function duration(totalMonths: number): string {
  if (totalMonths < 24) return months(totalMonths);

  const years = Math.floor(totalMonths / 12);
  const rest = totalMonths % 12;

  const lastY = years % 10;
  const tensY = years % 100;
  let yearWord = "лет";
  if (lastY === 1 && tensY !== 11) yearWord = "год";
  else if (lastY >= 2 && lastY <= 4 && (tensY < 12 || tensY > 14)) yearWord = "года";

  return rest === 0 ? `${years} ${yearWord}` : `${years} ${yearWord} ${months(rest)}`;
}
