import { AuthGuard } from "@/components/auth-guard";
import { NavSidebar } from "@/components/nav-sidebar";

export default function ReceptionistLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen bg-slate-50">
        <NavSidebar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
