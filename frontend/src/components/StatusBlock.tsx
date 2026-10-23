import type { StatusView } from "../api/types";

/** Статус в том виде, в каком его видит клиент: заголовок + подсказка «что дальше». */
export default function StatusBlock({ status }: { status: StatusView }) {
  return (
    <section>
      <h2>{status.title}</h2>
      <p>{status.hint}</p>
      <p className="muted">
        внутренний код: <code>{status.code}</code> (на проде клиенту не показываем)
      </p>
    </section>
  );
}
