import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Spenden-Transparenz",
    template: "%s | Spenden-Transparenz",
  },
};

// The <html> and <body> elements live in the layouts below this one, because the lang
// attribute depends on the locale segment.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
