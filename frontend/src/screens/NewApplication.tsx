import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { Product } from "../api/types";
import { money, rate } from "../lib/format";

/** Выбор продукта. Создаёт черновик и уводит в карточку заявки. */
export default function NewApplication({ inn }: { inn: string }) {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api
      .products()
      .then(setProducts)
      .catch((e) => setError((e as ApiError).message));
  }, []);

  async function choose(code: string) {
    setBusy(code);
    setError(null);
    try {
      const app = await api.createApplication({ inn, product_code: code });
      navigate(`/application/${app.id}`);
    } catch (e) {
      setError((e as ApiError).message);
      setBusy(null);
    }
  }

  if (error && products === null) return <p className="field-error">{error}</p>;
  if (products === null) return <p>Загружаем каталог…</p>;

  return (
    <>
      <section>
        <h2>Какой кредит нужен</h2>
        <p className="muted">
          Шаг «определить потребность» из кейса. Здесь должны быть подсказки для тех, кто не
          разбирается в банковских продуктах — пока только сухие параметры.
        </p>
      </section>

      {products.map((p) => (
        <section key={p.code}>
          <h3>{p.name}</h3>
          <p>{p.description}</p>
          <table>
            <tbody>
              <tr>
                <th>Сумма</th>
                <td>
                  {money(p.min_amount)} — {money(p.max_amount)}
                </td>
              </tr>
              <tr>
                <th>Срок</th>
                <td>
                  {p.min_term_months}—{p.max_term_months} мес.
                </td>
              </tr>
              <tr>
                <th>Ставка</th>
                <td>{rate(p.base_rate)}</td>
              </tr>
              <tr>
                <th>Залог</th>
                <td>{p.requires_collateral ? "нужен" : "не нужен"}</td>
              </tr>
              <tr>
                <th>Бизнесу должно быть</th>
                <td>от {p.min_business_age_months} мес.</td>
              </tr>
            </tbody>
          </table>
          <p>
            <button onClick={() => choose(p.code)} disabled={busy !== null}>
              {busy === p.code ? "Создаём…" : "Выбрать и заполнить заявку"}
            </button>
          </p>
        </section>
      ))}

      {error && <p className="field-error">{error}</p>}
    </>
  );
}
