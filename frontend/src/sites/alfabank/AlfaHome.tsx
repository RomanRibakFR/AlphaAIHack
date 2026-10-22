/** Клон главной https://alfabank.ru на нашей дизайн-системе.
 *
 *  Зачем он здесь: это рабочий образец того, как из токенов и компонентов
 *  Альфы собираются реальные экраны. Любую секцию можно скопировать
 *  в кабинет и подменить контент.
 *
 *  Разделы и размеры — с живой страницы (замеры при ширине 1280).
 *  Чего нет и почему — в docs/design-system/README.md.
 */
import { useEffect, useRef, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import AlfaLogo from "../../ui/AlfaLogo";
import Calculator from "./sections/Calculator";
import { CardPure, Container, Grid, Text } from "../../ui/primitives";
import {
  ABOUT_TABS,
  APP_PROMO,
  FOOTER_COLUMNS,
  FOOTER_LEGAL,
  HERO,
  HERO_SIDE,
  HERO_SMALL,
  NAV,
  PARTNERS,
  PRODUCT_TABS,
  PROMO_CARDS,
  RATES,
  SERVICES,
  SMART_SEARCH,
  SUPPORT,
} from "./content";
import "./home.css";

const INVERTED = "var(--color-light-text-primary-inverted)";
const INVERTED_2 = "var(--color-light-text-secondary-inverted)";
const SECONDARY = "var(--color-light-text-secondary)";

/** alfabank.ru отдаёт десктопный макет фиксированной ширины:
 *  <meta name="viewport" content="width=1280">. На узком экране браузер
 *  не перестраивает вёрстку, а масштабирует её целиком. Повторяем это
 *  на время показа клона и возвращаем прежний viewport при уходе со страницы. */
function useFixedViewport(width = 1280) {
  useEffect(() => {
    const meta = document.querySelector<HTMLMetaElement>('meta[name="viewport"]');
    if (!meta) return;
    const previous = meta.content;
    meta.content = `width=${width}`;
    return () => {
      meta.content = previous;
    };
  }, [width]);
}

/** Переносы в текстах контента заданы через \n — сохраняем их как в оригинале. */
function Lines({ text }: { text: string }) {
  const parts = text.split("\n");
  return (
    <>
      {parts.map((p, i) => (
        <span key={i}>
          {p}
          {i < parts.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}

function Header() {
  return (
    <header className="ab-header">
      <Container>
        <div className="ab-header-row">
          <a href="https://alfabank.ru/" aria-label="Альфа-Банк">
            <AlfaLogo height={40} />
          </a>
          <nav className="ab-nav">
            {NAV.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </nav>
          <div className="ab-header-right">
            <Button view="secondary" size={40} href="https://alfabank.ru/lp/retail/startclient/">
              Стать клиентом
            </Button>
            <Button view="accent" size={40}>
              Войти
            </Button>
          </div>
        </div>
      </Container>
    </header>
  );
}

function Hero() {
  return (
    <Container>
      <div className="ab-bento">
        <div className="ab-bento-main">
          <a className="ab-hero" href={HERO.href} style={{ background: HERO.bg }}>
            {/* На сайте в геро крутится видео, постер — тот же кадр. */}
            <video
              className="ab-hero-media"
              src={HERO.video}
              poster={HERO.media}
              autoPlay
              muted
              loop
              playsInline
            />
            <div className="ab-hero-body">
              <Text view="promo-hero" tag="h1" color={INVERTED}>
                {HERO.title.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </Text>
              <Text view="primary-small" color={INVERTED_2} style={{ marginTop: 16 }}>
                {HERO.subtitle.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </Text>
              <div className="ab-hero-cta">
                <Button view="accent" size={48}>
                  {HERO.cta}
                </Button>
              </div>
            </div>
          </a>

          <div className="ab-bento-row">
            {HERO_SMALL.map((card) => (
              <CardPure
                key={card.href}
                href={card.href}
                background={card.img}
                backgroundColor={card.bg}
                backgroundPosition="right center"
                borderRadius={24}
              >
                <div className="ab-bento-card-body">
                  <Text view="promo-card">
                    <Lines text={card.title} />
                  </Text>
                </div>
              </CardPure>
            ))}
          </div>
        </div>

        <div className="ab-bento-side">
          {HERO_SIDE.map((card, i) => (
            <CardPure
              key={card.href}
              href={card.href}
              height={273}
              background={card.img}
              backgroundColor={card.bg}
              backgroundPosition="center bottom"
              borderRadius={24}
            >
              <div style={{ padding: 20, textAlign: "center" }}>
                <Text view="accent-primary-large" color={i === 1 ? INVERTED : undefined}>
                  <Lines text={card.title} />
                </Text>
              </div>
            </CardPure>
          ))}
        </div>
      </div>
    </Container>
  );
}

function Products() {
  const [active, setActive] = useState(0);
  const tab = PRODUCT_TABS[active];

  return (
    <section className="ab-section">
      <div className="ab-section-head">
        <Text view="promo-h2" tag="h2">
          Выбирайте лучшее
        </Text>
        <div className="ab-tabs" role="tablist">
          {PRODUCT_TABS.map((t, i) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={i === active}
              className="ab-tab"
              onClick={() => setActive(i)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab.note && (
        <Text view="primary-small" color={SECONDARY} style={{ marginTop: -24, marginBottom: 24 }}>
          {tab.note}
        </Text>
      )}

      <Grid columns={4}>
        {tab.cards.map((card) => (
          <a
            key={card.href + card.title}
            className="ab-product"
            href={card.href}
            style={{ backgroundImage: `url(${card.img})` }}
          >
            <Text view="promo-card">
              <Lines text={card.title} />
            </Text>
            {card.subtitle && (
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 4 }}>
                {card.subtitle}
              </Text>
            )}
          </a>
        ))}
      </Grid>
    </section>
  );
}

function PromoCarousel() {
  const track = useRef<HTMLDivElement>(null);
  const scrollBy = (dir: 1 | -1) => track.current?.scrollBy({ left: dir * (364 + 24) * 3, behavior: "smooth" });

  return (
    <section className="ab-section">
      <div className="ab-section-head">
        <Text view="promo-h2" tag="h2">
          Получайте больше
          <br />с Альфа-Банком
        </Text>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="ab-arrow" aria-label="Назад" onClick={() => scrollBy(-1)}>
            ‹
          </button>
          <button className="ab-arrow" aria-label="Вперёд" onClick={() => scrollBy(1)}>
            ›
          </button>
        </div>
      </div>

      <div className="ab-carousel" ref={track}>
        {PROMO_CARDS.map((card) => (
          <a
            key={card.href + card.title}
            className="ab-promo"
            href={card.href}
            style={{ backgroundImage: `url(${card.img})` }}
          >
            <Text view="accent-primary-large">
              <Lines text={card.title} />
            </Text>
            {card.subtitle && (
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 6 }}>
                <Lines text={card.subtitle} />
              </Text>
            )}
          </a>
        ))}
      </div>
    </section>
  );
}

function Partners() {
  return (
    <section className="ab-section">
      <CardPure
        backgroundColor={PARTNERS.bg}
        background={PARTNERS.img}
        backgroundPosition="right bottom"
        borderRadius={32}
        style={{ minHeight: 312 }}
      >
        <div style={{ padding: 40, maxWidth: 520 }}>
          <Text view="promo-h2" tag="h2">
            {PARTNERS.title.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </Text>
          <Text view="primary-small" style={{ marginTop: 16 }}>
            {PARTNERS.text}
          </Text>
          <div style={{ marginTop: 24 }}>
            <Button view="accent" size={48} href={PARTNERS.href}>
              {PARTNERS.cta}
            </Button>
          </div>
        </div>
      </CardPure>
    </section>
  );
}

function Services() {
  return (
    <section className="ab-section">
      <Text view="promo-h2" tag="h2" style={{ marginBottom: 40 }}>
        Сервисы
      </Text>
      <Grid columns={2}>
        <div style={{ display: "grid", gap: 24, alignContent: "start" }}>
          {/* Виджет курсов на сайте ходит в их API; здесь — снятые значения. */}
          <div
            style={{
              borderRadius: "var(--alfa-tile-radius)",
              background: "var(--color-light-base-bg-secondary)",
              padding: 24,
            }}
          >
            <Text view="accent-primary-large">Курсы валют</Text>
            <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
              {RATES.map((r) => (
                <div key={r.code} style={{ display: "flex", justifyContent: "space-between" }}>
                  <Text view="primary-small" color={SECONDARY}>
                    {r.code}
                  </Text>
                  <Text view="primary-small">
                    {r.buy} / {r.sell} ₽
                  </Text>
                </div>
              ))}
            </div>
            <Text view="secondary-small" color={SECONDARY} style={{ marginTop: 16 }}>
              Информация о курсах справочная и может меняться в течение дня.
            </Text>
          </div>

          <a className="ab-service" href={SUPPORT.href}>
            <div>
              <Text view="accent-primary-medium">{SUPPORT.title}</Text>
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 4 }}>
                {SUPPORT.subtitle}
              </Text>
            </div>
            <img src={SUPPORT.img} alt="" />
          </a>
        </div>

        <div style={{ display: "grid", gap: 24, alignContent: "start" }}>
          {SERVICES.map((card) => {
            const dark = Boolean(card.bg);
            return (
              <a
                key={card.href}
                className="ab-service"
                href={card.href}
                style={card.bg ? { background: card.bg } : undefined}
              >
                <div>
                  <Text view="accent-primary-medium" color={dark ? INVERTED : undefined}>
                    {card.title}
                  </Text>
                  <Text
                    view="primary-small"
                    color={dark ? INVERTED_2 : SECONDARY}
                    style={{ marginTop: 4 }}
                  >
                    {card.subtitle}
                  </Text>
                </div>
                <img src={card.img} alt="" />
              </a>
            );
          })}
        </div>
      </Grid>
    </section>
  );
}

function About() {
  const [active, setActive] = useState(0);
  const tab = ABOUT_TABS[active];

  return (
    <section className="ab-section">
      <div className="ab-section-head">
        <Text view="promo-h2" tag="h2">
          О банке
        </Text>
        <div className="ab-tabs" role="tablist">
          {ABOUT_TABS.map((t, i) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={i === active}
              className="ab-tab"
              onClick={() => setActive(i)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <Grid columns={2}>
        <CardPure
          href={tab.cards[0].href}
          background={tab.cards[0].img}
          backgroundColor="var(--color-light-base-bg-secondary)"
          backgroundPosition="center bottom"
          borderRadius={24}
          style={{ height: 444 }}
        >
          <div style={{ padding: 24, textAlign: "center" }}>
            <Text view="accent-primary-large">{tab.cards[0].title}</Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 4 }}>
              {tab.cards[0].subtitle}
            </Text>
          </div>
        </CardPure>

        <div style={{ display: "grid", gap: 24, gridTemplateRows: "1fr 1fr" }}>
          {tab.cards.slice(1).map((card) => (
            <CardPure
              key={card.href}
              href={card.href}
              background={card.img}
              backgroundColor="var(--color-light-base-bg-secondary)"
              backgroundPosition="right bottom"
              borderRadius={24}
            >
              <div style={{ padding: 24, maxWidth: "65%" }}>
                <Text view="accent-primary-medium">{card.title}</Text>
                <Text view="primary-small" color={SECONDARY} style={{ marginTop: 4 }}>
                  {card.subtitle}
                </Text>
              </div>
            </CardPure>
          ))}
        </div>
      </Grid>
    </section>
  );
}

function SmartSearch() {
  return (
    <section className="ab-section">
      <CardPure
        background={SMART_SEARCH.img}
        backgroundColor="#1c1c1e"
        backgroundPosition="right center"
        borderRadius={32}
        style={{ minHeight: 244 }}
      >
        <div style={{ padding: 40, maxWidth: 620 }}>
          <Text view="promo-h3" color={INVERTED}>
            {SMART_SEARCH.title.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </Text>
          <Text view="primary-small" color={INVERTED_2} style={{ marginTop: 12 }}>
            {SMART_SEARCH.text}
          </Text>
          <div style={{ marginTop: 24 }}>
            <Button view="secondary" size={48} href={SMART_SEARCH.href}>
              {SMART_SEARCH.cta}
            </Button>
          </div>
        </div>
      </CardPure>
    </section>
  );
}

function Footer() {
  return (
    <footer className="ab-footer">
      <Container>
        <div className="ab-app">
          <div style={{ flex: 1 }}>
            <Text view="promo-h3" color={INVERTED}>
              {APP_PROMO.title.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </Text>
            <Text view="primary-small" color={INVERTED_2} style={{ marginTop: 16, maxWidth: 420 }}>
              {APP_PROMO.text}
            </Text>
            <div style={{ display: "flex", gap: 12, marginTop: 32 }}>
              <Button view="secondary" size={48}>
                {APP_PROMO.primary}
              </Button>
              <Button view="transparent" size={48}>
                {APP_PROMO.secondary}
              </Button>
            </div>
          </div>
          <video
            className="ab-app-media"
            src={APP_PROMO.video}
            poster={APP_PROMO.poster}
            autoPlay
            muted
            loop
            playsInline
          />
        </div>

        <div className="ab-footer-cols">
          {FOOTER_COLUMNS.map((col) => (
            <div className="ab-footer-col" key={col.head}>
              <h3>{col.head}</h3>
              {col.items.map(([label, href]) => (
                <a key={href + label} href={href}>
                  {label}
                </a>
              ))}
            </div>
          ))}
        </div>

        <Text view="secondary-small" color={INVERTED_2} style={{ marginTop: 48, maxWidth: 1140 }}>
          {FOOTER_LEGAL}
        </Text>
      </Container>
    </footer>
  );
}

export default function AlfaHome() {
  useFixedViewport(1280);

  return (
    <div className="ab-page">
      <Header />
      <Hero />
      <div className="ab-content">
        <Container>
          <Products />
          <Calculator />
          <PromoCarousel />
          <Partners />
          <Services />
          <About />
          <SmartSearch />
        </Container>
      </div>
      <Footer />
    </div>
  );
}
