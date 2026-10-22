import type {
  Application,
  ApplicationListItem,
  FieldProblem,
  Product,
  RegistryCompany,
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
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
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
    },
  ) => request<Application>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  submit: (id: number) => request<Application>(`/applications/${id}/submit`, { method: "POST" }),

  withdraw: (id: number) => request<Application>(`/applications/${id}/withdraw`, { method: "POST" }),

  // ── Ручек ниже на бэкенде ПОКА НЕТ (есть только в available_actions). ──
  // Как появятся — раскомментировать и убрать заглушку в components/Actions.tsx.
  // accept:  (id: number) => request<Application>(`/applications/${id}/accept`,  { method: "POST" }),
  // decline: (id: number) => request<Application>(`/applications/${id}/decline`, { method: "POST" }),
  // sign:    (id: number) => request<Application>(`/applications/${id}/sign`,    { method: "POST" }),
};
