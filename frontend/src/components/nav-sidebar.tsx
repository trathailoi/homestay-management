"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/rooms", label: "Rooms" },
  { href: "/bookings", label: "Bookings" },
];

export function NavSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <aside className="w-56 h-screen bg-slate-900 text-white flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-xl font-bold">Homestay</h1>
        <p className="text-xs text-slate-400">Management Dashboard</p>
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

      {/* User Footer */}
      <div className="p-4 border-t border-slate-700">
        {user && (
          <div className="space-y-2">
            <div className="text-sm">
              <span className="text-slate-400">Signed in as</span>
              <p className="font-medium truncate">{user.username}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-slate-300 hover:text-white hover:bg-slate-800"
              onClick={handleLogout}
            >
              Sign out
            </Button>
          </div>
        )}
      </div>
    </aside>
  );
}
