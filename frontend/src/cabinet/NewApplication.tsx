import { useEffect, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { Product, RegistryCompany } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal, Stagger } from "../ui/Reveal";
import { money, rateRange, termRange } from "../lib/format";
import { GOALS } from "./content";
import { checkProduct, productFits, type Criterion } from "./precheck";

const SECONDARY = "var(--color-light-text-secondary)";

function Mark({ ok }: { ok: boolean }) {
  return (
    <svg className="cb-check-mark" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      {ok ? (
        <path
          d="M3 8.5l3.5 3.5L13 5"
          fill="none"
          stroke="var(--color-light-text-positive)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M4 4l8 8M12 4l-8 8"
          fill="none"
          stroke="var(--color-light-text-negative)"
          strokeWidth="2"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}

function ProductCard({
  product,
  criteria,
  fits,
  busy,
  onChoose,
}: {
  product: Product;
  criteria: Criterion[];
  fits: boolean;
  busy: boolean;
  onChoose: () => void;
}) {
  return (
    <div className="cb-card-white" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Text view="promo-card" tag="h3">
        {product.name}
      </Text>
      <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
        {product.description}
      </Text>

      <div className="cb-pairs" style={{ marginTop: 20 }}>
        <div className="cb-pair">
          <span>Сумма</span>
          <span>
            {money(product.min_amount)} — {money(product.max_amount)}
          </span>
        </div>
        <div className="cb-pair">
          <span>Срок</span>
          <span>{termRange(product.min_term_months, product.max_term_months)}</span>
        </div>
        <div className="cb-pair">
          <span>Ставка</span>
          <span>{rateRange(product.base_rate, product.max_rate)}</span>
        </div>
      </div>

      <div style={{ marginTop: 20, display: "grid", gap: 10 }}>
        {criteria.map((c) => (
          <div key={c.text} className="cb-check">
            <Mark ok={c.ok} />
            <span style={{ color: c.ok ? undefined : "var(--color-light-text-negative)" }}>
              {c.text}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "auto", paddingTop: 24 }}>
        <Button view="accent" size={48} block className="mo-press" disabled={!fits || busy} onClick={onChoose}>
          {busy ? "Создаём…" : fits ? "Заполнить заявку" : "Пока не подходит"}
        </Button>
      </div>
    </div>
  );
}

/**
 * Подбор кредита.
 *
 * Сначала спрашиваем про задачу, а не про банковский продукт: из исследования
 * предприниматель не знает, что выбрать, и идёт за консультацией к менеджеру.
 * Формальные критерии показываем здесь же — до того, как человек начал
 * заполнять анкету.
 */
export default function NewApplication({ inn }: { inn: string }) {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [company, setCompany] = useState<RegistryCompany | null>(null);
  const [goalId, setGoalId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.products(), api.lookupCompany(inn)])
      .then(([p, c]) => {
        if (!alive) return;
        setProducts(p);
        setCompany(c);
      })
      .catch((e) => alive && setError((e as ApiError).message));
    return () => {
      alive = false;
    };
  }, [inn]);

  async function choose(code: string, purpose: string) {
    setBusy(code);
    setError(null);
    try {
      const app = await api.createApplication({ inn, product_code: code, purpose });
      navigate(`/application/${app.id}`);
    } catch (e) {
      setError((e as ApiError).message);
      setBusy(null);
    }
  }

  if (error && products === null) {
    return (
      <Text view="primary-medium" color="var(--color-light-text-negative)">
        {error}
      </Text>
    );
  }

  if (products === null || company === null) {
    return <div className="lp-skeleton mo-shimmer" style={{ minHeight: 320, borderRadius: 32 }} />;
  }

  const goal = GOALS.find((g) => g.id === goalId);
  const matching = goal
    ? goal.products
        .map((code) => products.find((p) => p.code === code))
        .filter((p): p is Product => p !== undefined)
    : [];

  return (
    <>
      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              На что нужны деньги
            </Text>
            <Text view="primary-medium" color={SECONDARY} style={{ marginTop: 8, maxWidth: 620 }}>
              Выберите задачу — подходящий кредит подберём сами. Сразу покажем, проходите ли
              вы по формальным требованиям.
            </Text>
          </div>
        </div>
      </Reveal>

      <Stagger className="cb-goals" step={80}>
        {GOALS.map((g) => (
          <button
            key={g.id}
            className="cb-goal mo-press"
            aria-pressed={g.id === goalId}
            onClick={() => setGoalId(g.id)}
          >
            <Text view="accent-primary-large" tag="div">
              {g.title}
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              {g.text}
            </Text>
          </button>
        ))}
      </Stagger>

      {goal && (
        <div style={{ marginTop: 48 }}>
          <Reveal>
            <Text view="promo-h3" tag="h2">
              {matching.length === 1 ? "Подходит" : "Что подходит"}
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8, marginBottom: 24 }}>
              Требования проверены по данным реестра — заполнять ничего не нужно.
            </Text>
          </Reveal>

          <Stagger
            className="cb-goals"
            step={80}
            style={{ gridTemplateColumns: `repeat(${Math.min(matching.length, 3)}, 1fr)` }}
          >
            {matching.map((p) => (
              <ProductCard
                key={p.code}
                product={p}
                criteria={checkProduct(company, p)}
                fits={productFits(company, p)}
                busy={busy === p.code}
                onChoose={() => choose(p.code, goal.title)}
              />
            ))}
          </Stagger>

          {error && (
            <Text view="primary-small" color="var(--color-light-text-negative)" style={{ marginTop: 16 }}>
              {error}
            </Text>
          )}
        </div>
      )}
    </>
  );
}
