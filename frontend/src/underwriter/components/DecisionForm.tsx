import { useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { Select } from "@alfalab/core-components/select";
import { Textarea } from "@alfalab/core-components/textarea";
import type { Recommendation, UnderwriterDecision } from "../../api/types";
import { Text } from "../../ui/primitives";
import { money } from "../../lib/format";
import { REJECT_REASONS, REQUEST_ITEMS } from "../content";

const SECONDARY = "var(--color-light-text-secondary)";

type Action = UnderwriterDecision["action"];

const ACTIONS: Array<{ id: Action; label: string }> = [
  { id: "approve", label: "Одобрить" },
  { id: "request_info", label: "Запросить данные" },
  { id: "reject", label: "Отказать" },
];

/**
 * Решение специалиста.
 *
 * Комментарий обязателен во всех трёх случаях — так требует бэкенд,
 * и это правильно: решение человека должно быть объяснено в деле,
 * иначе разобраться в нём потом невозможно.
 *
 * При одобрении поля суммы, срока и ставки заранее заполнены
 * рекомендацией системы: чаще всего специалист с ней соглашается,
 * а менять их всё равно можно.
 */
export default function DecisionForm({
  recommendation,
  busy,
  error,
  onSubmit,
}: {
  recommendation: Recommendation | null;
  busy: boolean;
  error: string | null;
  onSubmit: (body: UnderwriterDecision) => void;
}) {
  const [action, setAction] = useState<Action>("approve");
  const [comment, setComment] = useState("");

  const [amount, setAmount] = useState(recommendation ? String(recommendation.amount) : "");
  const [term, setTerm] = useState(recommendation ? String(recommendation.term_months) : "");
  const [rate, setRate] = useState(recommendation ? String(recommendation.rate) : "");

  const [reasonCode, setReasonCode] = useState("");
  const [reason, setReason] = useState("");
  const [advice, setAdvice] = useState("");

  const [items, setItems] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  const ready =
    comment.trim() !== "" &&
    (action !== "reject" || reasonCode !== "") &&
    (action !== "request_info" || (items.length > 0 && message.trim() !== ""));

  function submit() {
    if (action === "approve") {
      onSubmit({
        action,
        comment: comment.trim(),
        amount: amount.trim() || undefined,
        term_months: term.trim() ? Number(term) : undefined,
        rate: rate.trim() || undefined,
      });
    } else if (action === "reject") {
      onSubmit({
        action,
        comment: comment.trim(),
        reason_code: reasonCode,
        reason: reason.trim() || undefined,
        advice: advice.trim() || undefined,
      });
    } else {
      onSubmit({ action, comment: comment.trim(), items, message: message.trim() });
    }
  }

  return (
    <section className="cb-card">
      <Text view="accent-primary-large" tag="h2">
        Решение
      </Text>

      <div className="uw-actions" role="tablist">
        {ACTIONS.map((a) => (
          <button
            key={a.id}
            role="tab"
            aria-selected={a.id === action}
            className="uw-action"
            onClick={() => setAction(a.id)}
          >
            {a.label}
          </button>
        ))}
      </div>

      {action === "approve" && (
        <div style={{ marginTop: 20, display: "grid", gap: 12 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            {recommendation
              ? "Подставлена рекомендация системы — можно изменить."
              : "Рекомендации нет, укажите условия сами."}
          </Text>
          <Input
            label="Сумма"
            rightAddons="₽"
            type="number"
            block
            value={amount}
            onChange={(_, { value }) => setAmount(value)}
          />
          <Input
            label="Срок"
            rightAddons="мес."
            type="number"
            block
            value={term}
            onChange={(_, { value }) => setTerm(value)}
          />
          <Input
            label="Ставка"
            rightAddons="% годовых"
            type="number"
            block
            value={rate}
            onChange={(_, { value }) => setRate(value)}
          />
          {recommendation && (
            <Text view="secondary-medium" color={SECONDARY}>
              Платёж по рекомендации — {money(String(recommendation.monthly_payment))} в месяц.
            </Text>
          )}
        </div>
      )}

      {action === "reject" && (
        <div style={{ marginTop: 20, display: "grid", gap: 12 }}>
          <Select
            label="Причина отказа"
            placeholder="Выберите причину"
            block
            options={REJECT_REASONS.map((r) => ({ key: r.code, content: r.title }))}
            selected={reasonCode || null}
            onChange={({ selected }) => setReasonCode(selected ? String(selected.key) : "")}
          />
          <Textarea
            label="Причина для клиента"
            block
            maxRows={4}
            value={reason}
            onChange={(_, { value }) => setReason(value)}
          />
          <Textarea
            label="Что клиент может сделать"
            block
            maxRows={4}
            value={advice}
            onChange={(_, { value }) => setAdvice(value)}
          />
          <Text view="secondary-medium" color={SECONDARY}>
            Эти два текста клиент увидит в кабинете. Если оставить пустыми, банк напишет
            формулировку по умолчанию.
          </Text>
        </div>
      )}

      {action === "request_info" && (
        <div style={{ marginTop: 20, display: "grid", gap: 12 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Что запросить у клиента
          </Text>
          <div style={{ display: "grid", gap: 8 }}>
            {REQUEST_ITEMS.map((item) => (
              <button
                key={item.code}
                type="button"
                className="cb-variant"
                aria-pressed={items.includes(item.code)}
                onClick={() =>
                  setItems((prev) =>
                    prev.includes(item.code)
                      ? prev.filter((c) => c !== item.code)
                      : [...prev, item.code],
                  )
                }
              >
                <span>{item.title}</span>
              </button>
            ))}
          </div>
          <Textarea
            label="Что и зачем нужно — увидит клиент"
            block
            maxRows={5}
            value={message}
            onChange={(_, { value }) => setMessage(value)}
          />
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <Textarea
          label="Комментарий специалиста"
          block
          maxRows={4}
          value={comment}
          onChange={(_, { value }) => setComment(value)}
        />
        <div className="cb-hint">
          Остаётся в деле заявки, клиенту не показывается. Без него решение не принимается.
        </div>
      </div>

      <Button
        view="accent"
        size={48}
        block
        className="mo-press"
        style={{ marginTop: 16 }}
        loading={busy}
        disabled={!ready}
        onClick={submit}
      >
        {ACTIONS.find((a) => a.id === action)?.label}
      </Button>

      {error && (
        <Text
          view="secondary-medium"
          color="var(--color-light-text-negative)"
          style={{ marginTop: 12 }}
        >
          {error}
        </Text>
      )}
    </section>
  );
}
