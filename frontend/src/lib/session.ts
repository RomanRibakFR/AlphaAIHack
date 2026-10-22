// Заглушка авторизации: вместо логина держим ИНН компании.
// Бэкенд ищет заявки по ИНН, настоящего входа пока нет.
// Когда появится авторизация — менять только здесь.

const KEY = "credit-cabinet:inn";

export function currentInn(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function signIn(inn: string): void {
  try {
    localStorage.setItem(KEY, inn);
  } catch {
    // приватный режим — переживём, просто не запомним
  }
}

export function signOut(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
