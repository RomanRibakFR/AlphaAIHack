import { Button } from "@alfalab/core-components/button";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AlfaLogo from "../ui/AlfaLogo";
import { Container } from "../ui/primitives";
import { useScrollProgress, useScrolled } from "../lib/motion";
import { NAV } from "./content";

/**
 * Шапка повторяет alfabank.ru: логотип, три раздела, кнопки справа.
 *
 * Отличие одно — вместо «Стать клиентом» на вторичной кнопке стоит вход
 * для сотрудника банка. На настоящем сайте такого входа в шапке нет,
 * но жюри должно добираться до банковской части в один клик.
 */
export default function Header() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const scrolled = useScrolled();
  const progress = useScrollProgress();

  return (
    <header className="lp-header" data-scrolled={scrolled}>
      <Container>
        <div className="lp-header-row">
          <Link to="/" aria-label="Альфа-Банк">
            <AlfaLogo height={40} />
          </Link>

          <nav className="lp-nav">
            {NAV.map((item) => (
              <Link
                key={item.label}
                to={item.href}
                // подсвечен тот раздел, на котором мы сейчас
                aria-current={item.href === pathname ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="lp-header-right">
            <Button
              view="secondary"
              size={40}
              className="mo-press lp-btn-ghost"
              onClick={() => navigate("/staff")}
            >
              Вход для сотрудника
            </Button>
            <Button view="accent" size={40} className="mo-press" onClick={() => navigate("/login")}>
              Войти
            </Button>
          </div>
        </div>
      </Container>

      {/* сколько страницы прочитано */}
      <div className="lp-progress" style={{ transform: `scaleX(${progress})` }} />
    </header>
  );
}
