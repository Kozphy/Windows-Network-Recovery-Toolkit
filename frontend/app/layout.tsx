import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "WNRT SaaS Dashboard",
  description: "Windows Network Recovery Toolkit SaaS frontend",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
