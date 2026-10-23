import { useEffect, useRef, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { RegistryCompany } from "../api/types";
import { Text } from "../ui/primitives";
import { date } from "../lib/format";

const SECONDARY = "var(--color-light-text-secondary)";

/** Тестовые ИНН из мока реестра — чтобы на демо не искать их в README. */
const DEMO = [
  { inn: "7701123451", name: "ООО «Северный ветер»", hint: "должно одобрить" },
  { inn: "7802543212", name: "ООО «Пекарня Колосок»", hint: "другие условия" },
  { inn: "540612345667", name: "ИП Смирнова Анна", hint: "ручная проверка" },
  { inn: "5403987653", name: "ООО «Быстрый старт»", hint: "отказ" },
  { inn: "7711234560", name: "ООО «Закат»", hint: "ликвидация" },
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
                  {found.registered_at && ` · с ${date(found.registered_at)}`}
                </Text>
                {found.status !== "active" && (
                  <Text
                    view="secondary-medium"
                    color="var(--color-light-text-negative)"
                    style={{ marginTop: 6 }}
                  >
                    Статус в реестре: {found.status}
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
              <Text view="secondary-medium" color={SECONDARY} style={{ marginBottom: 8 }}>
                Тестовые компании
              </Text>
              <div style={{ display: "grid", gap: 6 }}>
                {DEMO.map((d) => (
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
          Ролей и паролей на бэкенде пока нет, экран наполняется. Пускаем сразу — функциональность
          обсуждаем отдельно.
        </Text>
      </div>

      <Button view="accent" size={56} block className="mo-press" onClick={onEnter}>
        Открыть рабочее место
      </Button>
    </>
  );
}
