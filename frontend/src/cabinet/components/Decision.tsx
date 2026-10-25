/**
 * Решение банка: предложение, отказ и договор после выдачи.
 *
 * Всё, что здесь показано, приходит из ответа бэкенда — фронт ничего
 * не пересчитывает. Это важно по двум причинам: цифры решения считает
 * кредитная политика, а жюри должно видеть, что на экране ровно то,
 * что решил банк.
 */
import { useState } from "react";
import type { Offer, Payment, Rejection } from "../../api/types";
import { Text } from "../../ui/primitives";
import { date, dateTime, money, months, plural, rate } from "../../lib/format";

const SECONDARY = "var(--color-light-text-secondary)";

/** Чем предложение отличается от запроса — словами, а не кодом. */
const COUNTER_KIND: Record<string, string> = {
  TERM_EXTENDED: "срок больше, чем вы просили",
  TERM_REDUCED: "срок меньше, чем вы просили",
  AMOUNT_REDUCED: "сумма меньше, чем вы просили",
  AMOUNT_AND_TERM: "другая сумма и другой срок",
};

function Pair({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="cb-pair">
      <span>{label}</span>
      <span style={strong ? { fontWeight: 600 } : undefined}>{value}</span>
    </div>
  );
}

/**
 * Предложение банка.
 *
 * Главное здесь — не перепутать запрошенное с одобренным. Если банк
 * изменил условия, обе цифры стоят рядом: иначе человек принимает одно,
 * а подписывает другое.
 */
export function OfferPanel({
  offer,
  chosen,
  onChoose,
}: {
  offer: Offer;
  chosen: number | null;
  onChoose: (index: number | null) => void;
}) {
  const counter = offer.type === "COUNTER";
  const variant =
    chosen === null
      ? { amount: offer.amount, term_months: offer.term_months, monthly_payment: offer.monthly_payment }
      : offer.alternatives[chosen];

  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        {counter ? "Предложение банка" : "Кредит одобрен"}
      </Text>

      {counter && (
        <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
          Вы просили {money(offer.requested_amount)} на {months(offer.requested_term_months)}.
          Банк готов выдать на других условиях
          {offer.counter_kind && COUNTER_KIND[offer.counter_kind]
            ? `: ${COUNTER_KIND[offer.counter_kind]}`
            : ""}
          .
        </Text>
      )}

      <div className="cb-pairs" style={{ marginTop: 20 }}>
        <Pair label="Сумма" value={money(variant.amount)} />
        <Pair label="Срок" value={months(variant.term_months)} />
        <Pair label="Ставка" value={rate(offer.rate)} />
        <Pair label="Платёж" value={`${money(variant.monthly_payment)} в месяц`} strong />
        {chosen === null && <Pair label="Вернуть за весь срок" value={money(offer.total_payment)} />}
      </div>

      {offer.alternatives.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <Text view="accent-primary-medium" tag="h3">
            Можно выбрать другой вариант
          </Text>
          <div className="cb-variants">
            <button
              type="button"
              className="cb-variant"
              aria-pressed={chosen === null}
              onClick={() => onChoose(null)}
            >
              <span>{money(offer.amount)}</span>
              <span style={{ color: SECONDARY }}>
                {months(offer.term_months)} · {money(offer.monthly_payment)} в месяц
              </span>
            </button>
            {offer.alternatives.map((alt, i) => (
              <button
                type="button"
                key={i}
                className="cb-variant"
                aria-pressed={chosen === i}
                onClick={() => onChoose(i)}
              >
                <span>{money(alt.amount)}</span>
                <span style={{ color: SECONDARY }}>
                  {months(alt.term_months)} · {money(alt.monthly_payment)} в месяц
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {offer.reason && (
        <div className="cb-card" style={{ marginTop: 20 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Почему такие условия
          </Text>
          <Text view="primary-small" style={{ marginTop: 4 }}>
            {offer.reason}
          </Text>
        </div>
      )}

      {offer.advice && (
        <div className="cb-card" style={{ marginTop: 12 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Что можно сделать
          </Text>
          <Text view="primary-small" style={{ marginTop: 4 }}>
            {offer.advice}
          </Text>
        </div>
      )}

      {offer.conditions.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Условия выдачи
          </Text>
          <ul className="cb-list" style={{ marginTop: 8 }}>
            {offer.conditions.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 20 }}>
        Предложение действует до {dateTime(offer.valid_until)}.
      </Text>
    </section>
  );
}

/** Отказ: причина и что с этим делать — то, чего по исследованию ждут клиенты. */
export function RejectionPanel({ rejection }: { rejection: Rejection }) {
  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        Почему отказали
      </Text>
      <Text view="primary-medium" style={{ marginTop: 12, maxWidth: 560 }}>
        {rejection.reason}
      </Text>
      {rejection.advice && (
        <div className="cb-card" style={{ marginTop: 20 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Что можно сделать
          </Text>
          <Text view="primary-small" style={{ marginTop: 4 }}>
            {rejection.advice}
          </Text>
        </div>
      )}
    </section>
  );
}

const SHOWN_BY_DEFAULT = 6;

/** Договор и график платежей — после выдачи. */
export function ContractPanel({
  contractNumber,
  issuedAt,
  schedule,
}: {
  contractNumber: string | null;
  issuedAt: string | null;
  schedule: Payment[] | null;
}) {
  const [all, setAll] = useState(false);
  const rows = schedule ?? [];
  const shown = all ? rows : rows.slice(0, SHOWN_BY_DEFAULT);

  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        Договор
      </Text>

      <div className="cb-pairs" style={{ marginTop: 20 }}>
        {contractNumber && <Pair label="Номер договора" value={contractNumber} />}
        {issuedAt && <Pair label="Деньги зачислены" value={dateTime(issuedAt)} />}
        {rows.length > 0 && <Pair label="Платежей" value={String(rows.length)} />}
      </div>

      {rows.length > 0 && (
        <>
          <Text view="accent-primary-medium" tag="h3" style={{ marginTop: 24 }}>
            График платежей
          </Text>
          <table className="cb-table" style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>№</th>
                <th>Дата</th>
                <th>Платёж</th>
                <th>Основной долг</th>
                <th>Проценты</th>
                <th>Остаток</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((row) => (
                <tr key={row.n}>
                  <td>{row.n}</td>
                  <td>{date(row.date)}</td>
                  <td>{money(row.payment)}</td>
                  <td>{money(row.principal)}</td>
                  <td>{money(row.interest)}</td>
                  <td>{money(row.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {rows.length > SHOWN_BY_DEFAULT && (
            <button type="button" className="cb-more" onClick={() => setAll((v) => !v)}>
              {all
                ? "Свернуть график"
                : `Показать все ${rows.length} ${plural(rows.length, "платёж", "платежа", "платежей")}`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
