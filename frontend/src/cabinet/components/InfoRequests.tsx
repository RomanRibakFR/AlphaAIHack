import { useRef, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { ApiError, api } from "../../api/client";
import type { Application, FieldProblem, RequestItem } from "../../api/types";
import { Text } from "../../ui/primitives";
import { dateTime, money } from "../../lib/format";

const SECONDARY = "var(--color-light-text-secondary)";
const MAX_FILE_MB = 10;

/** Выписку бэкенд принимает только вместе с суммой поступлений по ней. */
const STATEMENT = "other_bank_statement";

/**
 * Что банк просит дополнить.
 *
 * По исследованию дозапрос — место, где заявки теряются: человек не понимает,
 * что именно от него хотят, и бросает. Поэтому каждый пункт показан отдельной
 * карточкой со словами банка, а рядом — ровно то действие, которое закрывает
 * этот пункт.
 */
export default function InfoRequests({
  app,
  problems,
  onUpdated,
}: {
  app: Application;
  problems: FieldProblem[];
  onUpdated: (updated: Application) => void;
}) {
  if (app.info_requests.length === 0) return null;

  // пункты всех открытых запросов подряд: клиенту неважно, каким решением они заведены
  const items = app.info_requests.flatMap((r) => r.items);
  const asked = app.info_requests[0];

  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        Что нужно дополнить
      </Text>
      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 8 }}>
        Запрошено {dateTime(asked.created_at)}. Заявка не начнётся заново — она продолжится
        с того же места.
      </Text>

      {/* Чего не хватило при попытке отправить — бэкенд называет это поимённо. */}
      {problems.length > 0 && (
        <ul className="cb-list cb-missing" style={{ marginTop: 16 }}>
          {problems.map((p) => (
            <li key={`${p.field}-${p.message}`}>{p.message}</li>
          ))}
        </ul>
      )}

      <div style={{ marginTop: 20, display: "grid", gap: 12 }}>
        {items.map((item) => (
          <RequestCard key={item.code} app={app} item={item} onUpdated={onUpdated} />
        ))}
      </div>

      {app.documents.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Уже загружено
          </Text>
          <ul className="cb-list" style={{ marginTop: 8 }}>
            {app.documents.map((d) => (
              <li key={d.id}>
                {d.filename} · {Math.max(1, Math.round(d.size / 1024))} КБ · {dateTime(d.uploaded_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function RequestCard({
  app,
  item,
  onUpdated,
}: {
  app: Application;
  item: RequestItem;
  onUpdated: (updated: Application) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [turnover, setTurnover] = useState("");
  const [months, setMonths] = useState("6");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const done = app.documents.some((d) => d.doc_type === item.code);
  const isField = item.kind === "field";
  const needsTurnover = item.code === STATEMENT;
  const ready =
    file !== null && (!needsTurnover || (turnover.trim() !== "" && months.trim() !== ""));

  async function upload() {
    if (!file) return;
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      setError(`Файл больше ${MAX_FILE_MB} МБ`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onUpdated(
        await api.uploadDocument(
          app.id,
          item.code,
          file,
          needsTurnover ? { turnover: Number(turnover), months: Number(months) } : undefined,
        ),
      );
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="cb-request" data-done={done}>
      <div className="cb-request-head">
        <Text view="accent-primary-medium" tag="h3">
          {item.title}
        </Text>
        {done && <span className="cb-request-done">загружено</span>}
      </div>

      <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
        {item.message}
      </Text>

      {/* Залог — не файл, а поля анкеты: она здесь же, ниже на странице. */}
      {isField ? (
        <Text view="secondary-medium" style={{ marginTop: 12 }}>
          Заполните вид и стоимость залога в анкете ниже — она сохранится сама.
        </Text>
      ) : (
        !done && (
          <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
            <input
              ref={fileRef}
              type="file"
              className="cb-file"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setError(null);
              }}
            />

            {needsTurnover && (
              <>
                <Input
                  label="Поступления по выписке"
                  rightAddons="₽"
                  type="number"
                  block
                  value={turnover}
                  onChange={(_, { value }) => setTurnover(value)}
                />
                <Input
                  label="За сколько месяцев"
                  rightAddons="мес."
                  type="number"
                  block
                  value={months}
                  onChange={(_, { value }) => setMonths(value)}
                />
                <Text view="secondary-medium" color={SECONDARY}>
                  Банк сверит эту сумму с выручкой из анкеты — {money(app.annual_revenue)} за год.
                </Text>
              </>
            )}

            <Button
              view="secondary"
              size={48}
              block
              className="mo-press"
              loading={busy}
              disabled={!ready}
              onClick={upload}
            >
              Загрузить
            </Button>

            <Text view="secondary-medium" color={SECONDARY}>
              До {MAX_FILE_MB} МБ. Файл остаётся внутри прототипа.
            </Text>
          </div>
        )
      )}

      {error && (
        <Text
          view="secondary-medium"
          color="var(--color-light-text-negative)"
          style={{ marginTop: 12 }}
        >
          {error}
        </Text>
      )}
    </div>
  );
}
