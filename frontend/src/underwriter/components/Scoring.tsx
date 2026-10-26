import type { Decision } from "../../api/types";
import { Text } from "../../ui/primitives";
import { FEATURES } from "../content";
import Grade from "./Grade";

const SECONDARY = "var(--color-light-text-secondary)";

const pct = (v: string) =>
  `${(Number(v) * 100).toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%`;

function value(raw: number | undefined, format: string): string {
  if (raw === undefined) return "—";
  const num = (v: number, digits = 2) => v.toLocaleString("ru-RU", { maximumFractionDigits: digits });
  switch (format) {
    case "years":
      return `${num(raw, 1)} г.`;
    case "months":
      return `${num(raw, 1)} мес.`;
    case "share":
      return `${num(raw * 100, 1)}%`;
    case "flag":
      return raw ? "да" : "нет";
    default:
      return num(raw);
  }
}

/**
 * Почему получилась такая оценка.
 *
 * Жюри требует, чтобы логика решения была прозрачна: по каким данным
 * и почему вышел результат. Поэтому рядом с каждым признаком стоит его
 * значение и вклад в оценку — вправо риск повышается, влево понижается.
 * Числа берём из решения как есть, сами ничего не считаем.
 */
export default function Scoring({ decision }: { decision: Decision }) {
  const rows = FEATURES.filter((f) => f.key in decision.contributions).map((f) => ({
    ...f,
    raw: decision.features[f.key],
    weight: decision.contributions[f.key] ?? 0,
  }));
  const clipped = decision.clipping_warnings.map((w) => String(w.feature));
  const scale = Math.max(...rows.map((r) => Math.abs(r.weight)), 0.001);

  return (
    <section className="cb-card-white">
      <div className="uw-scoring-head">
        <Text view="accent-primary-large" tag="h2">
          Оценка риска
        </Text>
        <Grade grade={decision.grade} pd={decision.pd} />
      </div>

      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 8 }}>
        Политика {decision.policy_version}
        {decision.model_version && ` · модель ${decision.model_version}`}
      </Text>

      <table className="uw-features">
        <thead>
          <tr>
            <th>Признак</th>
            <th>Значение</th>
            <th>Вклад в оценку</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const width = `${(Math.abs(r.weight) / scale) * 50}%`;
            const risky = r.weight > 0;
            return (
              <tr key={r.key}>
                <td>
                  <span className="uw-feature-title">{r.title}</span>
                  <span className="uw-feature-hint">{r.hint}</span>
                </td>
                <td className="uw-feature-value">{value(r.raw, r.format)}</td>
                <td>
                  <span className="uw-bar" title={r.weight.toFixed(3)}>
                    <span className="uw-bar-axis" />
                    <span
                      className="uw-bar-fill"
                      data-risky={risky}
                      style={risky ? { left: "50%", width } : { right: "50%", width }}
                    />
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {decision.lgd !== null && decision.product_pd_max !== null && (
        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 12 }}>
          LGD {pct(decision.lgd)} · граница отказа для продукта — PD {pct(decision.product_pd_max)}
          {decision.pd_at_requested_terms !== null &&
            ` · на запрошенных условиях PD была бы ${pct(decision.pd_at_requested_terms)}`}
        </Text>
      )}
      {clipped.length > 0 && (
        <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 8 }}>
          Вне диапазона обучения, модель взяла границу:{" "}
          {clipped.map((k) => FEATURES.find((f) => f.key === k)?.title ?? k).join(", ")}
        </Text>
      )}

      <div className="uw-legend">
        <span>
          <i data-risky="false" /> снижает риск
        </span>
        <span>
          <i data-risky="true" /> повышает риск
        </span>
      </div>

      {decision.stop_factors.length > 0 && (
        <div className="uw-stop">
          <Text view="accent-primary-medium" tag="h3">
            Стоп-факторы
          </Text>
          <ul className="cb-list" style={{ marginTop: 8 }}>
            {decision.stop_factors.map((sf, i) => (
              <li key={i}>{String(sf.title ?? sf.code ?? JSON.stringify(sf))}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
