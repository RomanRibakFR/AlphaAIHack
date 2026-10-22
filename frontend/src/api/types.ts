// Типы ответов бэкенда. Руками с /api/openapi.json — если контракт поменяется, править здесь.
//
// Важно: деньги и ставки приходят СТРОКАМИ ("2000000.00"), а не числами —
// pydantic так сериализует Decimal. Считать и форматировать на нашей стороне,
// см. lib/money.ts.

/** Все 15 состояний заявки. Для логики — это, для показа — StatusView.title. */
export type StatusCode =
  | "draft"
  | "submitted"
  | "validation"
  | "needs_info"
  | "external_checks"
  | "scoring"
  | "manual_review"
  | "approved"
  | "counter_offer"
  | "signing"
  | "issued"
  | "rejected"
  | "declined_by_client"
  | "withdrawn"
  | "expired";

export type Actor = "client" | "system" | "underwriter";

/** Что бэкенд разрешает нажать прямо сейчас. Рендерим кнопки по этому списку. */
export type ActionCode = "edit" | "submit" | "withdraw" | "accept" | "decline" | "sign";

export type Product = {
  code: string;
  name: string;
  description: string;
  min_amount: string;
  max_amount: string;
  min_term_months: number;
  max_term_months: number;
  base_rate: string;
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

/** Внутренние шаги банка склеены: submitted/validation/external_checks дают один title. */
export type StatusView = { code: StatusCode; title: string; hint: string };

export type HistoryItem = {
  from_status: StatusCode | null;
  to_status: StatusCode;
  actor: Actor;
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
  estimated_payment: string | null;
  available_actions: ActionCode[];
  history: HistoryItem[];
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
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
