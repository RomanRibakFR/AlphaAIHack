import { useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Slider } from "@alfalab/core-components/slider";
import { useNavigate } from "react-router-dom";
import { Container, Text } from "../../ui/primitives";
import { Reveal } from "../../ui/Reveal";
import { useCountUp } from "../../lib/motion";
import type { Product } from "../../api/types";
import { months } from "../../lib/format";

const SECONDARY = "var(--color-light-text-secondary)";
const AMOUNT_STEP = 100_000;

const rub = (v: number) => `${Math.round(v).toLocaleString("ru-RU")} ₽`;

/** Аннуитет — та же формула, что считает бэкенд в applications.py. */
function annuity(principal: number, annualRate: number, termMonths: number) {
  const i = annualRate / 100 / 12;
  if (i === 0) return principal / termMonths;
  return (principal * i) / (1 - Math.pow(1 + i, -termMonths));
}

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

/** Сумма по умолчанию — ближе к началу диапазона, округлённая до шага слайдера. */
function defaultAmount(p: Product) {
  const min = Number(p.min_amount);
  const max = Number(p.max_amount);
  return clamp(Math.round((min + (max - min) * 0.2) / AMOUNT_STEP) * AMOUNT_STEP, min, max);
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="lp-calc-row">
      <span style={{ color: SECONDARY }}>{label}</span>
      <span style={{ fontWeight: strong ? 700 : 500 }}>{value}</span>
    </div>
  );
}

/** Сама панель. Вынесена отдельно, чтобы хуки не оказались за условием. */
function Panel({ products }: { products: Product[] }) {
  const navigate = useNavigate();
  const [code, setCode] = useState(products[0].code);
  const [amount, setAmount] = useState(() => defaultAmount(products[0]));
  const [term, setTerm] = useState(
    () => Math.round((products[0].min_term_months + products[0].max_term_months) / 2),
  );

  const product = products.find((p) => p.code === code) ?? products[0];
  const minAmount = Number(product.min_amount);
  const maxAmount = Number(product.max_amount);
  const rateValue = Number(product.base_rate);

  const safeAmount = clamp(amount, minAmount, maxAmount);
  const safeTerm = clamp(term, product.min_term_months, product.max_term_months);

  const payment = annuity(safeAmount, rateValue, safeTerm);
  const total = payment * safeTerm;

  /** Ticker: при движении слайдера платёж добегает до нового значения. */
  const shownPayment = useCountUp(payment, { duration: 320 });

  function pickProduct(next: Product) {
    setCode(next.code);
    // переносим выставленное человеком в границы нового продукта
    setAmount(clamp(safeAmount, Number(next.min_amount), Number(next.max_amount)));
    setTerm(clamp(safeTerm, next.min_term_months, next.max_term_months));
  }

  return (
    <Reveal variant="grow">
      <div className="lp-calc">
        <div className="lp-calc-controls">
          <div className="lp-tabs" role="tablist" aria-label="Кредитный продукт">
            {products.map((p) => (
              <button
                key={p.code}
                role="tab"
                aria-selected={p.code === product.code}
                className="lp-tab mo-press"
                onClick={() => pickProduct(p)}
              >
                {p.name}
              </button>
            ))}
          </div>

          <div className="lp-calc-field" style={{ marginTop: 32 }}>
            <div className="lp-calc-field-head">
              <Text view="primary-small" color={SECONDARY}>
                Сумма
              </Text>
              <Text view="accent-primary-large">{rub(safeAmount)}</Text>
            </div>
            <Slider
              min={minAmount}
              max={maxAmount}
              step={AMOUNT_STEP}
              value={safeAmount}
              onChange={({ value }) => setAmount(value)}
            />
          </div>

          <div className="lp-calc-field">
            <div className="lp-calc-field-head">
              <Text view="primary-small" color={SECONDARY}>
                Срок
              </Text>
              <Text view="accent-primary-large">{months(safeTerm)}</Text>
            </div>
            <Slider
              min={product.min_term_months}
              max={product.max_term_months}
              step={1}
              value={safeTerm}
              onChange={({ value }) => setTerm(value)}
            />
          </div>
        </div>

        <div className="lp-calc-result">
          <Text view="primary-small" color={SECONDARY}>
            Ежемесячный платёж
          </Text>
          <Text view="promo-h2" tag="div" style={{ marginTop: 4 }}>
            {rub(shownPayment)}
          </Text>

          <div className="lp-calc-rows">
            <Row label="Продукт" value={product.name} />
            <Row label="Ставка" value={`${rateValue.toLocaleString("ru-RU")}% годовых`} />
            <Row label="Залог" value={product.requires_collateral ? "нужен" : "не нужен"} />
            <Row label="Вернуть за весь срок" value={rub(total)} strong />
          </div>

          <div className="lp-calc-cta">
            <Button
              view="accent"
              size={56}
              block
              className="mo-press"
              onClick={() => navigate("/login")}
            >
              Подать заявку
            </Button>
          </div>
        </div>
      </div>
    </Reveal>
  );
}

export default function Calculator({ products }: { products: Product[] | null }) {
  return (
    <section className="lp-section" id="calculator">
      <Container>
        <Reveal>
          <div className="lp-section-head">
            <Text view="promo-h2" tag="h2">
              Сколько придётся платить
            </Text>
            <Text view="primary-large" color={SECONDARY} tag="p">
              Расчёт по базовой ставке продукта. Окончательные условия банк назовёт после
              проверки — они могут отличаться.
            </Text>
          </div>
        </Reveal>

        {products === null || products.length === 0 ? (
          <div className="lp-skeleton mo-shimmer" style={{ minHeight: 420 }} />
        ) : (
          <Panel products={products} />
        )}
      </Container>
    </section>
  );
}
