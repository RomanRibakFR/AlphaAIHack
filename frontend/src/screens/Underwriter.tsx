/**
 * Рабочее место кредитного специалиста.
 *
 * Полностью заглушка: на бэкенде нет ни выборки заявок на ручной разбор,
 * ни ручек решения. В statuses.py роль underwriter уже есть и ей разрешены
 * переходы manual_review → approved / counter_offer / rejected / needs_info,
 * но API для них не написан.
 */
export default function Underwriter() {
  return (
    <>
      <section className="stub" data-why="API для сотрудника банка нет совсем">
        <h2>Очередь на ручную проверку</h2>
        <p>Чтобы этот экран заработал, нужно от бэкенда:</p>
        <ul>
          <li>
            <code>GET /api/underwriter/applications?status=manual_review</code> — очередь заявок
          </li>
          <li>
            <code>GET /api/underwriter/applications/{"{id}"}</code> — карточка с внутренними
            данными: результаты внешних проверок, баллы скоринга, сработавшие факторы и стоп-факторы
          </li>
          <li>
            <code>POST /api/underwriter/applications/{"{id}"}/decision</code> — решение с
            комментарием: одобрить, предложить другие условия, отказать, запросить дополнение
          </li>
          <li>роль и авторизация: клиент не должен попадать на этот экран</li>
        </ul>
      </section>

      <section>
        <h3>Как это должно выглядеть</h3>
        <table>
          <thead>
            <tr>
              <th>№</th>
              <th>Компания</th>
              <th>Продукт</th>
              <th>Сумма</th>
              <th>Балл скоринга</th>
              <th>Почему попало на разбор</th>
              <th>Решение</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>—</td>
              <td>ИП Смирнова Анна Сергеевна</td>
              <td>Оборотный кредит</td>
              <td>1 500 000 ₽</td>
              <td>—</td>
              <td>нет кредитной истории</td>
              <td className="muted">кнопки решения</td>
            </tr>
          </tbody>
        </table>
        <p className="muted">Строка выдуманная, данные взяты из тестового набора.</p>
      </section>
    </>
  );
}
