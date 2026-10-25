import { Container, Text } from "../../ui/primitives";
import { Reveal, Stagger } from "../../ui/Reveal";
import { REQUIREMENTS, WE_ASK } from "../content";

const SECONDARY = "var(--color-light-text-secondary)";

function Check() {
  return (
    <svg className="lp-check" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M3 8.5l3.5 3.5L13 5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function Panel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="lp-panel">
      <Text view="promo-card" tag="h3">
        {title}
      </Text>
      <ul className="lp-list" style={{ marginTop: 20 }}>
        {items.map((item) => (
          <li key={item}>
            <Check />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Requirements() {
  return (
    <section className="lp-section" id="requirements">
      <Container>
        <Reveal>
          <div className="lp-section-head">
            <Text view="promo-h2" tag="h2">
              Что нужно, чтобы подать заявку
            </Text>
            <Text view="primary-large" color={SECONDARY} tag="p">
              Ничего сканировать и никуда ехать не придётся: почти всё банк находит сам по ИНН.
            </Text>
          </div>
        </Reveal>

        <Stagger className="lp-three" step={90}>
          <Panel title="Требования к бизнесу" items={REQUIREMENTS} />
          {WE_ASK.map((group) => (
            <Panel key={group.title} title={group.title} items={group.items} />
          ))}
        </Stagger>
      </Container>
    </section>
  );
}
