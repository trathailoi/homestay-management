import type { Metadata } from "next";

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
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-slate-900">Homestay</h1>
          <p className="text-sm text-slate-600">
            Find and book your perfect room
          </p>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
      <footer className="border-t mt-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-sm text-slate-500">
          <p>Welcome to our homestay. We look forward to hosting you.</p>
        </div>
      </footer>
    </div>
  );
}
