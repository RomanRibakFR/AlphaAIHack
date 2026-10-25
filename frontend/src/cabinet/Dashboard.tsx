import { useEffect, useMemo, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { ApplicationListItem, RegistryCompany } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal, Stagger } from "../ui/Reveal";
import { date, dateTime, duration, money, months } from "../lib/format";
import { businessAgeMonths, isActive, statusLabel } from "./precheck";
import { NEXT_STEP, STATUS_TONE, TABS } from "./content";
import NewsFeed from "./components/NewsFeed";
import SupportChat from "../chat/SupportChat";

const SECONDARY = "var(--color-light-text-secondary)";

function CompanyCard({ company }: { company: RegistryCompany }) {
  const age = businessAgeMonths(company.registered_at);

  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        {company.name}
      </Text>
      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
        {company.kind === "ul" ? "Юридическое лицо" : "Индивидуальный предприниматель"}
      </Text>

      <div className="cb-pairs" style={{ marginTop: 20 }}>
        <div className="cb-pair">
          <span>ИНН</span>
          <span>{company.inn}</span>
        </div>
        {company.okved_name && (
          <div className="cb-pair">
            {/* короткая подпись оставляет больше места значению: название
                отрасли длинное и иначе рвётся на четыре строки */}
            <span>ОКВЭД</span>
            <span>{company.okved_name}</span>
          </div>
        )}
        <div className="cb-pair">
          <span>В реестре с</span>
          <span>
            {date(company.registered_at)}
            {age !== null && ` · ${duration(age)}`}
          </span>
        </div>
        <div className="cb-pair">
          <span>Статус</span>
          <span style={{ color: isActive(company) ? undefined : "var(--color-light-text-negative)" }}>
            {statusLabel(company.status)}
          </span>
        </div>
      </div>

      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 16 }}>
        Данные подтянуты из реестра по ИНН. Вводить их в заявке не нужно.
      </Text>
    </section>
  );
}

/** Кабинет: карточка компании и список заявок. */
export default function Dashboard({ inn }: { inn: string }) {
  const navigate = useNavigate();
  const [company, setCompany] = useState<RegistryCompany | null>(null);
  const [apps, setApps] = useState<ApplicationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // открываем «Все заявки» — первую вкладку
  const [activeTab, setTab] = useState(TABS[0].id);

  const visible = useMemo(() => {
    if (apps === null) return [];
    const rule = TABS.find((t) => t.id === activeTab) ?? TABS[TABS.length - 1];
    return apps.filter((a) => rule.match(a.status.code));
  }, [apps, activeTab]);

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

  if (error) {
    return (
      <div className="cb-empty">
        <Text view="primary-medium" color="var(--color-light-text-negative)">
          {error}
        </Text>
      </div>
    );
  }

  if (apps === null || company === null) {
    return (
      <div className="lp-skeleton mo-shimmer" style={{ minHeight: 320, borderRadius: 32 }} />
    );
  }

  return (
    <>
      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              Заявки
            </Text>
            <Text view="primary-medium" color={SECONDARY} style={{ marginTop: 8 }}>
              Здесь видно, на каком шаге каждая заявка и что делать дальше.
            </Text>
          </div>
          <Button view="accent" size={56} className="mo-press" onClick={() => navigate("/new")}>
            Подать заявку
          </Button>
        </div>
      </Reveal>

      <div className="cb-grid-2">
        <div>
          {apps.length === 0 ? (
            <Reveal>
              <div className="cb-empty">
                <Text view="accent-primary-large">Заявок пока нет</Text>
                <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
                  Подбор занимает пару минут: ответьте, на что нужны деньги, и мы предложим
                  подходящий кредит.
                </Text>
                <Button
                  view="primary"
                  size={48}
                  className="mo-press"
                  style={{ marginTop: 20 }}
                  onClick={() => navigate("/new")}
                >
                  Подобрать кредит
                </Button>
              </div>
            </Reveal>
          ) : (
            <>
              <div className="cb-tabs" role="tablist" aria-label="Группы заявок">
                {TABS.map((t) => {
                  const count = apps.filter((a) => t.match(a.status.code)).length;
                  return (
                    <button
                      key={t.id}
                      role="tab"
                      aria-selected={t.id === activeTab}
                      className="cb-tab mo-press"
                      onClick={() => setTab(t.id)}
                    >
                      {t.label}
                      <span className="cb-tab-count" data-zero={count === 0}>
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {visible.length === 0 ? (
                <div className="cb-empty">
                  <Text view="primary-medium" color={SECONDARY}>
                    В этой группе заявок нет.
                  </Text>
                </div>
              ) : (
                <Stagger className="cb-rows" step={60}>
                  {visible.map((a) => (
                    <Link key={a.id} to={`/application/${a.id}`} className="cb-row">
                      <div>
                        <Text view="accent-primary-medium">{a.product.name}</Text>
                        <Text view="secondary-medium" color={SECONDARY}>
                          № {a.id} · изменена {dateTime(a.updated_at)}
                        </Text>
                      </div>

                      <div className="cb-row-amount">
                        <Text view="accent-primary-medium">
                          {a.amount === null ? "Не заполнена" : money(a.amount)}
                        </Text>
                        {a.term_months !== null && (
                          <Text view="secondary-medium" color={SECONDARY}>
                            {months(a.term_months)}
                          </Text>
                        )}
                      </div>

                      <div className="cb-row-state">
                        <span className="cb-chip" data-tone={STATUS_TONE[a.status.code]}>
                          {a.status.title}
                        </span>
                        {NEXT_STEP[a.status.code] && (
                          <Text view="secondary-medium" color={SECONDARY}>
                            {NEXT_STEP[a.status.code]}
                          </Text>
                        )}
                      </div>

                      <span className="cb-row-chevron" aria-hidden="true">
                        <svg width="8" height="14" viewBox="0 0 8 14" fill="none">
                          <path
                            d="M1 1l6 6-6 6"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                    </Link>
                  ))}
                </Stagger>
              )}
            </>
          )}
        </div>

        <div style={{ display: "grid", gap: 24 }}>
          <Reveal delay={80}>
            <CompanyCard company={company} />
          </Reveal>
          {/* Поддержка выше новостей: это то, ради чего сюда возвращаются,
              а лента — фон. */}
          <Reveal delay={140}>
            <SupportChat inn={inn} />
          </Reveal>
          <Reveal delay={200}>
            <NewsFeed okvedName={company.okved_name} />
          </Reveal>
        </div>
      </div>
    </>
  );
}
