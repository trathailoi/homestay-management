"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTranslation } from "@/lib/language-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import { cn } from "@/lib/utils";

export function NavSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  const navItems = [
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/rooms", label: t("nav.rooms") },
    { href: "/bookings", label: t("nav.bookings") },
    { href: "/availability", label: t("nav.availability") },
  ];

  const handleLogout = async () => {
    await logout();
  };

  return (
    <aside className="w-56 h-screen bg-slate-900 text-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold">{t("nav.homestay")}</h1>
        <p className="text-xs text-slate-400">{t("nav.managementDashboard")}</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-slate-800 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Toggles + User Footer */}
      <div className="px-4 pb-2 flex items-center gap-1">
        <ThemeToggle className="text-slate-300 hover:text-white hover:bg-slate-800" />
        <LanguageToggle className="text-slate-300 hover:text-white hover:bg-slate-800" />
      </div>
      <div className="p-4 border-t border-slate-700">
        {user && (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="text-slate-400">{t("nav.signedInAs")}</span>
              <p className="font-medium truncate">{user.username}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-slate-300 hover:text-white hover:bg-slate-800"
              onClick={handleLogout}
            >
              {t("nav.signOut")}
            </Button>
          </div>
        )}
      </div>
    </aside>
  );
}
