import type { Metadata } from "next";
import { Hanken_Grotesk, Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// Inter for body/UI, Hanken Grotesk for display headings (Horizon Bound).
// vietnamese subset: vi is the default locale.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "vietnamese"],
});

const hanken = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin", "vietnamese"],
});

export const metadata: Metadata = {
  title: "Homestay Management",
  description: "Room booking and management for homestays",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${hanken.variable} antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
