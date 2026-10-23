import { useState } from "react";
import { Container, Text } from "../../ui/primitives";
import { Reveal, Stagger } from "../../ui/Reveal";
import { FAQ } from "../content";

function Chevron() {
  return (
    <svg className="lp-faq-chevron" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <path
        d="M5 7.5L10 12.5L15 7.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Раскрытие анимируется через grid-template-rows: 0fr → 1fr, см. landing.css. */
export default function Faq() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section className="lp-section" id="faq">
      <Container>
        <Reveal>
          <div className="lp-section-head">
            <Text view="promo-h2" tag="h2">
              Частые вопросы
            </Text>
          </div>
        </Reveal>

        <Stagger className="lp-faq" step={60}>
          {FAQ.map((item, i) => (
            <div key={item.q} className="lp-faq-item" data-open={open === i}>
              <button
                className="lp-faq-q"
                aria-expanded={open === i}
                onClick={() => setOpen(open === i ? null : i)}
              >
                <span>{item.q}</span>
                <Chevron />
              </button>
              <div className="lp-faq-a">
                <div className="lp-faq-a-inner">
                  <p>{item.a}</p>
                </div>
              </div>
            </div>
          ))}
        </Stagger>
      </Container>
    </section>
  );
}
