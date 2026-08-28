import { fontVariables } from "../fonts";

// Internal route tree. Renders its own document because it sits outside [locale].
export default function DevLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={fontVariables}>
      <body>{children}</body>
    </html>
  );
}
