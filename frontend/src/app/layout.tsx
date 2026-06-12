import type { Metadata, Viewport } from "next";
import { LocaleHtml } from "@/components/LocaleHtml";
import { WorkspaceReset } from "@/components/WorkspaceReset";
import { I18nProvider } from "@/i18n/context";
import "./globals.css";

export const metadata: Metadata = {
  title: "CV Tailor",
  description: "Adapt your CV to job descriptions while preserving structure",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="safe-bottom antialiased">
        <I18nProvider>
          <WorkspaceReset />
          <LocaleHtml />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
