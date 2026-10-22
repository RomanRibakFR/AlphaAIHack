/** Витрина дизайн-системы Альфа-Банка: что доступно и как это выглядит.
 *
 *  Слева — официальные компоненты из @alfalab/core-components (тот самый
 *  публичный core-ds, на котором собран alfabank.ru).
 *  Справа — наши примитивы из src/ui, повторяющие вёрстку их главной.
 *
 *  Страница нужна, чтобы при сборке кабинета не гадать: открыл, посмотрел,
 *  скопировал кусок.
 */
import { useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Input } from "@alfalab/core-components/input";
import { Select } from "@alfalab/core-components/select";
import { Checkbox } from "@alfalab/core-components/checkbox";
import { Switch } from "@alfalab/core-components/switch";
import { Tag } from "@alfalab/core-components/tag";
import { Badge } from "@alfalab/core-components/badge";
import { Status } from "@alfalab/core-components/status";
import { Amount } from "@alfalab/core-components/amount";
import { Typography } from "@alfalab/core-components/typography";
import { CardPure, Container, Grid, Text } from "../ui/primitives";
import AlfaLogo from "../ui/AlfaLogo";

const COLORS: Array<[string, string, string]> = [
  ["--color-light-accent-primary", "#ef3124", "фирменный красный, кнопки и акценты"],
  ["--color-light-text-primary", "rgba(3,3,6,0.88)", "основной текст на светлом"],
  ["--color-light-text-secondary", "rgba(4,4,19,0.55)", "вторичный текст"],
  ["--color-light-text-primary-inverted", "rgba(255,255,255,0.94)", "основной текст на тёмном"],
  ["--color-light-text-secondary-inverted", "rgba(238,238,251,0.55)", "вторичный на тёмном"],
  ["--color-light-base-bg-primary", "#fff", "белый фон страницы"],
  ["--color-light-base-bg-secondary", "#f2f3f5", "подложка карточек"],
  ["--color-light-base-bg-primary-inverted", "#121213", "тёмные блоки: шапка, футер"],
  ["--color-light-text-negative", "#ec2d20", "ошибка, отказ"],
  ["--color-light-text-positive", "#0d9336", "успех, одобрено"],
  ["--color-light-text-attention", "#ea8313", "предупреждение"],
  ["--color-light-text-info", "#2a77ef", "информация"],
];

const PROMO: Array<[string, string]> = [
  ["--alfa-promo-lavender", "#dfbfff"],
  ["--alfa-promo-lilac", "#e9e0ff"],
  ["--alfa-promo-blue", "#5297ff"],
  ["--alfa-promo-navy", "#000058"],
  ["--alfa-promo-pink", "#ffcac7"],
  ["--alfa-promo-sky", "#e5ecff"],
];

const TYPE_SCALE = [
  ["promo-hero", "48 / 52 / 700", "заголовок геро-блока"],
  ["promo-h2", "40 / 48 / 700", "заголовок секции"],
  ["promo-h3", "30 / 36 / 700", "подзаголовок"],
  ["promo-card", "22 / 26 / 700", "заголовок карточки"],
  ["accent-primary-medium", "16 / 24 / 700", "акцент в тексте"],
  ["primary-medium", "16 / 24 / 400", "крупный текст"],
  ["primary-small", "14 / 20 / 400", "основной текст (самый частый на сайте)"],
  ["secondary-medium", "12 / 16 / 400", "подписи"],
  ["secondary-small", "11 / 16 / 400", "мелкие сноски"],
] as const;

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section style={{ border: "none", padding: 0, margin: "0 0 64px" }}>
      <Text view="promo-h3" tag="h2" style={{ marginBottom: hint ? 4 : 24 }}>
        {title}
      </Text>
      {hint && (
        <Text view="primary-small" color="var(--color-light-text-secondary)" style={{ marginBottom: 24 }}>
          {hint}
        </Text>
      )}
      {children}
    </section>
  );
}

export default function UiKit() {
  const [checked, setChecked] = useState(true);
  const [on, setOn] = useState(true);
  const [sum, setSum] = useState("1 000 000");

  return (
    <div className="alfa-on-light" style={{ paddingBottom: 96 }}>
      <Container>
        <header style={{ display: "flex", alignItems: "center", gap: 16, padding: "48px 0 40px" }}>
          <AlfaLogo height={44} />
          <div>
            <Text view="promo-h2" tag="h1">
              Дизайн-система
            </Text>
            <Text view="primary-medium" color="var(--color-light-text-secondary)">
              @alfalab/core-components + токены и примитивы с alfabank.ru
            </Text>
          </div>
        </header>

        <Section
          title="Цвета"
          hint="Токены из @alfalab/core-components-vars, тема bluetint — та же, что на alfabank.ru."
        >
          <Grid columns={3} gap={16}>
            {COLORS.map(([token, value, note]) => (
              <div
                key={token}
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  padding: 12,
                  borderRadius: 16,
                  background: "var(--color-light-base-bg-secondary)",
                }}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 12,
                    flex: "0 0 auto",
                    background: `var(${token})`,
                    boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.08)",
                  }}
                />
                <div style={{ minWidth: 0 }}>
                  <Text view="accent-primary-small" style={{ wordBreak: "break-all" }}>
                    {token.replace("--color-light-", "")}
                  </Text>
                  <Text view="secondary-medium" color="var(--color-light-text-secondary)">
                    {value} — {note}
                  </Text>
                </div>
              </div>
            ))}
          </Grid>

          <Text view="accent-primary-medium" style={{ margin: "32px 0 12px" }}>
            Промо-подложки карточек
          </Text>
          <Grid columns={6} gap={16}>
            {PROMO.map(([token, value]) => (
              <div key={token}>
                <div style={{ height: 72, borderRadius: 16, background: `var(${token})` }} />
                <Text view="secondary-medium" color="var(--color-light-text-secondary)" style={{ marginTop: 8 }}>
                  {value}
                </Text>
              </div>
            ))}
          </Grid>
        </Section>

        <Section title="Типографика" hint="Alfa Interface Sans — фирменный шрифт, скачан с их CDN. Размер / интерлиньяж / насыщенность.">
          <div style={{ display: "grid", gap: 20 }}>
            {TYPE_SCALE.map(([view, spec, note]) => (
              <div key={view} style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 24, alignItems: "baseline" }}>
                <div>
                  <Text view="accent-primary-small">{view}</Text>
                  <Text view="secondary-medium" color="var(--color-light-text-secondary)">
                    {spec} — {note}
                  </Text>
                </div>
                <Text view={view}>Съешь ещё этих мягких булок</Text>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Скругления" hint="Из токенов --border-radius-*. На главной чаще всего 32, 24 и 99 (pill).">
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[8, 10, 12, 16, 20, 24, 32, 64].map((r) => (
              <div key={r} style={{ textAlign: "center" }}>
                <div
                  style={{
                    width: 96,
                    height: 72,
                    borderRadius: r,
                    background: "var(--color-light-base-bg-secondary)",
                  }}
                />
                <Text view="secondary-medium" color="var(--color-light-text-secondary)" style={{ marginTop: 6 }}>
                  {r}px
                </Text>
              </div>
            ))}
          </div>
        </Section>

        <Section
          title="Кнопки"
          hint="Button из core-components. Главный CTA на сайте — view=accent (фирменный красный), view=primary чёрная."
        >
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <Button view="accent" size={48}>
              Отправить заявку
            </Button>
            <Button view="primary" size={48}>
              Подписать
            </Button>
            <Button view="secondary" size={48}>
              Сохранить черновик
            </Button>
            <Button view="outlined" size={48}>
              Отозвать
            </Button>
            <Button view="transparent" size={48}>
              Подробнее
            </Button>
            <Button view="text">Ссылка-кнопка</Button>
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginTop: 16 }}>
            <Button view="accent" size={48} loading>
              Отправляем
            </Button>
            <Button view="accent" size={48} disabled>
              Недоступно
            </Button>
            <Button view="accent" size={48} shape="rounded">
              Скруглённая
            </Button>
          </div>
          <Text view="accent-primary-small" style={{ margin: "24px 0 12px" }}>
            Размеры: высота в пикселях
          </Text>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            {([32, 40, 48, 56, 64, 72] as const).map((s) => (
              <Button key={s} view="accent" size={s}>
                {s}
              </Button>
            ))}
          </div>
          <Text view="secondary-medium" color="var(--color-light-text-secondary)" style={{ marginTop: 12 }}>
            В шапке alfabank.ru «Войти» — view=accent, size=40, скругление 10px.
          </Text>
        </Section>

        <Section title="Поля и управление" hint="То, из чего будет собрана форма заявки.">
          <Grid columns={3} gap={24} style={{ alignItems: "start" }}>
            <Input label="ИНН" placeholder="10 или 12 цифр" block />
            <Input
              label="Сумма кредита"
              value={sum}
              onChange={(_, { value }) => setSum(value)}
              rightAddons="₽"
              block
            />
            <Select
              label="Продукт"
              placeholder="Выберите продукт"
              options={[
                { key: "overdraft", content: "Овердрафт" },
                { key: "working", content: "Оборотный кредит" },
                { key: "invest", content: "Инвестиционный кредит" },
              ]}
              block
            />
          </Grid>
          <div style={{ display: "flex", gap: 32, marginTop: 24, alignItems: "center", flexWrap: "wrap" }}>
            <Checkbox label="Согласен с условиями" checked={checked} onChange={() => setChecked((v) => !v)} />
            <Switch label="Капитализация процентов" checked={on} onChange={() => setOn((v) => !v)} />
            <Tag view="filled" checked>
              6 месяцев
            </Tag>
            <Tag view="filled">1 год</Tag>
          </div>
        </Section>

        <Section title="Статусы и суммы" hint="Для статусов заявки и денежных значений есть готовые компоненты.">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 20 }}>
            <Status view="soft" color="green">
              Одобрена
            </Status>
            <Status view="soft" color="orange">
              Ручная проверка
            </Status>
            <Status view="soft" color="red">
              Отказ
            </Status>
            <Status view="soft" color="blue">
              Рассматриваем
            </Status>
            <Status view="soft" color="grey">
              Черновик
            </Status>
            <Badge view="count" height={24} content={3} />
          </div>
          <Typography.Title tag="div" view="small" font="system">
            <Amount value={135000000} minority={100} currency="RUR" />
          </Typography.Title>
        </Section>

        <Section
          title="CardPure"
          hint="Примитив карточки с alfabank.ru: картинка-фон, цвет подложки, скругление. Картинки — настоящие, с их CDN."
        >
          <Grid columns={4} gap={24}>
            <CardPure
              height={298}
              background="/alfa/img/D_CardPromo_267_298_vertical_dc.png"
              backgroundColor="#f2f3f5"
              backgroundPosition="center bottom"
            >
              <div style={{ padding: "24px 20px", textAlign: "center" }}>
                <Text view="promo-card">Дебетовые карты</Text>
                <Text view="primary-small" color="var(--color-light-text-secondary)" style={{ marginTop: 4 }}>
                  Суперкэшбэк до 100%
                </Text>
              </div>
            </CardPure>
            <CardPure
              height={298}
              background="/alfa/img/CardPromo_267x298_121123-4.png"
              backgroundColor="#f2f3f5"
              backgroundPosition="center bottom"
            >
              <div style={{ padding: "24px 20px", textAlign: "center" }}>
                <Text view="promo-card">Кредиты</Text>
                <Text view="primary-small" color="var(--color-light-text-secondary)" style={{ marginTop: 4 }}>
                  Оформление онлайн
                </Text>
              </div>
            </CardPure>
            <CardPure
              height={298}
              background="/alfa/img/D_MainBento_267x273-investments-base.png"
              backgroundColor="#5297ff"
              backgroundPosition="center bottom"
            >
              <div style={{ padding: "24px 20px" }}>
                <Text view="promo-card" color="var(--color-light-text-primary-inverted)">
                  Инвестируйте
                  <br />и зарабатывайте
                </Text>
              </div>
            </CardPure>
            <CardPure
              height={298}
              backgroundColor="#dfbfff"
              background="/alfa/img/D_MainBento_412x128_020925.png"
              backgroundPosition="right bottom"
            >
              <div style={{ padding: "24px 20px" }}>
                <Text view="promo-card">Кредит наличными</Text>
              </div>
            </CardPure>
          </Grid>
        </Section>

        <Section title="Тёмный блок" hint="Шапка, геро и футер сайта лежат на #121213, текст инвертируется.">
          <div className="alfa-on-dark" style={{ borderRadius: 32, padding: 40 }}>
            <Text view="promo-h3" color="var(--color-light-text-primary-inverted)">
              Умный кредитный кабинет
            </Text>
            <Text
              view="primary-medium"
              color="var(--color-light-text-secondary-inverted)"
              style={{ marginTop: 8, maxWidth: 520 }}
            >
              Решение по заявке онлайн, без визита в отделение и бумажных справок
            </Text>
            <div style={{ marginTop: 24 }}>
              <Button view="primary">Подать заявку</Button>
            </div>
          </div>
        </Section>
      </Container>
    </div>
  );
}
