import { useEffect, useState } from "react";

type Health = Record<string, string>;

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main style={{ fontFamily: "Arial, sans-serif", padding: 32 }}>
      <h1>Умный кредитный кабинет</h1>
      <p>Каркас запущен. Состояние сервисов:</p>
      {error && <p style={{ color: "crimson" }}>Бэкенд недоступен: {error}</p>}
      {health && (
        <ul>
          {Object.entries(health).map(([k, v]) => (
            <li key={k}>
              {k}: <b>{v}</b>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
