/**
 * Предпроверка по ИНН.
 *
 * Из исследования: у всех банков формальный отсев происходит уже после
 * заявки — человек заполняет анкету и только потом узнаёт, что не подходит
 * по сроку работы. Мы показываем это до заполнения.
 *
 * Здесь только формальные признаки, которые видны в выписке из реестра
 * и в карточке продукта. Никакой оценки риска: баллы и решение считает
 * бэкенд, фронт про них ничего не знает.
 */
import type { Product, RegistryCompany } from "../api/types";
import { duration, months } from "../lib/format";

/**
 * Статус в реестре приходит латиницей в верхнем регистре: ACTIVE, LIQUIDATING,
 * LIQUIDATED, BANKRUPT, REORGANIZING (docs/mocks-format.md, раздел 3.1).
 * Показывать это клиенту нельзя, поэтому переводим.
 */
const STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Действующая",
  LIQUIDATING: "В процессе ликвидации",
  LIQUIDATED: "Ликвидирована",
  BANKRUPT: "Банкротство",
  REORGANIZING: "В процессе реорганизации",
};

export function isActive(company: RegistryCompany): boolean {
  return company.status.toUpperCase() === "ACTIVE";
}

export function statusLabel(status: string): string {
  return STATUS_LABEL[status.toUpperCase()] ?? status;
}

/** Сколько полных месяцев компания в реестре. */
export function businessAgeMonths(registeredAt: string | null): number | null {
  if (!registeredAt) return null;
  const from = new Date(registeredAt);
  if (Number.isNaN(from.getTime())) return null;

  const now = new Date();
  const months =
    (now.getFullYear() - from.getFullYear()) * 12 + (now.getMonth() - from.getMonth());
  return now.getDate() < from.getDate() ? months - 1 : months;
}

export type Criterion = {
  ok: boolean;
  text: string;
};

/** Формальные критерии продукта для конкретной компании. */
export function checkProduct(company: RegistryCompany, product: Product): Criterion[] {
  const age = businessAgeMonths(company.registered_at);
  const needed = product.min_business_age_months;

  const active = isActive(company);
  const oldEnough = age !== null && age >= needed;

  return [
    {
      ok: active,
      text: active
        ? "Компания действующая по данным реестра"
        : "По данным реестра компания не действующая",
    },
    {
      ok: oldEnough,
      // «от 24 месяца» звучало бы неграмотно: после «от» нужен родительный
      // падеж. Обходим согласование словом «минимум» — оно идёт с именительным.
      text:
        age === null
          ? `Нужен срок работы: минимум ${months(needed)}`
          : oldEnough
            ? `Бизнес работает ${duration(age)}, минимум ${months(needed)}`
            : `Бизнес работает ${duration(age)}, а нужно минимум ${months(needed)}`,
    },
    {
      ok: !product.requires_collateral,
      text: product.requires_collateral ? "Понадобится залог" : "Залог не нужен",
    },
  ];
}

/** Продукт проходит формальные критерии (залог — не препятствие, а условие). */
export function productFits(company: RegistryCompany, product: Product): boolean {
  const age = businessAgeMonths(company.registered_at);
  return isActive(company) && age !== null && age >= product.min_business_age_months;
}
