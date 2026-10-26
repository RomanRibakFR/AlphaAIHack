/** Словари рабочего места сотрудника банка.
 *
 *  Здесь, в отличие от кабинета, банковские слова уместны: экран читает
 *  кредитный специалист. Но коды наружу всё равно не показываем — человек
 *  не обязан помнить, что такое M1_GREY_ZONE.
 */

/** Почему заявка ушла на ручной разбор — как в backend/app/texts.py. */
export const MANUAL_TRIGGERS: Record<string, string> = {
  M1_GREY_ZONE: "Пограничная оценка риска (класс C)",
  M2_LARGE_AMOUNT: "Сумма выше порога автоодобрения",
  M3_COLLATERAL: "Кредит с залогом — залог требует оценки",
  M4_DATA_MISMATCH: "Выручка в анкете не подтверждена выпиской",
  M5_CHECKS_INCOMPLETE: "Внешний источник не ответил",
  M6_MODEL_UNAVAILABLE: "Модель оценки риска недоступна или для неё нет данных",
  M7_REVIEWED_BEFORE: "Заявку уже рассматривал специалист",
  M8_OUT_OF_MODEL_SCOPE: "Категория бизнеса вне области модели (не микро и не малое)",
};

/**
 * Признаки модели PD задачи 2 — названия из docs/decision-policy.md, раздел 5.1.
 * У ИП 11 признаков, у юрлица ещё 8 из отчётности; показываем те, что пришли в решении.
 */
export const FEATURES: Array<{
  key: string;
  title: string;
  hint: string;
  format: "years" | "share" | "ratio" | "months" | "flag";
}> = [
  { key: "cash_buffer_months", title: "Денежный резерв", hint: "остаток на счёте к расходам и платежам, месяцев", format: "months" },
  { key: "debt_coverage", title: "Покрытие долговых платежей", hint: "(поступления − расходы) / все платежи по кредитам", format: "ratio" },
  { key: "cash_operating_margin", title: "Денежная маржа", hint: "доля поступлений, остающаяся после расходов", format: "share" },
  { key: "receipts_growth", title: "Динамика поступлений", hint: "последние 3 мес. к предыдущим 3", format: "share" },
  { key: "receipts_cv", title: "Колебания поступлений", hint: "коэффициент вариации за 12 мес.", format: "share" },
  { key: "largest_customer_share", title: "Концентрация покупателей", hint: "доля крупнейшего покупателя, без эквайринга", format: "share" },
  { key: "business_age_years", title: "Возраст бизнеса", hint: "лет с даты регистрации · ЕГРЮЛ", format: "years" },
  { key: "is_small_business", title: "Малое предприятие", hint: "реестр МСП: малое, а не микро", format: "flag" },
  { key: "industry_manufacturing", title: "Отрасль: производство", hint: "ОКВЭД2 10–33", format: "flag" },
  { key: "industry_construction", title: "Отрасль: строительство", hint: "ОКВЭД2 41–43", format: "flag" },
  { key: "industry_trade", title: "Отрасль: торговля", hint: "ОКВЭД2 45–47", format: "flag" },
  { key: "equity_assets", title: "Капитал к активам", hint: "строки 1300 / 1600 · ГИР БО", format: "share" },
  { key: "current_ratio", title: "Текущая ликвидность", hint: "строки 1200 / 1500 · ГИР БО", format: "ratio" },
  { key: "net_margin", title: "Чистая рентабельность", hint: "строки 2400 / 2110 · ГИР БО", format: "share" },
  { key: "asset_turnover", title: "Оборачиваемость активов", hint: "строки 2110 / 1600 · ГИР БО", format: "ratio" },
  { key: "short_term_liabilities_assets", title: "Краткосрочные обязательства к активам", hint: "строки 1500 / 1600 · ГИР БО", format: "share" },
  { key: "expenses_revenue", title: "Расходы к выручке", hint: "строки 2120 / 2110 · ГИР БО", format: "ratio" },
  { key: "expenses_missing", title: "Нет строки 2120", hint: "расходы заменены медианой обучения", format: "flag" },
  { key: "simplified_reporting", title: "Упрощённая отчётность", hint: "форма отчётности · ГИР БО", format: "flag" },
];

/** Внешние источники — как их называют люди. */
export const SOURCES: Record<string, string> = {
  egrul: "ЕГРЮЛ / ЕГРИП",
  fns: "ФНС",
  zsk: "ЗСК (115-ФЗ)",
  bki: "Бюро кредитных историй",
  bank: "Данные банка",
  gir_bo: "ГИР БО (отчётность)",
};

/** Что ответил источник. */
export const CHECK_STATUS: Record<string, { label: string; tone: "ok" | "warn" | "bad" }> = {
  ok: { label: "Ответил", tone: "ok" },
  not_found: { label: "Нет сведений", tone: "warn" },
  unavailable: { label: "Недоступен", tone: "bad" },
  timeout: { label: "Не дождались ответа", tone: "bad" },
  error: { label: "Ошибка", tone: "bad" },
};

/** Что ограничило лимит — из docs/decision-policy.md. */
export const LIMIT_BINDING: Record<string, string> = {
  new_payment: "новый платёж ≤ 10% поступлений",
  total_debt_service: "вся нагрузка ≤ 17% поступлений",
  turnover_share: "доля оборота (овердрафт)",
  product_max: "максимум продукта",
  collateral: "стоимость залога",
};

/** Исход решения. */
export const OUTCOME: Record<string, string> = {
  AUTO_APPROVED: "Автоодобрение",
  APPROVED: "Одобрено",
  COUNTER_OFFER: "Другие условия",
  MANUAL_REVIEW: "На ручной разбор",
  REJECTED: "Отказ",
  INFO_REQUESTED: "Запрошены данные",
};

/** Что можно запросить у клиента — коды из backend/app/texts.py. */
export const REQUEST_ITEMS: Array<{ code: string; title: string }> = [
  { code: "other_bank_statement", title: "Выписка по счетам в других банках" },
  { code: "financial_statements", title: "Бухгалтерская отчётность за последний год" },
  { code: "collateral", title: "Вид и стоимость залога" },
  { code: "other", title: "Другой документ" },
];

/** Причины отказа специалиста. Код уходит в решение, текст — клиенту. */
export const REJECT_REASONS: Array<{ code: string; title: string }> = [
  { code: "UW01_RISK", title: "Риск выше приемлемого" },
  { code: "UW02_DOCUMENTS", title: "Документы не подтверждают данные анкеты" },
  { code: "UW03_COLLATERAL", title: "Залог не подходит или оценён ниже" },
  { code: "UW04_BUSINESS_MODEL", title: "Непрозрачная деятельность компании" },
  { code: "UW05_OTHER", title: "Другая причина" },
];
