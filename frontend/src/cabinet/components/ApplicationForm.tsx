import { useEffect, useRef, useState } from "react";
import { Input } from "@alfalab/core-components/input";
import { Select } from "@alfalab/core-components/select";
import { Textarea } from "@alfalab/core-components/textarea";
import { ApiError, api } from "../../api/client";
import type { Application, FieldProblem, Product } from "../../api/types";
import { Text } from "../../ui/primitives";
import { money, months, rate } from "../../lib/format";

const SECONDARY = "var(--color-light-text-secondary)";
const SAVE_DELAY_MS = 600;

type Snapshot = {
  amount: string;
  term: string;
  purpose: string;
  revenue: string;
  collateralType: string;
  collateralDescription: string;
  collateralValue: string;
};

/** В поле показываем 2000000, а не 2000000.00 — бэкенд всё равно нормализует. */
const plain = (value: string | null) => (value ?? "").replace(/\.00$/, "");

function snapshot(app: Application): Snapshot {
  return {
    amount: plain(app.amount),
    term: app.term_months?.toString() ?? "",
    purpose: app.purpose,
    revenue: plain(app.annual_revenue),
    collateralType: app.collateral_type ?? "",
    collateralDescription: app.collateral_description ?? "",
    collateralValue: plain(app.collateral_value),
  };
}

const same = (a: Snapshot, b: Snapshot) =>
  (Object.keys(a) as Array<keyof Snapshot>).every((k) => a[k] === b[k]);

/** Виды залога — как их называет бэкенд (collateral_type в анкете). */
const COLLATERAL_TYPES = [
  { value: "REAL_ESTATE", label: "Недвижимость" },
  { value: "EQUIPMENT", label: "Оборудование" },
  { value: "VEHICLE", label: "Транспорт" },
];

/**
 * Черновик заявки с автосохранением.
 *
 * Продукт здесь не меняется: его выбрали на шаге подбора по задаче.
 * Всё, что банк знает сам, в форме не спрашиваем — это главный смысл
 * кабинета по исследованию.
 */
export default function ApplicationForm({
  app,
  product,
  problems,
  onFieldEdited,
  onSaved,
}: {
  app: Application;
  product: Product | null;
  problems: FieldProblem[];
  onFieldEdited: (field: string) => void;
  onSaved: (updated: Application) => void;
}) {
  const initial = snapshot(app);
  const [amount, setAmount] = useState(initial.amount);
  const [term, setTerm] = useState(initial.term);
  const [purpose, setPurpose] = useState(initial.purpose);
  const [revenue, setRevenue] = useState(initial.revenue);
  const [collateralType, setCollateralType] = useState(initial.collateralType);
  const [collateralDescription, setCollateralDescription] = useState(initial.collateralDescription);
  const [collateralValue, setCollateralValue] = useState(initial.collateralValue);

  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  // сравниваем с тем, что уже в базе: в StrictMode эффекты вызываются дважды,
  // и счётчик рендеров дал бы лишний запрос на сохранение
  const saved = useRef(initial);
  const current: Snapshot = {
    amount,
    term,
    purpose,
    revenue,
    collateralType,
    collateralDescription,
    collateralValue,
  };

  useEffect(() => {
    if (same(saved.current, current)) return;

    const timer = setTimeout(async () => {
      setState("saving");
      setSaveError(null);
      try {
        const updated = await api.updateApplication(app.id, {
          amount: amount.trim() === "" ? null : amount.trim(),
          term_months: term.trim() === "" ? null : Number(term),
          purpose,
          annual_revenue: revenue.trim() === "" ? null : revenue.trim(),
          collateral_type: collateralType === "" ? null : collateralType,
          collateral_description:
            collateralDescription.trim() === "" ? null : collateralDescription.trim(),
          collateral_value: collateralValue.trim() === "" ? null : collateralValue.trim(),
        });
        saved.current = current;
        setState("saved");
        onSaved(updated);
      } catch (e) {
        setState("error");
        setSaveError((e as ApiError).message);
      }
    }, SAVE_DELAY_MS);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [amount, term, purpose, revenue, collateralType, collateralDescription, collateralValue]);

  const problemFor = (field: string) => problems.find((p) => p.field === field)?.message;

  return (
    <section className="cb-card-white">
      <Text view="accent-primary-large" tag="h2">
        Параметры кредита
      </Text>

      <div style={{ marginTop: 24 }}>
        <div className="cb-field">
          <Input
            label="Сумма"
            rightAddons="₽"
            type="number"
            block
            value={amount}
            error={problemFor("amount")}
            onChange={(_, { value }) => {
              setAmount(value);
              onFieldEdited("amount");
            }}
          />
          {product && !problemFor("amount") && (
            <div className="cb-hint">
              от {money(product.min_amount)} до {money(product.max_amount)}
            </div>
          )}
        </div>

        <div className="cb-field">
          <Input
            label="Срок"
            rightAddons="мес."
            type="number"
            block
            value={term}
            error={problemFor("term_months")}
            onChange={(_, { value }) => {
              setTerm(value);
              onFieldEdited("term_months");
            }}
          />
          {product && !problemFor("term_months") && (
            <div className="cb-hint">
              {product.min_term_months === product.max_term_months
                ? `только ${product.min_term_months} мес.`
                : `от ${product.min_term_months} до ${product.max_term_months} мес.`}
            </div>
          )}
        </div>

        <div className="cb-field">
          <Textarea
            label="На что нужны деньги"
            block
            maxRows={5}
            value={purpose}
            error={problemFor("purpose")}
            onChange={(_, { value }) => {
              setPurpose(value);
              onFieldEdited("purpose");
            }}
          />
          {!problemFor("purpose") && (
            <div className="cb-hint">
              Коротко: закупка товара, оборудование, зарплаты. Это помогает банку подобрать
              условия.
            </div>
          )}
        </div>

        {/* Единственная цифра, которой банк не знает сам: обороты он видит
            только по своему счёту, а выручка может идти и через другие банки.
            Расхождение с оборотами — повод запросить выписку. */}
        <div className="cb-field">
          <Input
            label="Выручка за последние 12 месяцев"
            rightAddons="₽"
            type="number"
            block
            value={revenue}
            error={problemFor("annual_revenue")}
            onChange={(_, { value }) => {
              setRevenue(value);
              onFieldEdited("annual_revenue");
            }}
          />
          {!problemFor("annual_revenue") && (
            <div className="cb-hint">
              По всем счетам, не только в Альфа-Банке. Банк сверит с оборотами по счёту.
            </div>
          )}
        </div>

        {product?.requires_collateral && (
          <>
            <div className="cb-field">
              <Select
                label="Вид залога"
                placeholder="Выберите вид залога"
                block
                options={COLLATERAL_TYPES.map((c) => ({ key: c.value, content: c.label }))}
                selected={collateralType || null}
                error={problemFor("collateral")}
                onChange={({ selected }) => {
                  setCollateralType(selected ? String(selected.key) : "");
                  onFieldEdited("collateral");
                }}
              />
            </div>

            <div className="cb-field">
              <Input
                label="Что именно в залог"
                block
                value={collateralDescription}
                onChange={(_, { value }) => setCollateralDescription(value)}
              />
              <div className="cb-hint">Например: производственное помещение, 1 200 м².</div>
            </div>

            <div className="cb-field">
              <Input
                label="Оценочная стоимость залога"
                rightAddons="₽"
                type="number"
                block
                value={collateralValue}
                onChange={(_, { value }) => setCollateralValue(value)}
              />
              <div className="cb-hint">Банк выдаёт не больше 70% стоимости залога.</div>
            </div>
          </>
        )}
      </div>

      {app.estimated_payment && (
        <div className="cb-card" style={{ marginTop: 8 }}>
          <Text view="secondary-medium" color={SECONDARY}>
            Примерный платёж
          </Text>
          <Text view="promo-h3" tag="div" style={{ marginTop: 4 }}>
            {money(app.estimated_payment)} в месяц
          </Text>
          <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 6 }}>
            {product ? `от ${rate(product.base_rate)} · ` : ""}
            {app.term_months !== null && months(app.term_months)}. Окончательные условия банк
            назовёт после проверки.
          </Text>
        </div>
      )}

      <div className="cb-save" style={{ marginTop: 16 }}>
        {state === "saving" && "Сохраняем…"}
        {state === "saved" && "Черновик сохранён"}
        {state === "idle" && "Черновик сохраняется сам"}
        {state === "error" && (
          <span style={{ color: "var(--color-light-text-negative)" }}>
            Не сохранилось: {saveError}
          </span>
        )}
      </div>
    </section>
  );
}
