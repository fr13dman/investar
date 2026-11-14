import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { THEME_INIT_SCRIPT } from "@/lib/themeScript";

import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Investar - S&P 500, Nasdaq-100 and niche-sector research",
  description: "Screen S&P 500, Nasdaq-100 and niche-sector stocks and ETFs, and research companies.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: the inline theme script adds `dark` and color-scheme before React hydrates.
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <Providers>
          <header className="border-b border-border">
            <nav className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
              <Link href="/" className="text-lg font-semibold tracking-tight">
                Investar
              </Link>
              <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
                Screener
              </Link>
              <Link href="/explore" className="text-sm text-muted-foreground hover:text-foreground">
                Explore
              </Link>
              <Link href="/watchlists" className="text-sm text-muted-foreground hover:text-foreground">
                Watchlists
              </Link>
              <div className="ml-auto">
                <ThemeToggle />
              </div>
            </nav>
          </header>
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">{children}</main>
          <footer className="border-t border-border px-4 py-3 text-center text-xs text-muted-foreground">
            Data from Yahoo Finance (delayed), Finnhub, SEC EDGAR, Wikidata and USPTO PatentsView. For research only;
            not financial advice.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
