import { useEffect, useRef, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { RegistryCompany } from "../api/types";
import { Text } from "../ui/primitives";
import { date, duration } from "../lib/format";
import { businessAgeMonths, isActive, statusLabel } from "../cabinet/precheck";

const SECONDARY = "var(--color-light-text-secondary)";

/**
 * Тестовые компании мок-сервиса — чтобы на демо не искать их в README.
 *
 * Все семнадцать сценариев из `mocks/companies/`, по исходам: проверяющему
 * нужна конкретная ветка, а не перебор ИНН подряд. Что вводить в анкету
 * под каждую компанию — в `docs/mocks-format.md`.
 */
const DEMO: Array<{ title: string; rows: Array<{ inn: string; name: string; hint: string }> }> = [
  {
    title: "Одобрят сразу",
    rows: [
      { inn: "0001000010", name: "ООО «Утренний кофе»", hint: "кофейня" },
      { inn: "000100000244", name: "ИП Кузнецов Д. О.", hint: "торговля" },
    ],
  },
  {
    title: "Предложат другие условия",
    rows: [
      { inn: "0001000035", name: "ООО «Сибирский маршрут»", hint: "срок больше" },
      { inn: "0001000042", name: "ООО «СтройБаза Юг»", hint: "сумма меньше" },
      { inn: "0001000081", name: "ООО «Оптовик Плюс»", hint: "овердрафт меньше" },
    ],
  },
  {
    title: "Попросят выписку",
    rows: [
      { inn: "0001000155", name: "ООО «Продовольственная компания Обь»", hint: "потом одобрят" },
      { inn: "000100001696", name: "ИП Белова О. С.", hint: "потом к специалисту" },
    ],
  },
  {
    title: "Посмотрит специалист",
    rows: [
      { inn: "0001000050", name: "ООО «Мастерская Кедр»", hint: "пограничная оценка" },
      { inn: "0001000067", name: "ООО «Цифровые решения»", hint: "крупная сумма" },
      { inn: "0001000074", name: "ООО «Хлебный дом»", hint: "залог" },
      { inn: "0001000170", name: "ООО «Склад-Сервис»", hint: "бюро не ответило" },
    ],
  },
  {
    title: "Откажут",
    rows: [
      { inn: "0001000099", name: "ООО «Салон Лаванда»", hint: "обороты не позволяют" },
      { inn: "0001000109", name: "ООО «Монолит-Строй»", hint: "высокий риск" },
      { inn: "000100001128", name: "ИП Захаров И. П.", hint: "долг по налогам" },
      { inn: "0001000123", name: "ООО «Ресторан Полёт»", hint: "текущая просрочка" },
      { inn: "0001000130", name: "ООО «Реклама Медиа Групп»", hint: "ликвидация" },
      { inn: "0001000148", name: "ООО «Маркетплейс-Старт»", hint: "бизнесу 7 месяцев" },
    ],
  },
];

type Props = {
  mode: "client" | "staff";
  onSignIn: (inn: string) => void;
};

/**
 * Окно входа поверх лендинга.
 *
 * Своего адреса у него два — /login и /staff, — поэтому ссылку на вход
 * можно дать напрямую, а закрытие просто возвращает на главную.
 *
 * Настоящей авторизации на бэкенде нет: компания определяется по ИНН,
 * им же бэкенд ищет заявки.
 */
export default function AuthModal({ mode, onSignIn }: Props) {
  const navigate = useNavigate();
  const close = () => navigate("/");

  const [inn, setInn] = useState("");
  const [found, setFound] = useState<RegistryCompany | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Esc закрывает, фон под окном не прокручивается
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function check(value: string) {
    const trimmed = value.trim();
    if (trimmed === "") return;
    setBusy(true);
    setError(null);
    setFound(null);
    try {
      setFound(await api.lookupCompany(trimmed));
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="lp-backdrop mo-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={mode === "staff" ? "Вход для сотрудника" : "Вход в кредитный кабинет"}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="lp-dialog mo-dialog">
        <button className="lp-dialog-close" onClick={close} aria-label="Закрыть">
          ✕
        </button>

        {mode === "staff" ? (
          <StaffBody onEnter={() => navigate("/underwriter")} />
        ) : (
          <>
            <Text view="promo-card" tag="h2">
              Вход в кредитный кабинет
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Введите ИНН компании или ИП. Пароля пока нет: это прототип, вход сделан по ИНН.
            </Text>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                void check(inn);
              }}
              style={{ marginTop: 24 }}
            >
              <Input
                ref={inputRef}
                label="ИНН"
                placeholder="10 или 12 цифр"
                value={inn}
                onChange={(_, { value }) => setInn(value)}
                error={error ?? undefined}
                block
              />
              <Button
                type="submit"
                view="accent"
                size={56}
                block
                loading={busy}
                className="mo-press"
                style={{ marginTop: 16 }}
              >
                Продолжить
              </Button>
            </form>

            {found && (
              <div className="lp-found mo-dialog">
                <Text view="accent-primary-medium">{found.name}</Text>
                <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
                  {found.kind === "ul" ? "Юридическое лицо" : "Индивидуальный предприниматель"}
                  {found.okved_name && ` · ${found.okved_name}`}
                </Text>
                {found.registered_at && (
                  <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
                    В реестре с {date(found.registered_at)}
                    {(() => {
                      const age = businessAgeMonths(found.registered_at);
                      return age === null ? "" : ` · бизнес работает ${duration(age)}`;
                    })()}
                  </Text>
                )}
                {!isActive(found) && (
                  <Text
                    view="secondary-medium"
                    color="var(--color-light-text-negative)"
                    style={{ marginTop: 6 }}
                  >
                    Статус в реестре: {statusLabel(found.status)}
                  </Text>
                )}
                <Button
                  view="primary"
                  size={48}
                  block
                  className="mo-press"
                  style={{ marginTop: 16 }}
                  onClick={() => onSignIn(found.inn)}
                >
                  Войти
                </Button>
              </div>
            )}

            <div style={{ marginTop: 24 }}>
              <Text view="secondary-medium" color={SECONDARY}>
                Тестовые компании
              </Text>
              {DEMO.map((group) => (
                <div key={group.title} style={{ marginTop: 16 }}>
                  <Text view="secondary-small" color={SECONDARY} className="lp-demo-group">
                    {group.title}
                  </Text>
                  <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
                    {group.rows.map((d) => (
                      <button
                        key={d.inn}
                        className="lp-demo-row"
                        onClick={() => {
                          setInn(d.inn);
                          void check(d.inn);
                        }}
                      >
                        <span>
                          <span style={{ fontWeight: 500 }}>{d.name}</span>
                          <span style={{ color: SECONDARY }}> · {d.hint}</span>
                        </span>
                        <code style={{ color: SECONDARY, fontSize: 12 }}>{d.inn}</code>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StaffBody({ onEnter }: { onEnter: () => void }) {
  return (
    <>
      <Text view="promo-card" tag="h2">
        Вход для сотрудника
      </Text>
      <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
        Рабочее место кредитного специалиста: очередь заявок на ручной разбор и принятие решения.
      </Text>

      <div className="lp-staff-note">
        <Text view="secondary-medium">
          Ролей и паролей на бэкенде нет: это прототип, вход свободный. В рабочем месте видно
          очередь заявок, разбор оценки и решение специалиста.
        </Text>
      </div>

      <Button view="accent" size={56} block className="mo-press" onClick={onEnter}>
        Открыть рабочее место
      </Button>
    </>
  );
}
