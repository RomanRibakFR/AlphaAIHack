import { Button } from "@alfalab/core-components/button";
import { useNavigate } from "react-router-dom";
import { Container, Text } from "../../ui/primitives";
import { Reveal, Stagger } from "../../ui/Reveal";
import type { Product } from "../../api/types";
import { money, rate } from "../../lib/format";
import { PRODUCT_STYLE } from "../content";

const SECONDARY = "var(--color-light-text-secondary)";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="lp-product-row">
      <span style={{ color: SECONDARY }}>{label}</span>
      <span style={{ fontWeight: 500, textAlign: "right" }}>{value}</span>
    </div>
  );
}

export default function Products({ products }: { products: Product[] | null }) {
  const navigate = useNavigate();

  return (
    <section className="lp-section" id="products">
      <Container>
        <Reveal>
          <div className="lp-section-head">
            <Text view="promo-h2" tag="h2">
              Три кредита под разные задачи
            </Text>
            <Text view="primary-large" color={SECONDARY} tag="p">
              Если не уверены, какой подходит, начните с калькулятора ниже — он покажет платёж
              по каждому.
            </Text>
          </div>
        </Reveal>

        {products === null ? (
          <div className="lp-products">
            {[0, 1, 2].map((i) => (
              <div key={i} className="lp-skeleton mo-shimmer" />
            ))}
          </div>
        ) : (
          <Stagger className="lp-products" step={90}>
            {products.map((p) => {
              const style = PRODUCT_STYLE[p.code] ?? { bg: "var(--alfa-promo-grey)", tagline: "" };
              return (
                <div
                  key={p.code}
                  className="lp-product mo-lift"
                  style={{ background: style.bg }}
                  role="group"
                >
                  <Text view="promo-card" tag="h3">
                    {p.name}
                  </Text>
                  <Text view="primary-small" style={{ marginTop: 8 }}>
                    {style.tagline || p.description}
                  </Text>

                  <div className="lp-product-rows">
                    <Row label="Сумма" value={`${money(p.min_amount)} — ${money(p.max_amount)}`} />
                    <Row
                      label="Срок"
                      value={`${p.min_term_months}—${p.max_term_months} мес.`}
                    />
                    <Row label="Залог" value={p.requires_collateral ? "нужен" : "не нужен"} />
                    <Row label="Бизнесу от" value={`${p.min_business_age_months} мес.`} />
                  </div>

                  <div className="lp-product-rate">
                    <Text view="accent-primary-large" tag="div">
                      {rate(p.base_rate)}
                    </Text>
                    <Button
                      view="primary"
                      size={48}
                      block
                      className="mo-press"
                      style={{ marginTop: 16 }}
                      onClick={() => navigate("/login")}
                    >
                      Подать заявку
                    </Button>
                  </div>
                </div>
              );
            })}
          </Stagger>
        )}
      </Container>
    </section>
  );
}
