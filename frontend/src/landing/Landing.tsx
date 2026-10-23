/** Продуктовая страница «Умного кредитного кабинета».
 *
 *  Собрана на дизайн-системе Альфа-Банка (@alfalab/core-components + токены),
 *  сетка повторяет alfabank.ru: колонка 1140, шаг 24, шапка 104,
 *  белый блок со скруглением 64 поверх тёмной подложки.
 *
 *  Анимации — в lib/motion.ts и ui/motion.css, все выключаются
 *  при prefers-reduced-motion.
 */
import Footer from "./Footer";
import Header from "./Header";
import Calculator from "./sections/Calculator";
import Cta from "./sections/Cta";
import Faq from "./sections/Faq";
import Hero from "./sections/Hero";
import Products from "./sections/Products";
import Requirements from "./sections/Requirements";
import Steps from "./sections/Steps";
import { Container, Text } from "../ui/primitives";
import { useProducts } from "./useProducts";
import "./landing.css";

export default function Landing() {
  const { products, live } = useProducts();

  const toCalculator = () =>
    document.getElementById("calculator")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="lp-page">
      <Header />
      <Hero onCalculator={toCalculator} />

      <div className="lp-content">
        <Products products={products} />
        <Calculator products={products} />
        <Steps />
        <Requirements />
        <Faq />
        <Cta />

        {!live && (
          <Container>
            <Text view="secondary-medium" color="var(--color-light-text-secondary)">
              Бэкенд не отвечает, каталог показан из запасной копии. Условия настоящие, но
              подать заявку не получится, пока не поднят API.
            </Text>
          </Container>
        )}
      </div>

      <Footer />
    </div>
  );
}
