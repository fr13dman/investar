import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Investar - S&P 500 and Nasdaq-100 research",
  description: "Screen S&P 500 and Nasdaq-100 stocks by sector and research companies.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}>
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
              <Link href="/watchlists" className="text-sm text-muted-foreground hover:text-foreground">
                Watchlists
              </Link>
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
