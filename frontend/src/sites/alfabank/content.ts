/** Контент главной alfabank.ru — снят с живой страницы 23 октября 2026 года.
 *
 *  Тексты, ссылки и имена картинок настоящие. Картинки скачаны с их CDN
 *  в /public/alfa/img, соответствие «источник → файл» описано
 *  в docs/design-system/README.md.
 *
 *  Внешние ссылки оставлены на alfabank.ru: это чужие страницы, их мы не клонируем.
 */

export const IMG = "/alfa/img";

export type Card = {
  title: string;
  subtitle?: string;
  href: string;
  img: string;
  bg?: string;
};

/* ——— шапка ——— */
export const NAV = [
  { label: "Частным лицам", href: "https://alfabank.ru/" },
  { label: "Малому бизнесу и ИП", href: "https://alfabank.ru/sme/" },
  { label: "Среднему и крупному бизнесу", href: "https://alfabank.ru/corporate/" },
];

/* ——— геро-бенто ——— */
export const HERO = {
  title: ["Карта для маленьких", "супергероев"],
  subtitle: ["Бесплатная карта с любимыми", "Леди Баг и Супер-Котом"],
  cta: "Заказать карту",
  href: "https://alfabank.ru/everyday/debit-cards/childcard/",
  bg: "#ef3124",
  media: `${IMG}/Bento_Primary_Static-ladybug-16092026.jpg`,
  video: "https://alfabank.servicecdn.ru/site-upload/02/b6/1449/D-850x420-ladybug-16092026.mp4",
};

export const HERO_SMALL: Card[] = [
  {
    title: "Кредит наличными",
    href: "https://alfabank.ru/get-money/credit/credit-cash/#form",
    img: `${IMG}/D_MainBento_412x128_020925.png`,
    bg: "#dfbfff",
  },
  {
    title: "Привилегии\nот Alfa Only",
    href: "https://alfabank.ru/everyday/package/premium/",
    img: `${IMG}/D_MainBento_412x128_150825.png`,
    bg: "#e9e0ff",
  },
];

export const HERO_SIDE: Card[] = [
  {
    title: "Бесплатная\nАльфа‑Карта",
    href: "https://alfabank.ru/everyday/debit-cards/alfacard/",
    img: `${IMG}/D_MainBento_267x273_240725.png`,
    bg: "#2bd9d0",
  },
  {
    title: "Инвестируйте\nи зарабатывайте",
    href: "https://alfabank.ru/make-money/investments/",
    img: `${IMG}/D_MainBento_267x273-investments-base.png`,
    bg: "#5297ff",
  },
];

/* ——— «Выбирайте лучшее»: три вкладки ——— */
export const PRODUCT_TABS: Array<{ id: string; label: string; note?: string; cards: Card[] }> = [
  {
    id: "retail",
    label: "Для всех",
    cards: [
      { title: "Дебетовые карты", subtitle: "Суперкэшбэк до 100%", href: "https://alfabank.ru/everyday/debit-cards/", img: `${IMG}/D_CardPromo_267_298_vertical_dc.png` },
      { title: "Кредитные карты", subtitle: "Обслуживание 0 ₽", href: "https://alfabank.ru/get-money/credit-cards/", img: `${IMG}/D_CardPromo_267x298_11082026-kk.jpg` },
      { title: "Кредиты", subtitle: "Оформление онлайн", href: "https://alfabank.ru/get-money/", img: `${IMG}/CardPromo_267x298_121123-4.png` },
      { title: "Накопления", subtitle: "Доход с первого месяца", href: "https://alfabank.ru/make-money/", img: `${IMG}/CardPromo_267x298_121123-2.png` },
      { title: "Инвестиции", subtitle: "Инвестируйте и зарабатывайте", href: "https://alfabank.ru/make-money/investments/", img: `${IMG}/D_CardPromo_267x298-15122025.png` },
      { title: "Мобильная связь", subtitle: "Безлимитный интернет", href: "https://alfabank.ru/mobile/", img: `${IMG}/D_CardPromo_267x298_MVNO.png` },
      { title: "Alfa Only", subtitle: "Ваш премиальный сервис", href: "https://alfabank.ru/everyday/package/premium/", img: `${IMG}/D_CardPromo_267x298_071024.png` },
      { title: "Для детей и семьи", subtitle: "Карты с кэшбэком", href: "https://alfabank.ru/everyday/family/", img: `${IMG}/D_CardPromo_267x298_120924.png` },
    ],
  },
  {
    id: "sme",
    label: "Малому бизнесу",
    note: "Для компаний с оборотом до 500 млн ₽ в год",
    cards: [
      { title: "Регистрация\nбизнеса", subtitle: "Онлайн за 0 ₽", href: "https://alfabank.ru/sme/start/", img: `${IMG}/D_CardPromo_267x298_221223-8.jpg` },
      { title: "Счёт для бизнеса", subtitle: "Бесплатно", href: "https://alfabank.ru/sme/tariffs/nullforservice/", img: `${IMG}/D_CardPromo_267x298_221223-1.jpg` },
      { title: "Кредиты", subtitle: "На развитие бизнеса", href: "https://alfabank.ru/sme/profits-new/", img: `${IMG}/D_CardPromo_267x298_3_18042025.png` },
      { title: "Эквайринг", subtitle: "Комиссия от 1%", href: "https://alfabank.ru/sme/payservice/", img: `${IMG}/D_CardPromo_267x298_221223-10.jpg` },
      { title: "Карты", subtitle: "С кэшбэком до 10%", href: "https://alfabank.ru/sme/cards/", img: `${IMG}/D_CardPromo_267x298_5_18042025.png` },
      { title: "Депозиты", subtitle: "Онлайн от 1 дня", href: "https://alfabank.ru/sme/deposits/", img: `${IMG}/D_CardPromo_267x298_dep.png` },
      { title: "Отраслевые решения", subtitle: "Для любого бизнеса", href: "https://alfabank.ru/sme/specialoffer/", img: `${IMG}/D_CardPromo_267x298_221223-6.jpg` },
      { title: "Всё для малого бизнеса", href: "https://alfabank.ru/sme/", img: `${IMG}/D_CardPromo_267x298_221223-7.jpg` },
    ],
  },
  {
    id: "corp",
    label: "Крупному бизнесу",
    note: "Для компаний с оборотом от 500 млн ₽ в год",
    cards: [
      { title: "Расчётный счёт", href: "https://alfabank.ru/corporate/rko/start/", img: `${IMG}/D_CardPromo_267x298_221223-8.jpg` },
      { title: "Кредиты", href: "https://alfabank.ru/corporate/new-kredit/", img: `${IMG}/D_CardPromo_267x298_221223-9.jpg` },
      { title: "Эквайринг", href: "https://alfabank.ru/sme/payservice/", img: `${IMG}/D_CardPromo_267x298_221223-10.jpg` },
      { title: "Факторинг", href: "https://alfabank.ru/corporate/credit/factoring/", img: `${IMG}/D_CardPromo_267x298_221223-11.jpg` },
      { title: "Зарплатный проект", href: "https://alfabank.ru/corporate/salaryproject/", img: `${IMG}/D_CardPromo_267x298_221223-12.jpg` },
      { title: "ВЭД", href: "https://alfabank.ru/corporate/ved/ved_konsalting/", img: `${IMG}/D_CardPromo_267x298_221223-13.jpg` },
      { title: "Инвестбанк", href: "https://alfabank.ru/corporate/investments/", img: `${IMG}/D_CardPromo_267x298_221223-14.jpg` },
      { title: "Всё для крупного бизнеса", href: "https://alfabank.ru/corporate/", img: `${IMG}/D_CardPromo_267x298_221223-15.jpg` },
    ],
  },
];

/* ——— «Получайте больше с Альфа-Банком»: карусель 364×364 ——— */
export const PROMO_CARDS: Card[] = [
  { title: "+3000 ₽ за перевод пенсии", subtitle: "Получайте деньги на Альфа‑Карту и пользуйтесь привилегиями", href: "https://alfabank.ru/everyday/pensioner/pensiya/", img: `${IMG}/D_CardSlot_364x364.png` },
  { title: "Платим\nза рекомендации", subtitle: "Приглашайте друзей в Альфа-Банк и зарабатывайте", href: "https://alfabank.ru/lp/retail/friends/", img: `${IMG}/D_CardPromo_328x195_DFBFFF-big.png` },
  { title: "Снизили цены на слитки", subtitle: "Удачный момент для покупки. Чем больше объём, тем выгоднее", href: "https://alfabank.ru/make-money/metall/bars/", img: `${IMG}/D_CardSlot_364x364-bars.png` },
  { title: "Высокие ставки по Альфа‑Вкладу", subtitle: "Растим ваши накопления\nв рублях и в юанях", href: "https://alfabank.ru/make-money/deposits/new-money/", img: `${IMG}/D_CardPromo_364x364_260724.png` },
  { title: "Альфа‑Карта с гравировкой", subtitle: "Закажите карту из лимитированной серии с кастомным дизайном", href: "https://alfabank.ru/everyday/debit-cards/?rp-tab=limit-cards", img: `${IMG}/D_CardPromo_364-364_25112025.png` },
  { title: "+1 категория кэшбэка", subtitle: "Получайте больше выгоды и привилегий с Альфа‑Смарт", href: "https://alfabank.ru/everyday/smart/", img: `${IMG}/D_CardPromo_364x364_190525.png` },
  { title: "Безопасные расчёты за 0 ₽", subtitle: "Поддержим любые ваши сделки с недвижимостью", href: "https://alfabank.ru/get-money/mortgage/house-deal/", img: `${IMG}/D_PureCard_364x364_150125.png` },
  { title: "Премиальный сервис\nAlfa Only", subtitle: "Путешествия с привилегиями\nи кэшбэк 10% в лучших ресторанах", href: "https://alfabank.ru/everyday/package/premium/", img: `${IMG}/D_CardPromo_364x364_2-13022026.png` },
  { title: "Кредит наличными", subtitle: "Получите решение онлайн за 2 минуты", href: "https://alfabank.ru/get-money/credit/credit-cash/", img: `${IMG}/D_CardPromo_364x364_170924_2.png` },
  { title: "Бесплатная\nкредитная карта", subtitle: "Целых 150 дней без %", href: "https://alfabank.ru/get-money/credit-cards/zayavka/", img: `${IMG}/D_CardSlot_364x364-basta-kk.jpg` },
  { title: "Зарплата на Альфа‑Карту", subtitle: "Пользуйтесь выгодой: особая категория кэшбэка каждый месяц и обслуживание за 0 ₽", href: "https://alfabank.ru/everyday/salary-card/individual-salary-card/", img: `${IMG}/D_CardPromo_364-364_210126.png` },
  { title: "Зарабатывайте играючи", subtitle: "Получайте деньги, умножайте кэшбэк, забирайте айфоны и другие гаджеты в играх Альфа‑Банка", href: "https://alfabank.ru/lp/retail/games/", img: `${IMG}/D_CardPromo_364x364_030326.png` },
];

/* ——— «Наши клиенты получают повышенный кэшбэк у партнёров» ——— */
export const PARTNERS = {
  title: ["Наши клиенты получают", "повышенный кэшбэк", "у партнёров"],
  text: "Каждый месяц мы собираем для вас выгодные предложения партнёров: кэшбэк на продукты, одежду, технику, развлечения, образование и не только. Станьте клиентом и забирайте кэшбэк!",
  cta: "Стать клиентом",
  href: "https://alfabank.ru/everyday/debit-cards/alfacard-short2/",
  img: `${IMG}/D_CardPromo_1140x312_121223.png`,
  bg: "#ffcac7",
};

/* ——— «Сервисы» ——— */
export const SERVICES: Card[] = [
  { title: "Отделения банка и банкоматы", subtitle: "Найдите ближайшие к вам отделения и банкоматы", href: "https://alfabank.ru/atm/", img: `${IMG}/D_CardPromo_58x58_211223_2.png` },
  { title: "Платежи и переводы", subtitle: "Оплачивайте и переводите деньги без комиссии", href: "https://alfabank.ru/everyday/payments-and-transfers/", img: `${IMG}/D_CardPromo_58x58_070324.png` },
  { title: "Купить или продать недвижимость", subtitle: "Сделка под ключ, быстро и безопасно", href: "https://alfabank.ru/get-money/mortgage/house-deal/", img: `${IMG}/D_CardPromo_58x58_071123.png` },
  { title: "Оформить самозанятость", subtitle: "Доходы, налоги и выгода в одном приложении", href: "https://alfabank.ru/selfemployed/", img: `${IMG}/D_CardPromo_58x58_21082205.png`, bg: "#0e0e0e" },
];

export const SUPPORT: Card = {
  title: "Поддержка",
  subtitle: "Любой вопрос решим по телефону или в чате",
  href: "https://alfabank.ru/feedback/support/",
  img: `${IMG}/D_CardPromo_58x58_211223.png`,
};

/* Курсы валют — виджет на сайте тянет их с API alfabank.ru.
   Значения ниже сняты с живой страницы, чтобы блок не висел пустым. */
export const RATES = [
  { code: "USD", buy: "81,53", sell: "83,10" },
  { code: "EUR", buy: "95,61", sell: "97,25" },
  { code: "CNY", buy: "12,15", sell: "12,45" },
];

/* ——— «О банке»: три вкладки ——— */
export const ABOUT_TABS: Array<{ id: string; label: string; cards: Card[] }> = [
  {
    id: "awards",
    label: "Достижения",
    cards: [
      { title: "Получили более 300 наград", subtitle: "Спасибо, что выбираете нас", href: "https://alfabank.ru/about/awards/", img: `${IMG}/D_CardPure_558x444_060525-1.png` },
      { title: "Крупнейший частный банк", subtitle: "40 миллионов клиентов выбрали нас  •  800+ офисов и доставка в 2500 городов", href: "https://alfabank.ru/about/", img: `${IMG}/D_CardPure_558x210_060525-3.png` },
      { title: "Отзывы", subtitle: "Мы читаем все ваши комментарии о нашей работе. И каждый день стараемся быть лучше", href: "https://alfabank.ru/feedback/support/reviews/", img: `${IMG}/D_CardPure_558x210_060525-2.png` },
    ],
  },
  {
    id: "job",
    label: "Работа в Альфе",
    cards: [
      { title: "Альфа‑Будущее", subtitle: "Стажировки для студентов со всей страны", href: "https://alfabank.ru/alfafuture/", img: `${IMG}/D_CardPure_558x444_060525.png` },
      { title: "Вакансии в Альфа‑Банке", subtitle: "Ждём вас в нашей команде", href: "https://job.alfabank.ru/vacancies", img: `${IMG}/D_CardPure_558x210_060525.png` },
      { title: "Свой в Альфе", subtitle: "Делитесь выгодой и зарабатывайте", href: "https://alfabank.ru/retail/agent/", img: `${IMG}/D_CardPure_558x210_060525-1.png` },
    ],
  },
];

/* ——— умный поиск ——— */
export const SMART_SEARCH = {
  title: ["Не нашли нужную информацию?", "Попробуйте умный поиск"],
  text: "Поможем разобраться в условиях продуктов и найти нужный",
  cta: "Задать вопрос",
  href: "https://alfabank.ru/smart-search/",
  img: `${IMG}/D_CardPure_1140x244_090625_2.png`,
};

/* ——— футер ——— */
export const APP_PROMO = {
  title: ["Приложение", "на ваш смартфон"],
  text: "Переводы, открытие счетов и вкладов, инвестиции и многое другое — в вашем смартфоне",
  primary: "Скачайте приложение",
  secondary: "Посмотрите все приложения",
  video: "https://alfabank.servicecdn.ru/site-upload/6f/6a/1449/D_Videoblock_528x528_241212(2).mp4",
  poster: `${IMG}/D_Videoblock_528x528_251224.jpg`,
};

export const FOOTER_COLUMNS: Array<{ head: string; items: Array<[string, string]> }> = [
  {
    head: "Связь с банком",
    items: [
      ["Звонок в банк", "https://alfabank.ru/feedback/support/"],
      ["2002", "tel:2002"],
      ["+7 495 788 88 78", "tel:+74957888878"],
    ],
  },
  {
    head: "Сервисы",
    items: [
      ["Курсы валют", "https://alfabank.ru/currency/"],
      ["Курсы металлов", "https://alfabank.ru/make-money/investments/metall/"],
      ["Отделения", "https://alfabank.ru/office/"],
      ["Банкоматы", "https://alfabank.ru/atm/"],
      ["Активация карты", "https://online.alfabank.ru/cards-activation/"],
      ["Конструктор сайтов", "https://alfabank.ru/cms/"],
      ["А-Клуб", "https://alfabank.ru/a-club/"],
      ["Акции и предложения", "https://alfabank.ru/retail/promotions/"],
    ],
  },
  {
    head: "Банк",
    items: [
      ["О банке", "https://alfabank.ru/about/"],
      ["Пресс-служба", "https://alfabank.ru/news/"],
      ["Вакансии", "https://job.alfabank.ru/"],
      ["Реквизиты", "https://alfabank.ru/essential/"],
      ["Тарифы и документы", "https://alfabank.ru/retail/tariffs/"],
      ["Должникам и взыскателям", "https://alfabank.ru/lp/retail/dolpri/"],
      ["Закупки", "https://alfabank.ru/tenders/"],
      ["Свой в Альфе", "https://alfabank.ru/retail/agent/"],
    ],
  },
  {
    head: "Поддержка",
    items: [
      ["Обращение в банк", "https://alfabank.ru/feedback/support/"],
      ["Справочный центр", "https://alfabank.ru/help/t/retail/"],
      ["Блог", "https://alfabank.ru/help/articles/"],
      ["Отзывы клиентов", "https://alfabank.ru/feedback/support/reviews/"],
      ["Безопасность", "https://alfabank.ru/everyday/online/alfaclick/security/"],
      ["Иностранным гражданам", "https://alfabank.ru/everyday/non-residents/"],
      ["Карта сайта", "https://alfabank.ru/sitemap/"],
    ],
  },
];

export const FOOTER_LEGAL =
  "© 2001-2026. АО «Альфа-Банк», официальный сайт. Генеральная лицензия Банка России № 1326 от 16 января 2015 г. АО «Альфа-Банк» является участником системы обязательного страхования вкладов. Информация о процентных ставках по договорам банковского вклада с физическими лицами. Центр раскрытия корпоративной информации. Информация о лицах, под контролем либо значительным влиянием которых находится Банк. Ул. Каланчевская, 27, Москва, 107078.";
