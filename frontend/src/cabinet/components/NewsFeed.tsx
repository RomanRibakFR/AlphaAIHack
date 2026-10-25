import { Text } from "../../ui/primitives";
import { NEWS, NEWS_SOURCE, type NewsItem } from "../content";

const SECONDARY = "var(--color-light-text-secondary)";

/** «23 октября» — без года, лента всегда свежая. */
function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

/**
 * Лента новостей в кабинете.
 *
 * Кейс требует показать, что лента меняется под клиента, поэтому у части
 * новостей есть подпись, кому они адресованы: по ОКВЭД и по размеру бизнеса.
 * Отраслевая новость подставляется по виду деятельности компании.
 */
export default function NewsFeed({ okvedName }: { okvedName?: string | null }) {
  const industry: NewsItem | null = okvedName
    ? {
        date: "2026-10-22",
        title: `Что меняется для отрасли «${okvedName}» в этом квартале`,
        audience: "по вашему ОКВЭД",
      }
    : null;

  const items = industry ? [industry, ...NEWS] : NEWS;

  return (
    <section className="cb-card-white">
      <div className="cb-news-head">
        <Text view="accent-primary-large" tag="h2">
          Новости
        </Text>
        <a className="cb-news-all" href={NEWS_SOURCE} target="_blank" rel="noreferrer">
          Все новости
        </a>
      </div>

      <div className="cb-news">
        {items.slice(0, 4).map((n) => (
          <article key={n.title} className="cb-news-item">
            <div className="cb-news-meta">
              <span>{shortDate(n.date)}</span>
              {n.audience && (
                <>
                  <span className="cb-news-dot">·</span>
                  <span className="cb-news-audience">{n.audience}</span>
                </>
              )}
            </div>
            <Text view="primary-small" style={{ marginTop: 4 }}>
              {n.title}
            </Text>
          </article>
        ))}
      </div>

      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 16 }}>
        Подборка собрана по виду деятельности и размеру бизнеса. Тексты демонстрационные.
      </Text>
    </section>
  );
}
