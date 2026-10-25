import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Product } from "../api/types";

/**
 * Каталог на случай, если бэкенд не поднят.
 *
 * Промо-страница должна читаться всегда: человек, открывший ссылку,
 * не обязан знать, что где-то не запустился контейнер. Значения —
 * копия того, что бэкенд соберёт из config/decision_policy.yaml
 * (см. backend/app/seed.py), в том же строковом формате, что отдаёт API.
 *
 * «Ставка от» у всех трёх продуктов одна и та же: ключевая 14% + маржа
 * банка 1 п.п. Продукты расходятся потолком — 22, 25 и 22 процента.
 */
const FALLBACK: Product[] = [
  {
    code: "OVERDRAFT",
    name: "Овердрафт",
    description: "Закрыть кассовый разрыв: уходите в минус по счёту в пределах лимита",
    min_amount: "100000.00",
    max_amount: "10000000.00",
    min_term_months: 12,
    max_term_months: 12,
    base_rate: "15.00",
    max_rate: "22.00",
    requires_collateral: false,
    min_business_age_months: 6,
  },
  {
    code: "WORKING_CAPITAL",
    name: "Оборотный кредит без залога",
    description: "Пополнить оборотные средства без залога: закупка товара, сырья, зарплаты",
    min_amount: "300000.00",
    max_amount: "30000000.00",
    min_term_months: 6,
    max_term_months: 36,
    base_rate: "15.00",
    max_rate: "25.00",
    requires_collateral: false,
    min_business_age_months: 9,
  },
  {
    code: "INVESTMENT",
    name: "Инвестиционный кредит с залогом",
    description: "Купить оборудование, транспорт или недвижимость для бизнеса, под залог",
    min_amount: "1000000.00",
    max_amount: "100000000.00",
    min_term_months: 12,
    max_term_months: 120,
    base_rate: "15.00",
    max_rate: "22.00",
    requires_collateral: true,
    min_business_age_months: 12,
  },
];

export function useProducts() {
  const [products, setProducts] = useState<Product[] | null>(null);
  /** false — показываем запасной каталог, бэкенд не ответил */
  const [live, setLive] = useState(true);

  useEffect(() => {
    let alive = true;
    api
      .products()
      .then((list) => alive && setProducts(list.length > 0 ? list : FALLBACK))
      .catch(() => {
        if (!alive) return;
        setProducts(FALLBACK);
        setLive(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  return { products, live };
}
