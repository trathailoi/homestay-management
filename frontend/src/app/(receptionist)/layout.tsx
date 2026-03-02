import { AuthGuard } from "@/components/auth-guard";
import { NavSidebar } from "@/components/nav-sidebar";

export default function ReceptionistLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex flex-col md:flex-row h-screen bg-slate-50 dark:bg-slate-950">
        <NavSidebar />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pt-18 md:pt-6">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
