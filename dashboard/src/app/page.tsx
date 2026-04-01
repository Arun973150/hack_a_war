import Nav from "@/components/nav";
import Hero from "@/components/hero";
import Frameworks from "@/components/frameworks";
import Statement from "@/components/statement";
import FeatureSections from "@/components/feature-sections";
import SocialProof from "@/components/social-proof";
import Integrations from "@/components/integrations";
import CTA from "@/components/cta";
import Footer from "@/components/footer";

export default function Home() {
  return (
    <main style={{ minHeight: "100vh", background: "#0A0A0A", overflow: "hidden" }}>
      <Nav />
      <Hero />
      <Frameworks />
      <Statement />
      <FeatureSections />
      <SocialProof />
      <Integrations />
      <CTA />
      <Footer />
    </main>
  );
}
