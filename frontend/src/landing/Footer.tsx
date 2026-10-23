import AlfaLogo from "../ui/AlfaLogo";
import { Container, Text } from "../ui/primitives";
import { FOOTER_COLUMNS, FOOTER_LEGAL } from "./content";

const INVERTED_2 = "var(--color-light-text-secondary-inverted)";

export default function Footer() {
  return (
    <footer className="lp-footer">
      <Container>
        <div className="lp-footer-cols">
          <div className="lp-footer-col">
            <AlfaLogo height={32} color="var(--color-light-text-primary-inverted)" />
          </div>
          {FOOTER_COLUMNS.map((col) => (
            <div key={col.title} className="lp-footer-col">
              <h3>{col.title}</h3>
              {col.links.map((link) => (
                <a key={link} href="#products">
                  {link}
                </a>
              ))}
            </div>
          ))}
        </div>

        <Text view="secondary-medium" color={INVERTED_2} style={{ maxWidth: 820 }}>
          {FOOTER_LEGAL}
        </Text>
      </Container>
    </footer>
  );
}
