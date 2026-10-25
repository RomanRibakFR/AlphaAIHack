// Типы ответов бэкенда. Руками с /api/openapi.json — если контракт поменяется, править здесь.
//
// Важно: деньги и ставки приходят СТРОКАМИ ("2000000.00"), а не числами —
// pydantic так сериализует Decimal. Считать и форматировать на нашей стороне,
// см. lib/money.ts.

/**
 * Все 13 состояний заявки — ровно как в backend/app/statuses.py.
 * Для логики — это, для показа — StatusView.title.
 */
export type StatusCode =
  | "draft"
  | "submitted"
  | "validation"
  | "info_requested"
  | "checks"
  | "scoring"
  | "manual_review"
  | "offer_proposed"
  | "signing"
  | "issued"
  | "rejected"
  | "cancelled"
  | "expired";

export type Actor = "client" | "system" | "underwriter" | "timer";

/** Что бэкенд разрешает нажать прямо сейчас. Рендерим кнопки по этому списку. */
export type ActionCode =
  | "edit"
  | "submit"
  | "cancel"
  | "accept"
  | "decline"
  | "sign"
  | "provide_info"
  | "upload_document";

export type Product = {
  code: string;
  name: string;
  description: string;
  min_amount: string;
  max_amount: string;
  min_term_months: number;
  max_term_months: number;
  base_rate: string;
  /** Потолок ставки продукта, % годовых. Вместе с base_rate даёт диапазон. */
  max_rate: string;
  requires_collateral: boolean;
  min_business_age_months: number;
};

export type RegistryCompany = {
  inn: string;
  ogrn: string | null;
  kind: "ul" | "ip";
  name: string;
  okved: string | null;
  okved_name: string | null;
  registered_at: string | null;
  status: string;
  address: string | null;
  director: string | null;
};

/** Внутренние шаги банка склеены: submitted/validation/checks дают один title. */
export type StatusView = { code: StatusCode; title: string; hint: string };

/** Подшаги рассмотрения — приходят с сервера, свои больше не выдумываем. */
export type ReviewStep = {
  code: string;
  title: string;
  state: "done" | "current" | "pending";
};

/** Вариант условий, который банк предлагает вместо основного. */
export type OfferVariant = {
  amount: string;
  term_months: number;
  monthly_payment: string;
};

/** Решение банка: что именно он готов выдать и на каких условиях. */
export type Offer = {
  /** AS_REQUESTED — как просили, COUNTER — на других условиях. */
  type: "AS_REQUESTED" | "COUNTER";
  /** Чем отличается от запроса: TERM_EXTENDED, AMOUNT_REDUCED и т. п. */
  counter_kind: string | null;
  amount: string;
  term_months: number;
  requested_amount: string;
  requested_term_months: number;
  rate: string;
  monthly_payment: string;
  total_payment: string;
  alternatives: OfferVariant[];
  conditions: string[];
  chosen_alternative: number | null;
  valid_until: string;
  reason: string;
  advice: string;
  text: string;
};

export type Rejection = { reason: string; advice: string; text: string };

/** Строка графика платежей. */
export type Payment = {
  n: number;
  date: string;
  payment: string;
  principal: string;
  interest: string;
  balance: string;
};

export type RequestItem = {
  kind: "document" | "field";
  code: string;
  title: string;
  message: string;
};

export type InfoRequest = {
  id: number;
  reason_code: string;
  items: RequestItem[];
  created_at: string;
};

export type Document = {
  id: number;
  doc_type: string;
  filename: string;
  size: number;
  uploaded_at: string;
};

export type HistoryItem = {
  transition_id: string;
  from_status: StatusCode | null;
  to_status: StatusCode;
  actor: Actor;
  reason_code: string | null;
  comment: string | null;
  created_at: string;
};

export type Application = {
  id: number;
  status: StatusView;
  company: { inn: string; name: string; kind: string };
  product: { code: string; name: string };
  amount: string | null;
  term_months: number | null;
  purpose: string;
  annual_revenue: string | null;
  collateral_type: string | null;
  collateral_description: string | null;
  collateral_value: string | null;
  estimated_payment: string | null;
  available_actions: ActionCode[];
  review_steps: ReviewStep[] | null;
  info_requests: InfoRequest[];
  documents: Document[];
  offer: Offer | null;
  rejection: Rejection | null;
  /** В настоящем банке пришёл бы в SMS — по условиям кейса показываем в кабинете. */
  sign_code: string | null;
  contract_number: string | null;
  schedule: Payment[] | null;
  /** До какого числа банк ждёт ответа клиента. */
  deadline_at: string | null;
  history: HistoryItem[];
  /** Защита от одновременного редактирования: растёт с каждым изменением. */
  version: number;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  issued_at: string | null;
};

export type ApplicationListItem = {
  id: number;
  status: StatusView;
  product: { code: string; name: string };
  amount: string | null;
  term_months: number | null;
  updated_at: string;
};

/** Ошибка валидации при отправке: какое поле подсветить и что написать. */
export type FieldProblem = { field: string; message: string };

// ———————————— рабочее место сотрудника банка ————————————

/** Строка очереди на ручной разбор. triggers уже человеческие. */
export type QueueItem = {
  id: number;
  company: { inn: string; name: string; kind: string };
  product: { code: string; name: string };
  amount: string | null;
  term_months: number | null;
  status: StatusCode;
  pd: string | null;
  grade: string | null;
  triggers: string[];
  submitted_at: string | null;
};

/** Ответ одного внешнего источника: налоговая, БКИ, реестр и так далее. */
export type Check = {
  source: string;
  status: string;
  attempts: number;
  response: Record<string, unknown> | null;
  error: string | null;
  started_at: string;
  finished_at: string;
};

/** Что предлагает система, если специалист согласен. */
export type Recommendation = {
  kind: string;
  amount: number;
  term_months: number;
  rate: number;
  monthly_payment: number;
  alternatives: Array<{ amount: number; term_months: number; monthly_payment: number }>;
  conditions: string[];
  reason: string;
  advice: string;
};

/** Запись решения: системного или принятого специалистом. */
export type Decision = {
  outcome: string;
  policy_version: string;
  model_version: string | null;
  pd: string | null;
  grade: string | null;
  /** Значения признаков F1…F6, по которым считалась оценка. */
  features: Record<string, number>;
  /** Вклад каждого признака в оценку: плюс повышает риск, минус понижает. */
  contributions: Record<string, number>;
  stop_factors: Array<Record<string, unknown>>;
  manual_triggers: string[];
  reason_codes: string[];
  max_amount: string | null;
  limit_binding: string | null;
  recommendation: Recommendation | null;
  reason: string;
  advice: string;
  decided_by: Actor;
  comment: string | null;
  created_at: string;
};

export type BackofficeApplication = {
  application: Application;
  checks: Check[];
  decisions: Decision[];
};

/** Решение специалиста. Комментарий обязателен во всех трёх случаях. */
export type UnderwriterDecision = {
  action: "approve" | "reject" | "request_info";
  comment: string;
  amount?: string;
  term_months?: number;
  rate?: string;
  reason_code?: string;
  reason?: string;
  advice?: string;
  items?: string[];
  message?: string;
};

// ———————————— чат с поддержкой ————————————

export type ChatAuthor = "client" | "support";

export type ChatMessage = {
  id: number;
  author: ChatAuthor;
  text: string;
  created_at: string;
};

export type ChatThread = {
  inn: string;
  company_name: string;
  messages: ChatMessage[];
  /** Сколько сообщений другой стороны ещё не прочитано. */
  unread: number;
};

/** Строка списка диалогов в рабочем месте сотрудника. */
export type ChatSummary = {
  inn: string;
  company_name: string;
  last_text: string;
  last_author: ChatAuthor;
  last_at: string;
  unread: number;
};
