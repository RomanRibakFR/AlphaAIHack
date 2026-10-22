import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api/client";
import type { Application, FieldProblem, Product } from "../api/types";
import { money, months, rate } from "../lib/format";

type Props = {
  app: Application;
  products: Product[];
  /** Поля, на которые пожаловался /submit. */
  problems: FieldProblem[];
  /** Пользователь правит поле — его ошибку пора убрать. */
  onFieldEdited: (field: string) => void;
  onSaved: (updated: Application) => void;
};

type SaveState = "idle" | "saving" | "saved" | "error";

/** Значения полей формы в том виде, в каком их видит пользователь. */
type Snapshot = { productCode: string; amount: string; term: string; purpose: string };

const SAVE_DELAY_MS = 600;

function snapshot(app: Application): Snapshot {
  return {
    productCode: app.product.code,
    amount: (app.amount ?? "").replace(/\.00$/, ""),
    term: app.term_months?.toString() ?? "",
    purpose: app.purpose,
  };
}

function same(a: Snapshot, b: Snapshot): boolean {
  return (
    a.productCode === b.productCode &&
    a.amount === b.amount &&
    a.term === b.term &&
    a.purpose === b.purpose
  );
}

/** Форма черновика с автосохранением: PATCH через паузу после последнего нажатия. */
export default function DraftForm({ app, products, problems, onFieldEdited, onSaved }: Props) {
  // в инпуте показываем 2000000, а не 2000000.00 — бэкенд всё равно нормализует
  const initial = snapshot(app);
  const [amount, setAmount] = useState(initial.amount);
  const [term, setTerm] = useState(initial.term);
  const [purpose, setPurpose] = useState(initial.purpose);
  const [productCode, setProductCode] = useState(initial.productCode);

  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  // что уже лежит в базе. Сравниваем с этим, а не считаем рендеры:
  // в StrictMode эффекты вызываются дважды, и счётчик рендеров дал бы лишний PATCH
  const saved = useRef(snapshot(app));
  const current: Snapshot = { productCode, amount, term, purpose };

  useEffect(() => {
    if (same(saved.current, current)) return;

    const timer = setTimeout(async () => {
      setSaveState("saving");
      setSaveError(null);
      try {
        const updated = await api.updateApplication(app.id, {
          product_code: productCode,
          amount: amount.trim() === "" ? null : amount.trim(),
          term_months: term.trim() === "" ? null : Number(term),
          purpose,
        });
        saved.current = current;
        setSaveState("saved");
        onSaved(updated);
      } catch (e) {
        setSaveState("error");
        setSaveError((e as ApiError).message);
      }
    }, SAVE_DELAY_MS);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [amount, term, purpose, productCode]);

  const problemFor = (field: string) => problems.find((p) => p.field === field)?.message;
  const product = products.find((p) => p.code === productCode);

  return (
    <section>
      <h3>Заявка</h3>

      <label>
        Продукт
        <select value={productCode} onChange={(e) => setProductCode(e.target.value)}>
          {products.map((p) => (
            <option key={p.code} value={p.code}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {product && (
        <p className="muted">
          {product.description}
          <br />
          Сумма {money(product.min_amount)} — {money(product.max_amount)}, срок{" "}
          {product.min_term_months}—{product.max_term_months} мес., {rate(product.base_rate)}
          {product.requires_collateral && ", нужен залог"}
        </p>
      )}

      <label>
        Сумма, ₽
        <input
          type="number"
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
            onFieldEdited("amount");
          }}
          placeholder="например, 2000000"
        />
      </label>
      {problemFor("amount") && <p className="field-error">{problemFor("amount")}</p>}

      <label>
        Срок, месяцев
        <input
          type="number"
          value={term}
          onChange={(e) => {
            setTerm(e.target.value);
            onFieldEdited("term_months");
          }}
          placeholder="например, 12"
        />
      </label>
      {problemFor("term_months") && <p className="field-error">{problemFor("term_months")}</p>}

      <label>
        На что нужны деньги
        <textarea
          value={purpose}
          onChange={(e) => {
            setPurpose(e.target.value);
            onFieldEdited("purpose");
          }}
          rows={3}
        />
      </label>
      {problemFor("purpose") && <p className="field-error">{problemFor("purpose")}</p>}

      <p>
        Примерный платёж: <b>{money(app.estimated_payment)}</b> в месяц
        {app.term_months !== null && ` на ${months(app.term_months)}`}
        <br />
        <span className="muted">считает бэкенд по базовой ставке продукта</span>
      </p>

      <p className="muted">
        {saveState === "saving" && "Сохраняем…"}
        {saveState === "saved" && "Черновик сохранён"}
        {saveState === "idle" && "Черновик сохраняется сам"}
        {saveState === "error" && <span className="field-error">Не сохранилось: {saveError}</span>}
      </p>
    </section>
  );
}
