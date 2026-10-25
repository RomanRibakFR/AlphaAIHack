import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import Footer from "../landing/Footer";
import AlfaLogo from "../ui/AlfaLogo";
import { Container, Text } from "../ui/primitives";
import "../cabinet/cabinet.css";
import "./underwriter.css";

const INVERTED = "var(--color-light-text-primary-inverted)";
const INVERTED_2 = "var(--color-light-text-secondary-inverted)";

/**
 * Оболочка рабочего места.
 *
 * Та же шапка и полотно, что в кабинете клиента, — это один продукт.
 * Отличает подпись в шапке: специалист должен видеть, что он не в кабинете
 * клиента, иначе на демо легко перепутать две стороны процесса.
 */
export default function UnderwriterLayout({ children }: { children: ReactNode }) {
  return (
    <div className="cb-page">
      <header className="cb-header">
        <Container>
          <div className="cb-header-row">
            <Link to="/" aria-label="На главную">
              <AlfaLogo height={36} />
            </Link>
            <Text view="accent-primary-medium" color={INVERTED} className="cb-header-title">
              Кредитный конвейер
            </Text>

            <div className="cb-header-who">
              <Text view="primary-small" color={INVERTED}>
                Кредитный специалист
              </Text>
              <Text view="secondary-medium" color={INVERTED_2}>
                рабочее место
              </Text>
            </div>

            <Link to="/" className="uw-exit">
              Выйти
            </Link>
          </div>
        </Container>
      </header>

      <main className="cb-main">
        <Container>{children}</Container>
      </main>

      <Footer />
    </div>
  );
}
