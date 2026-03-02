"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useTranslation } from "@/lib/language-context";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

export function NavSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { href: "/dashboard", label: t("nav.dashboard") },
    { href: "/rooms", label: t("nav.rooms") },
    { href: "/bookings", label: t("nav.bookings") },
    { href: "/availability", label: t("nav.availability") },
  ];

  const handleLogout = async () => {
    await logout();
  };

  function NavContent({ onNavigate }: { onNavigate?: () => void }) {
    return (
      <>
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
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
      </>
    );
  }

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-56 h-screen bg-slate-900 text-white flex-col shrink-0">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-xl font-bold">{t("nav.homestay")}</h1>
          <p className="text-xs text-slate-400">{t("nav.managementDashboard")}</p>
        </div>
        <NavContent />
      </aside>

      {/* Mobile Top Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-slate-900 text-white flex items-center h-14 px-4">
        <Button
          variant="ghost"
          size="sm"
          className="text-white hover:bg-slate-800 -ml-2"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-bold ml-3">{t("nav.homestay")}</h1>
      </div>

      {/* Mobile Drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="left"
          className="bg-slate-900 text-white border-slate-700 p-0 flex flex-col"
          showCloseButton={false}
        >
          <SheetHeader className="p-4 border-b border-slate-700">
            <SheetTitle className="text-white text-left">
              <span className="text-xl font-bold">{t("nav.homestay")}</span>
              <p className="text-xs text-slate-400 font-normal">{t("nav.managementDashboard")}</p>
            </SheetTitle>
          </SheetHeader>
          <NavContent onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>
    </>
  );
}
