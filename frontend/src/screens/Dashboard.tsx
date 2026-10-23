import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import NewsFeed from "../components/NewsFeed";
import { ApiError, api } from "../api/client";
import type { ApplicationListItem, RegistryCompany } from "../api/types";
import { dateTime, money, months } from "../lib/format";

/** Кабинет: кто мы, какие заявки есть, кнопка новой заявки, лента. */
export default function Dashboard({ inn }: { inn: string }) {
  const [company, setCompany] = useState<RegistryCompany | null>(null);
  const [apps, setApps] = useState<ApplicationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.lookupCompany(inn), api.applications(inn)])
      .then(([c, a]) => {
        if (!alive) return;
        setCompany(c);
        setApps(a);
      })
      .catch((e) => alive && setError((e as ApiError).message));
    return () => {
      alive = false;
    };
  }, [inn]);

  if (error) return <p className="field-error">{error}</p>;
  if (apps === null) return <p>Загружаем…</p>;

  return (
    <>
      <section>
        <h2>{company?.name ?? inn}</h2>
        <p className="muted">
          ИНН {inn}
          {company?.okved_name && ` · ${company.okved_name}`}
          {company?.status && company.status !== "active" && (
            <>
              {" · "}
              <b className="field-error">статус в реестре: {company.status}</b>
            </>
          )}
        </p>
        <p>
          <Link to="/new">
            <button>Новая заявка</button>
          </Link>
        </p>
      </section>

      <section>
        <h3>Мои заявки</h3>
        {apps.length === 0 ? (
          <p className="muted">Заявок пока нет.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>№</th>
                <th>Продукт</th>
                <th>Сумма</th>
                <th>Срок</th>
                <th>Статус</th>
                <th>Изменена</th>
              </tr>
            </thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/application/${a.id}`}>{a.id}</Link>
                  </td>
                  <td>{a.product.name}</td>
                  <td>{money(a.amount)}</td>
                  <td>{months(a.term_months)}</td>
                  <td>{a.status.title}</td>
                  <td>{dateTime(a.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <NewsFeed okvedName={company?.okved_name} statusTitle={apps[0]?.status.title} />
    </>
  );
}
