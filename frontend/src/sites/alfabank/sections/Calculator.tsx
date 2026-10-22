/** Блок «Рассчитайте выгоду» с главной alfabank.ru.
 *
 *  Четыре вкладки: вклад, счёт, кредит, ипотека. Два шаблона на всех:
 *   • пилюли + переключатели слева, таблица предложения справа (вклад, счёт);
 *   • слайдеры слева, итог справа (кредит, ипотека).
 *
 *  Размеры: внешняя карточка 1140×470, скругление 32, подложка #f2f3f5,
 *  внутренний отступ 8; левая панель 574, правая — белая карточка 550,
 *  скругление 24, отступ 24. Всё замерено на живой странице.
 *
 *  Ставки и значения по умолчанию взяты оттуда же. Платежи считаются
 *  аннуитетом прямо здесь, поэтому меняются вместе со слайдерами —
 *  на сайте расчёт делает их бэкенд.
 */
import { useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Slider } from "@alfalab/core-components/slider";
import { Switch } from "@alfalab/core-components/switch";
import { Tag } from "@alfalab/core-components/tag";
import { Text } from "../../../ui/primitives";

const SECONDARY = "var(--color-light-text-secondary)";

const money = (v: number) => Math.round(v).toLocaleString("ru-RU").replace(/,/g, " ");
const percent = (v: number) => v.toFixed(2).replace(".", ",") + "%";

/** Аннуитетный платёж: P — сумма, rate — годовая ставка в процентах, months — срок. */
function annuity(principal: number, rate: number, months: number) {
  const i = rate / 100 / 12;
  if (i === 0) return principal / months;
  return (principal * i) / (1 - Math.pow(1 + i, -months));
}

const TABS = ["Вклад", "Счёт", "Кредит", "Ипотека"] as const;

/* ——— вклад ——— */
const DEPOSIT_TERMS: Array<[string, number]> = [
  ["2 месяца", 2],
  ["3 месяца", 3],
  ["4 месяца", 4],
  ["5 месяцев", 5],
  ["6 месяцев", 6],
  ["7 месяцев", 7],
  ["8 месяцев", 8],
  ["9 месяцев", 9],
  ["10 месяцев", 10],
  ["11 месяцев", 11],
  ["1 год", 12],
  ["1,5 года", 18],
  ["2 года", 24],
  ["3 года", 36],
];

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "574px 550px",
        background: "var(--color-light-base-bg-secondary)",
        borderRadius: 32,
        padding: 8,
        minHeight: 470,
      }}
    >
      {children}
    </div>
  );
}

function Offer({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "var(--color-light-base-bg-primary)",
        borderRadius: 24,
        padding: 24,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {children}
    </div>
  );
}

function Row({ label, a, b }: { label: string; a: string; b?: string }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: b ? "1fr auto auto" : "1fr auto",
        gap: 24,
        alignItems: "baseline",
        padding: "12px 0",
        borderTop: "1px solid rgba(15, 25, 55, 0.1)",
      }}
    >
      <Text view="primary-small" color={SECONDARY}>
        {label}
      </Text>
      <Text view="accent-primary-medium" style={{ minWidth: 110, textAlign: "right" }}>
        {a}
      </Text>
      {b && (
        <Text view="accent-primary-medium" style={{ minWidth: 110, textAlign: "right" }}>
          {b}
        </Text>
      )}
    </div>
  );
}

function Deposit() {
  const [amount] = useState(1_000_000);
  const [term, setTerm] = useState(6);
  const [capitalization, setCapitalization] = useState(true);

  const base = capitalization ? 13.7 : 12.9;
  const only = base + 0.1;
  const income = (rate: number) => (amount * rate * term) / 100 / 12;

  return (
    <Panel>
      <div style={{ padding: 24 }}>
        <Text view="secondary-medium" color={SECONDARY}>
          Сумма вклада
        </Text>
        <Text view="promo-h3" style={{ marginTop: 4 }}>
          {money(amount)} ₽
        </Text>
        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
          от 10 000 ₽
        </Text>

        <Text view="primary-small" style={{ margin: "24px 0 12px" }}>
          Срок вклада:
        </Text>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {DEPOSIT_TERMS.map(([label, months]) => (
            <Tag
              key={months}
              view="filled"
              size={32}
              checked={months === term}
              onClick={() => setTerm(months)}
            >
              {label}
            </Tag>
          ))}
        </div>

        <Text view="primary-small" style={{ margin: "24px 0 12px" }}>
          Условия:
        </Text>
        <Switch
          label="Без вывода процентов (капитализация)"
          checked={capitalization}
          onChange={() => setCapitalization((v) => !v)}
        />
      </div>

      <Offer>
        <Text view="accent-primary-large" style={{ marginBottom: 16 }}>
          Наше предложение
        </Text>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto auto",
            gap: 24,
            paddingBottom: 8,
          }}
        >
          <Text view="secondary-medium" color={SECONDARY}>
            Условия
          </Text>
          <Text view="secondary-medium" color={SECONDARY} style={{ minWidth: 110, textAlign: "right" }}>
            Всем клиентам
          </Text>
          <Text view="secondary-medium" color={SECONDARY} style={{ minWidth: 110, textAlign: "right" }}>
            Клиентам Alfa Only
          </Text>
        </div>
        <Row label="Процентная ставка" a={percent(base)} b={percent(only)} />
        <Row label="Доход по вкладу" a={`+ ${money(income(base))} ₽`} b={`+ ${money(income(only))} ₽`} />
        <Row
          label="Сумма в конце срока"
          a={`${money(amount + income(base))} ₽`}
          b={`${money(amount + income(only))} ₽`}
        />

        <div style={{ marginTop: "auto", display: "flex", gap: 12, paddingTop: 24 }}>
          <Button view="secondary" size={48} href="https://alfabank.ru/make-money/deposits/">
            Подробные условия
          </Button>
          <Button view="accent" size={48} href="https://alfabank.ru/make-money/deposits/">
            Открыть вклад
          </Button>
        </div>
      </Offer>
    </Panel>
  );
}

/* ——— накопительный счёт ——— */
function SavingsAccount() {
  const [amount] = useState(1_000_000);
  const [kind, setKind] = useState(0);
  const [client, setClient] = useState(0);

  const first = [14, 13.5][kind] + [0, 0.3, 0.5][client];
  const later = [11.5, 11][kind] + [0, 0.3, 0.5][client];
  const perMonth = (rate: number) => (amount * rate) / 100 / 12;

  return (
    <Panel>
      <div style={{ padding: 24 }}>
        <Text view="secondary-medium" color={SECONDARY}>
          Сумма счёта
        </Text>
        <Text view="promo-h3" style={{ marginTop: 4 }}>
          {money(amount)} ₽
        </Text>

        <Text view="primary-small" style={{ margin: "24px 0 12px" }}>
          Вид счёта:
        </Text>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["% на минимальный остаток", "% на ежедневный остаток"].map((label, i) => (
            <Tag key={label} view="filled" size={32} checked={i === kind} onClick={() => setKind(i)}>
              {label}
            </Tag>
          ))}
        </div>

        <Text view="primary-small" style={{ margin: "24px 0 12px" }}>
          Условия:
        </Text>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Всем клиентам", "Клиентам Alfa Only", "Клиентам А-Клуба"].map((label, i) => (
            <Tag key={label} view="filled" size={32} checked={i === client} onClick={() => setClient(i)}>
              {label}
            </Tag>
          ))}
        </div>
      </div>

      <Offer>
        <Text view="accent-primary-large" style={{ marginBottom: 16 }}>
          Наше предложение
        </Text>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 24, paddingBottom: 8 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Период
          </Text>
          <Text view="secondary-medium" color={SECONDARY} style={{ minWidth: 110, textAlign: "right" }}>
            Ставка, % годовых
          </Text>
          <Text view="secondary-medium" color={SECONDARY} style={{ minWidth: 110, textAlign: "right" }}>
            Доход в месяц
          </Text>
        </div>
        <Row label="1–2 месяца" a={percent(first)} b={`${money(perMonth(first))} ₽`} />
        <Row label="с 3-го месяца" a={percent(later)} b={`${money(perMonth(later))} ₽`} />

        <Text view="primary-small" color={SECONDARY} style={{ marginTop: 16 }}>
          Выгодно, если копите. Начислим и выплатим % в конце месяца
        </Text>

        <div style={{ marginTop: "auto", display: "flex", gap: 12, paddingTop: 24 }}>
          <Button view="secondary" size={48} href="https://alfabank.ru/make-money/">
            Подробные условия
          </Button>
          <Button view="accent" size={48} href="https://alfabank.ru/make-money/">
            Открыть счёт
          </Button>
        </div>
      </Offer>
    </Panel>
  );
}

/* ——— кредит наличными ——— */
function CashCredit() {
  const [amount, setAmount] = useState(1_350_000);
  const [years, setYears] = useState(3);
  const rate = 17.99;
  const payment = annuity(amount, rate, years * 12);

  return (
    <Panel>
      <div style={{ padding: 24 }}>
        <Text view="secondary-medium" color={SECONDARY}>
          Сумма кредита
        </Text>
        <Text view="promo-h3" style={{ margin: "4px 0 16px" }}>
          {money(amount)} ₽
        </Text>
        <Slider
          min={30_000}
          max={30_000_000}
          step={10_000}
          value={amount}
          onChange={({ value }) => setAmount(value)}
          pips={{
            mode: "values",
            values: [30_000, 15_000_000, 30_000_000],
            format: { to: (v) => (v >= 1_000_000 ? `${v / 1_000_000} млн` : `${v / 1000} тыс.`) },
          }}
        />

        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 32 }}>
          Срок кредита
        </Text>
        <Text view="promo-h3" style={{ margin: "4px 0 16px" }}>
          {years} {years === 1 ? "год" : years < 5 ? "года" : "лет"}
        </Text>
        <Slider
          min={1}
          max={15}
          step={1}
          value={years}
          onChange={({ value }) => setYears(value)}
          pips={{
            mode: "values",
            values: [1, 15],
            format: { to: (v) => (v === 1 ? "1 год" : `${v} лет`) },
          }}
        />

        <Text view="secondary-small" color={SECONDARY} style={{ marginTop: 32 }}>
          ПСК 17,990% — 55,399%, % ставка от 17,99% до 55,39% годовых определяется для каждого
          заёмщика индивидуально. Не является публичной офертой
        </Text>
      </div>

      <Offer>
        <Text view="accent-primary-large">Наше предложение</Text>
        <Text view="primary-small" color={SECONDARY} style={{ marginTop: 24 }}>
          Ежемесячный платёж
        </Text>
        <Text view="promo-h2" style={{ marginTop: 4 }}>
          {money(payment)} ₽
        </Text>

        <Text view="primary-small" color={SECONDARY} style={{ marginTop: 32 }}>
          Вам понадобится
        </Text>
        <Text view="accent-primary-medium" style={{ marginTop: 4 }}>
          Паспорт
        </Text>

        <div style={{ marginTop: "auto", paddingTop: 24 }}>
          <Button view="accent" size={48} href="https://alfabank.ru/get-money/credit/credit-cash/">
            Получить деньги
          </Button>
        </div>
      </Offer>
    </Panel>
  );
}

/* ——— ипотека ——— */
function Mortgage() {
  const [price, setPrice] = useState(5_000_000);
  const [downPayment, setDownPayment] = useState(1_005_000);
  const [years, setYears] = useState(15);

  const principal = Math.max(price - downPayment, 0);
  const rate = 18.79;
  const payment = annuity(principal, rate, years * 12);

  return (
    <Panel>
      <div style={{ padding: 24 }}>
        <Text view="secondary-medium" color={SECONDARY}>
          Стоимость недвижимости
        </Text>
        <Text view="promo-h3" style={{ margin: "4px 0 16px" }}>
          {money(price)} ₽
        </Text>
        <Slider
          min={860_000}
          max={117_500_000}
          step={10_000}
          value={price}
          onChange={({ value }) => {
            setPrice(value);
            setDownPayment((d) => Math.min(d, value - 100_000));
          }}
          pips={{
            mode: "values",
            values: [860_000, 59_200_000, 117_500_000],
            format: { to: (v) => (v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)} млн` : `${v / 1000} тыс.`) },
          }}
        />

        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 28 }}>
          Первоначальный взнос
        </Text>
        <Text view="promo-h3" style={{ margin: "4px 0 16px" }}>
          {money(downPayment)} ₽ · {Math.round((downPayment / price) * 100)}%
        </Text>
        <Slider
          min={Math.round(price * 0.2)}
          max={Math.round(price * 0.9)}
          step={5_000}
          value={downPayment}
          onChange={({ value }) => setDownPayment(value)}
        />

        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 28 }}>
          Срок кредитования
        </Text>
        <Text view="promo-h3" style={{ margin: "4px 0 16px" }}>
          {years} лет
        </Text>
        <Slider min={3} max={30} step={1} value={years} onChange={({ value }) => setYears(value)} />
      </div>

      <Offer>
        <Text view="accent-primary-large">Наше предложение</Text>
        <Text view="primary-small" color={SECONDARY} style={{ marginTop: 20 }}>
          Ежемесячный платёж
        </Text>
        <Text view="promo-h2" style={{ marginTop: 4, marginBottom: 12 }}>
          {money(payment)} ₽
        </Text>
        <Row label="Сумма кредита" a={`${money(principal)} ₽`} />
        <Row label="Срок" a={`${years} лет`} />
        <Row label="Ставка" a={percent(rate)} />
        <Row label="ПСК" a="16,763% — 26,267%" />
        <Row label="Налоговый вычет" a="650 000 ₽" />

        <div style={{ marginTop: "auto", display: "flex", gap: 12, paddingTop: 20 }}>
          <Button view="secondary" size={48} href="https://alfabank.ru/get-money/mortgage/">
            График платежей
          </Button>
          <Button view="accent" size={48} href="https://alfabank.ru/get-money/mortgage/">
            Заполнить заявку
          </Button>
        </div>
      </Offer>
    </Panel>
  );
}

export default function Calculator() {
  const [active, setActive] = useState(0);

  return (
    <section className="ab-section">
      <div className="ab-section-head">
        <Text view="promo-h2" tag="h2">
          Рассчитайте выгоду
        </Text>
        <div className="ab-tabs" role="tablist">
          {TABS.map((label, i) => (
            <button
              key={label}
              role="tab"
              aria-selected={i === active}
              className="ab-tab"
              onClick={() => setActive(i)}
              style={{ width: 105 }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {active === 0 && <Deposit />}
      {active === 1 && <SavingsAccount />}
      {active === 2 && <CashCredit />}
      {active === 3 && <Mortgage />}

      <Text view="secondary-small" color={SECONDARY} style={{ marginTop: 16, maxWidth: 560 }}>
        Расчёт калькулятора предварительный. Персональные условия вы сможете узнать после
        оформления заявки.
      </Text>
    </section>
  );
}
