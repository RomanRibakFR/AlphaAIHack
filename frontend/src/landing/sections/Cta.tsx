import { Button } from "@alfalab/core-components/button";
import { useNavigate } from "react-router-dom";
import { Container, Text } from "../../ui/primitives";
import { Reveal } from "../../ui/Reveal";
import { CTA } from "../content";

export default function Cta() {
  const navigate = useNavigate();

  return (
    <section className="lp-section">
      <Container>
        <Reveal variant="grow">
          <div className="lp-cta">
            <div>
              <Text view="promo-h2" tag="h2">
                {CTA.title}
              </Text>
              <Text view="primary-large" style={{ marginTop: 12, opacity: 0.9 }}>
                {CTA.text}
              </Text>
            </div>
            <Button
              view="primary"
              size={64}
              className="mo-press"
              style={{ flex: "0 0 auto" }}
              onClick={() => navigate("/login")}
            >
              {CTA.button}
            </Button>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
