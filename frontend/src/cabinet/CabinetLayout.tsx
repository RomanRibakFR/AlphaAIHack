import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@alfalab/core-components/button";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { RegistryCompany } from "../api/types";
import Footer from "../landing/Footer";
import AlfaLogo from "../ui/AlfaLogo";
import { Container, Text } from "../ui/primitives";
import "./cabinet.css";

const INVERTED = "var(--color-light-text-primary-inverted)";
const INVERTED_2 = "var(--color-light-text-secondary-inverted)";

/** Оболочка кабинета: тёмная шапка, светлое полотно под контент. */
export default function CabinetLayout({
  inn,
  onSignOut,
  children,
}: {
  inn: string;
  onSignOut: () => void;
  children: ReactNode;
}) {
  const [company, setCompany] = useState<RegistryCompany | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .lookupCompany(inn)
      .then((c) => alive && setCompany(c))
      .catch(() => {
        /* имя компании — украшение шапки, без него кабинет работает */
      });
    return () => {
      alive = false;
    };
  }, [inn]);

  return (
    <div className="cb-page">
      <header className="cb-header">
        <Container>
          <div className="cb-header-row">
            <Link to="/" aria-label="На главную">
              <AlfaLogo height={36} />
            </Link>
            <Text view="accent-primary-medium" color={INVERTED} className="cb-header-title">
              Кредитный кабинет
            </Text>

            <div className="cb-header-who">
              <Text view="primary-small" color={INVERTED}>
                {company?.name ?? "Компания"}
              </Text>
              <Text view="secondary-medium" color={INVERTED_2}>
                ИНН {inn}
              </Text>
            </div>

            <Button
              view="secondary"
              size={40}
              className="mo-press lp-btn-ghost"
              onClick={onSignOut}
            >
              Выйти
            </Button>
          </div>
        </Container>
      </header>

      <main className="cb-main">
        <Container>{children}</Container>
      </main>

      {/* тот же подвал, что на сайте: кабинет остаётся частью продукта */}
      <Footer />
    </div>
  );
}
