import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Red Forge — AI Regulatory Compliance",
  description:
    "Red Forge monitors regulatory changes across 40+ jurisdictions, extracts obligations, maps them to your controls, and generates action plans — automatically.",
  keywords: [
    "regulatory compliance",
    "AI compliance",
    "GDPR",
    "HIPAA",
    "SOC2",
    "compliance automation",
    "regulatory monitoring",
  ],
  openGraph: {
    title: "Red Forge — AI Regulatory Compliance",
    description:
      "Stop manually tracking regulatory changes. Red Forge does it for you.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-forge-bg text-forge-text antialiased">
        {children}
      </body>
    </html>
  );
}
