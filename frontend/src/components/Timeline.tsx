import type { Actor, HistoryItem } from "../api/types";
import { dateTime } from "../lib/format";

const ACTOR_NAME: Record<Actor, string> = {
  client: "клиент",
  system: "система",
  underwriter: "сотрудник банка",
};

/** История переходов. Пока показываем как есть — на проде часть шагов надо склеить. */
export default function Timeline({ history }: { history: HistoryItem[] }) {
  if (history.length === 0) {
    return (
      <section>
        <h3>История</h3>
        <p className="muted">Пока ничего не происходило.</p>
      </section>
    );
  }

  return (
    <section>
      <h3>История</h3>
      <table>
        <thead>
          <tr>
            <th>Когда</th>
            <th>Переход</th>
            <th>Кто</th>
            <th>Комментарий</th>
          </tr>
        </thead>
        <tbody>
          {history.map((h, i) => (
            <tr key={i}>
              <td>{dateTime(h.created_at)}</td>
              <td>
                <code>{h.from_status ?? "—"}</code> → <code>{h.to_status}</code>
              </td>
              <td>{ACTOR_NAME[h.actor]}</td>
              <td>{h.comment ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
