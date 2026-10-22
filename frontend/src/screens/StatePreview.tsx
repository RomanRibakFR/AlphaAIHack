import StatusBlock from "../components/StatusBlock";
import type { StatusCode } from "../api/types";

/**
 * Инструмент для вёрстки, не часть кабинета.
 *
 * Бэкенд не умеет доводить заявку дальше «Рассматриваем», поэтому увидеть
 * остальные 11 состояний живьём нельзя. Здесь они все сразу.
 *
 * ВНИМАНИЕ: тексты скопированы из backend/app/statuses.py (CLIENT_VIEW) и могут
 * разойтись с бэкендом. Боевые экраны их не используют — там берём status.title
 * из ответа API. Правильнее попросить эндпоинт GET /api/statuses.
 */
const CLIENT_VIEW: Record<StatusCode, { title: string; hint: string; group: string }> = {
  draft: {
    title: "Черновик",
    hint: "Заполните заявку и отправьте её в банк",
    group: "у клиента",
  },
  submitted: {
    title: "Рассматриваем заявку",
    hint: "Проверяем данные, обычно это занимает пару минут",
    group: "внутри банка (клиенту не видно)",
  },
  validation: {
    title: "Рассматриваем заявку",
    hint: "Проверяем данные, обычно это занимает пару минут",
    group: "внутри банка (клиенту не видно)",
  },
  external_checks: {
    title: "Рассматриваем заявку",
    hint: "Проверяем данные, обычно это занимает пару минут",
    group: "внутри банка (клиенту не видно)",
  },
  scoring: {
    title: "Рассматриваем заявку",
    hint: "Принимаем решение",
    group: "внутри банка (клиенту не видно)",
  },
  manual_review: {
    title: "Рассматривает специалист",
    hint: "Заявку смотрит кредитный специалист, обычно до 1 рабочего дня",
    group: "у сотрудника банка",
  },
  needs_info: {
    title: "Нужно дополнить",
    hint: "Банку не хватает данных — посмотрите, что нужно добавить",
    group: "вернулось клиенту",
  },
  approved: {
    title: "Одобрено",
    hint: "Ознакомьтесь с условиями и примите предложение",
    group: "решение принято",
  },
  counter_offer: {
    title: "Есть предложение",
    hint: "Можем выдать кредит на других условиях",
    group: "решение принято",
  },
  signing: {
    title: "Подписание",
    hint: "Проверьте договор и подпишите его",
    group: "оформление",
  },
  issued: {
    title: "Кредит выдан",
    hint: "Деньги на счёте, график платежей в карточке заявки",
    group: "финал",
  },
  rejected: {
    title: "Отказ",
    hint: "К сожалению, сейчас банк не может выдать кредит",
    group: "финал",
  },
  declined_by_client: {
    title: "Вы отказались",
    hint: "Предложение отклонено",
    group: "финал",
  },
  withdrawn: { title: "Отозвана", hint: "Вы отозвали заявку", group: "финал" },
  expired: {
    title: "Истекла",
    hint: "Срок ответа истёк, можно подать новую заявку",
    group: "финал",
  },
};

const CODES = Object.keys(CLIENT_VIEW) as StatusCode[];

export default function StatePreview() {
  return (
    <>
      <section className="stub" data-why="страница для нас, в кабинете её не будет">
        <h2>Все 15 состояний заявки</h2>
        <p>
          Пока нет логики решения, живьём достижимы только <code>draft</code>,{" "}
          <code>submitted</code> и <code>withdrawn</code>. Остальные — здесь, чтобы было что
          верстать.
        </p>
      </section>

      <section>
        <h3>Таблица</h3>
        <table>
          <thead>
            <tr>
              <th>Код</th>
              <th>Что видит клиент</th>
              <th>Подсказка</th>
              <th>Этап</th>
            </tr>
          </thead>
          <tbody>
            {CODES.map((code) => (
              <tr key={code}>
                <td>
                  <code>{code}</code>
                </td>
                <td>{CLIENT_VIEW[code].title}</td>
                <td>{CLIENT_VIEW[code].hint}</td>
                <td className="muted">{CLIENT_VIEW[code].group}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">
          Четыре внутренних статуса дают один и тот же заголовок «Рассматриваем заявку» — клиент не
          должен видеть внутреннюю кухню банка.
        </p>
      </section>

      <h3>Как выглядит блок статуса</h3>
      {CODES.map((code) => (
        <StatusBlock
          key={code}
          status={{ code, title: CLIENT_VIEW[code].title, hint: CLIENT_VIEW[code].hint }}
        />
      ))}
    </>
  );
}
