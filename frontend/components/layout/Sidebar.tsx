"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, OrganizationSwitcher } from "@clerk/nextjs";
import { LayoutDashboard, Search, History, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/research", icon: Search, label: "Research" },
  { href: "/history", icon: History, label: "History" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[220px] flex flex-col bg-surface border-r border-border z-30">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-ai-dim border border-ai/30 flex items-center justify-center">
            <span className="text-ai text-xs font-mono font-bold">S</span>
          </div>
          <span className="text-sm font-medium text-ink tracking-tight">SignalStack</span>
        </div>
      </div>

      {/* Org switcher */}
      <div className="px-3 py-3 border-b border-border">
        <OrganizationSwitcher
          appearance={{
            elements: {
              rootBox: "w-full",
              organizationSwitcherTrigger:
                "w-full justify-start px-2 py-1.5 rounded-md hover:bg-card text-xs text-ink-secondary transition-colors",
            },
          }}
        />
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm transition-colors",
                isActive
                  ? "bg-ai-glow text-ai border border-ai/15"
                  : "text-ink-secondary hover:text-ink hover:bg-card"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2">
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-7 h-7",
              },
            }}
          />
          <span className="text-xs text-ink-muted truncate">Account</span>
        </div>
      </div>
    </aside>
  );
}