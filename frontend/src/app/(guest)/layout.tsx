import type { Metadata } from "next";
import { GuestHeader } from "@/components/guest-header";
import { GuestFooter } from "@/components/guest-footer";

export const metadata: Metadata = {
  title: "Homestay - Find Your Perfect Room",
  description: "Search and book your perfect homestay room",
};

export default function GuestLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
      <GuestHeader />
      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
      <GuestFooter />
    </div>
  );
}
