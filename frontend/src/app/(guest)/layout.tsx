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
    <div className="min-h-screen flex flex-col bg-background">
      <GuestHeader />
      <main className="flex-1">{children}</main>
      <GuestFooter />
    </div>
  );
}
