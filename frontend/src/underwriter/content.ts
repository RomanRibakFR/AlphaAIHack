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
  M6_MODEL_UNAVAILABLE: "Модель оценки риска недоступна",
  M7_REVIEWED_BEFORE: "Заявку уже рассматривал специалист",
};

/** Признаки модели — названия и единицы из docs/decision-policy.md. */
export const FEATURES: Array<{
  key: string;
  contribution: string;
  title: string;
  hint: string;
  format: "months" | "money" | "share" | "ratio" | "count";
}> = [
  {
    key: "F1_business_age_months",
    contribution: "F1",
    title: "Срок ведения бизнеса",
    hint: "месяцев с даты регистрации · ЕГРЮЛ",
    format: "months",
  },
  {
    key: "F2_avg_monthly_turnover",
    contribution: "F2",
    title: "Обороты по счёту",
    hint: "среднемесячные поступления за 12 мес. · банк",
    format: "money",
  },
  {
    key: "F3_turnover_cv",
    contribution: "F3",
    title: "Стабильность оборотов",
    hint: "коэффициент вариации, больше — неровнее · банк",
    format: "ratio",
  },
  {
    key: "F4_debt_load",
    contribution: "F4",
    title: "Долговая нагрузка",
    hint: "платежи по кредитам к обороту · БКИ",
    format: "share",
  },
  {
    key: "F5_overdue_30plus_count_24m",
    contribution: "F5",
    title: "Прошлые просрочки",
    hint: "случаев 30+ дней за 24 мес. · БКИ",
    format: "count",
  },
  {
    key: "F6_amount_to_turnover",
    contribution: "F6",
    title: "Сумма к оборотам",
    hint: "запрошенная сумма к среднемесячному обороту",
    format: "ratio",
  },
];

/** Внешние источники — как их называют люди. */
export const SOURCES: Record<string, string> = {
  egrul: "ЕГРЮЛ / ЕГРИП",
  fns: "ФНС",
  zsk: "ЗСК (115-ФЗ)",
  bki: "Бюро кредитных историй",
  bank: "Данные банка",
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
  payment_capacity: "платёжеспособность",
  turnover_cap: "потолок к оборотам",
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
