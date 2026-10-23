import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Product } from "../api/types";

/**
 * Каталог на случай, если бэкенд не поднят.
 *
 * Промо-страница должна читаться всегда: человек, открывший ссылку,
 * не обязан знать, что где-то не запустился контейнер. Значения —
 * копия backend/app/seed.py, в том же строковом формате, что отдаёт API.
 */
const FALLBACK: Product[] = [
  {
    code: "overdraft",
    name: "Овердрафт",
    description: "Закрыть кассовый разрыв: уходите в минус по счёту в пределах лимита",
    min_amount: "100000.00",
    max_amount: "5000000.00",
    min_term_months: 1,
    max_term_months: 12,
    base_rate: "18.50",
    requires_collateral: false,
    min_business_age_months: 6,
  },
  {
    code: "working_capital",
    name: "Оборотный кредит",
    description: "Пополнить оборотные средства: закупка товара, сырья, зарплаты",
    min_amount: "500000.00",
    max_amount: "20000000.00",
    min_term_months: 3,
    max_term_months: 36,
    base_rate: "17.00",
    requires_collateral: false,
    min_business_age_months: 12,
  },
  {
    code: "investment",
    name: "Инвестиционный кредит",
    description: "Купить оборудование, транспорт или недвижимость для бизнеса",
    min_amount: "1000000.00",
    max_amount: "100000000.00",
    min_term_months: 12,
    max_term_months: 84,
    base_rate: "15.50",
    requires_collateral: true,
    min_business_age_months: 24,
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
