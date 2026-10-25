import type {
  Application,
  ApplicationListItem,
  BackofficeApplication,
  ChatSummary,
  ChatThread,
  FieldProblem,
  Product,
  QueueItem,
  RegistryCompany,
  StatusCode,
  UnderwriterDecision,
} from "./types";

/**
 * Ошибка от бэкенда в удобном для экранов виде.
 * problems заполнен только у 422 от /submit — там бэкенд говорит, какие поля подсветить.
 */
export class ApiError extends Error {
  status: number;
  problems: FieldProblem[];

  constructor(status: number, message: string, problems: FieldProblem[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problems = problems;
  }
}

/** detail у FastAPI бывает строкой, объектом с problems или списком ошибок валидации. */
function parseError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string") return new ApiError(status, detail);

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { message?: string; problems?: FieldProblem[] };
    return new ApiError(status, d.message ?? `Ошибка ${status}`, d.problems ?? []);
  }

  // Стандартный 422 от pydantic: [{loc, msg, type}, ...]
  if (Array.isArray(detail)) {
    const problems = detail.map((e: { loc?: unknown[]; msg?: string }) => ({
      field: String(e.loc?.[e.loc.length - 1] ?? ""),
      message: e.msg ?? "Некорректное значение",
    }));
    return new ApiError(status, "Проверьте заполненные поля", problems);
  }

  return new ApiError(status, `Ошибка ${status}`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // У multipart заголовок ставит браузер: в нём граница частей, её не угадать.
  const json = init?.body !== undefined && !(init.body instanceof FormData);
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: json ? { "Content-Type": "application/json" } : undefined,
    });
  } catch {
    // сеть/бэкенд лежит — до HTTP-кода дело не дошло
    throw new ApiError(0, "Не удалось связаться с сервером");
  }

  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) throw parseError(response.status, body);
  return body as T;
}

export const api = {
  health: () => request<Record<string, string>>("/health"),

  products: () => request<Product[]>("/products"),

  lookupCompany: (inn: string) =>
    request<RegistryCompany>(`/companies/lookup?inn=${encodeURIComponent(inn)}`),

  applications: (inn: string) =>
    request<ApplicationListItem[]>(`/applications?inn=${encodeURIComponent(inn)}`),

  application: (id: number) => request<Application>(`/applications/${id}`),

  createApplication: (body: { inn: string; product_code: string; purpose?: string }) =>
    request<Application>("/applications", { method: "POST", body: JSON.stringify(body) }),

  /** Автосохранение черновика: присылаем только изменённые поля. */
  updateApplication: (
    id: number,
    patch: {
      product_code?: string;
      amount?: string | null;
      term_months?: number | null;
      purpose?: string;
      annual_revenue?: string | null;
      collateral_type?: string | null;
      collateral_description?: string | null;
      collateral_value?: string | null;
    },
  ) => request<Application>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  submit: (id: number) => request<Application>(`/applications/${id}/submit`, { method: "POST" }),

  /** Отозвать заявку. Раньше ручка называлась withdraw. */
  cancel: (id: number) => request<Application>(`/applications/${id}/cancel`, { method: "POST" }),

  /**
   * Принять предложение. alternative — номер варианта из offer.alternatives,
   * без него принимаются основные условия.
   */
  accept: (id: number, alternative?: number) =>
    request<Application>(`/applications/${id}/accept`, {
      method: "POST",
      body: JSON.stringify(alternative === undefined ? {} : { alternative }),
    }),

  decline: (id: number) => request<Application>(`/applications/${id}/decline`, { method: "POST" }),

  sign: (id: number, code: string) =>
    request<Application>(`/applications/${id}/sign`, {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  provideInfo: (id: number) =>
    request<Application>(`/applications/${id}/provide-info`, { method: "POST" }),

  /**
   * Загрузить документ. Для выписки из другого банка бэкенд дополнительно
   * просит сумму поступлений по ней — по ней он сверяет выручку из анкеты.
   */
  uploadDocument: (
    id: number,
    docType: string,
    file: File,
    declared?: { turnover: number; months: number },
  ) => {
    const form = new FormData();
    form.append("doc_type", docType);
    form.append("file", file);
    if (declared) {
      form.append("declared_turnover", String(declared.turnover));
      form.append("declared_months", String(declared.months));
    }
    return request<Application>(`/applications/${id}/documents`, { method: "POST", body: form });
  },

  /** Чат с поддержкой. Привязан к компании по ИНН, а не к заявке. */
  chat: {
    thread: (inn: string) => request<ChatThread>(`/chat?inn=${encodeURIComponent(inn)}`),

    send: (inn: string, text: string) =>
      request<ChatThread>(`/chat?inn=${encodeURIComponent(inn)}`, {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
  },

  /** Рабочее место сотрудника банка. */
  backoffice: {
    /** Очередь заявок. Без статуса — те, что ждут специалиста. */
    queue: (status?: StatusCode) =>
      request<QueueItem[]>(
        `/backoffice/applications${status ? `?status=${encodeURIComponent(status)}` : ""}`,
      ),

    application: (id: number) => request<BackofficeApplication>(`/backoffice/applications/${id}`),

    decide: (id: number, body: UnderwriterDecision) =>
      request<BackofficeApplication>(`/backoffice/applications/${id}/decision`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    /** Диалоги с клиентами: сначала те, где ждут ответа. */
    chats: () => request<ChatSummary[]>("/backoffice/chats"),

    chat: (inn: string) => request<ChatThread>(`/backoffice/chats/${encodeURIComponent(inn)}`),

    reply: (inn: string, text: string) =>
      request<ChatThread>(`/backoffice/chats/${encodeURIComponent(inn)}`, {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
  },
};
