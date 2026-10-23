import { Container, Text } from "../../ui/primitives";
import { Reveal } from "../../ui/Reveal";
import { useInView } from "../../lib/motion";
import { STEPS } from "../content";

const SECONDARY = "var(--color-light-text-secondary)";

/** Путь заявки. Линия между шагами прочерчивается, когда блок попадает в окно. */
export default function Steps() {
  const { ref, inView } = useInView<HTMLDivElement>();

  return (
    <section className="lp-section" id="how">
      <Container>
        <Reveal>
          <div className="lp-section-head">
            <Text view="promo-h2" tag="h2">
              Как проходит заявка
            </Text>
            <Text view="primary-large" color={SECONDARY} tag="p">
              Внутри банка шагов больше, но вам видно главное: на чём заявка сейчас и что делать
              дальше.
            </Text>
          </div>
        </Reveal>

        <div className="lp-steps" ref={ref}>
          <div className="lp-steps-line mo-draw" data-shown={inView} />
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              className="mo-reveal"
              data-shown={inView}
              style={{ transitionDelay: `${i * 120}ms` }}
            >
              <div className="lp-step-num">{i + 1}</div>
              <Text view="accent-primary-large" tag="h3">
                {step.title}
              </Text>
              <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
                {step.text}
              </Text>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
