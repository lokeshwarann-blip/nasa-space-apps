import type { Metadata } from "next";
import { Syne, Pinyon_Script, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const syne = Syne({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["700", "800"],
});

const pinyonScript = Pinyon_Script({
  variable: "--font-script",
  subsets: ["latin"],
  weight: ["400"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "MELIORA | Astronaut Health Monitoring",
  description: "Astronaut health monitoring and mission intelligence platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${pinyonScript.variable} ${ibmPlexMono.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
