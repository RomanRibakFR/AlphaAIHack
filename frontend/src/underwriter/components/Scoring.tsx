import type { Decision } from "../../api/types";
import { Text } from "../../ui/primitives";
import { money, months } from "../../lib/format";
import { FEATURES } from "../content";
import Grade from "./Grade";

const SECONDARY = "var(--color-light-text-secondary)";

function value(raw: number | undefined, format: string): string {
  if (raw === undefined) return "—";
  switch (format) {
    case "months":
      return months(raw);
    case "money":
      return money(String(raw));
    case "share":
      return `${(raw * 100).toLocaleString("ru-RU", { maximumFractionDigits: 1 })}%`;
    case "count":
      return String(raw);
    default:
      return raw.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
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
  const rows = FEATURES.map((f) => ({
    ...f,
    raw: decision.features[f.key],
    weight: decision.contributions[f.contribution] ?? 0,
  }));
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
