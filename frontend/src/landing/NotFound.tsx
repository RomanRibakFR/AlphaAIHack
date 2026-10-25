/** Страница 404.
 *
 *  Показывается на разделах, которых в прототипе нет («Частным лицам»,
 *  «Крупному бизнесу»), и на любом незнакомом адресе.
 *
 *  Содержимое короткое, поэтому страница растянута на всю высоту окна,
 *  а подвал прижат к низу — иначе под ним оставалась бы белая полоса.
 */
import { Button } from "@alfalab/core-components/button";
import { useNavigate } from "react-router-dom";
import Footer from "./Footer";
import Header from "./Header";
import { Container, Text } from "../ui/primitives";
import "./landing.css";

const INVERTED = "var(--color-light-text-primary-inverted)";
const INVERTED_2 = "var(--color-light-text-secondary-inverted)";

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="lp-page lp-page-short">
      <Header />

      <Container>
        <div className="lp-404">
          <div className="lp-hero-kicker mo-enter">Ошибка 404</div>

          <Text view="promo-hero" tag="h1" color={INVERTED} className="mo-enter">
            Такой страницы нет
          </Text>

          <Text
            view="primary-large"
            color={INVERTED_2}
            className="mo-enter"
            style={{ marginTop: 20, maxWidth: 520, animationDelay: "90ms" }}
          >
            Этого раздела в прототипе нет. Мы собрали кредитный путь для малого бизнеса и ИП —
            он на главной.
          </Text>

          <div className="lp-hero-cta mo-enter" style={{ animationDelay: "160ms" }}>
            <Button view="accent" size={56} className="mo-press" onClick={() => navigate("/")}>
              На главную
            </Button>
          </div>
        </div>
      </Container>

      <Footer />
    </div>
  );
}
