import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GenResearch — AI-Powered Academic Research Platform",
  description:
    "GenResearch is a multi-agent AI platform for academics and students. Upload papers, generate literature reviews, summaries, citations, and proposals in seconds.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
