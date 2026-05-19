import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export type Theme = "dark" | "light" | "system";
export type SidebarState = "expanded" | "collapsed";

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  createdAt: number;
}

interface UIStore {
  // ── Command palette ────────────────────────────────────────
  commandPaletteOpen: boolean;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleCommandPalette: () => void;

  // ── Sidebar ────────────────────────────────────────────────
  sidebarState: SidebarState;
  toggleSidebar: () => void;
  setSidebarState: (state: SidebarState) => void;

  // ── Theme ──────────────────────────────────────────────────
  theme: Theme;
  setTheme: (theme: Theme) => void;

  // ── Transient notifications (not persisted) ────────────────
  notifications: Notification[];
  addNotification: (n: Omit<Notification, "id" | "createdAt">) => void;
  dismissNotification: (id: string) => void;
  clearNotifications: () => void;
}

export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      (set) => ({
        // Command palette
        commandPaletteOpen: false,
        openCommandPalette:  () => set({ commandPaletteOpen: true }),
        closeCommandPalette: () => set({ commandPaletteOpen: false }),
        toggleCommandPalette: () =>
          set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),

        // Sidebar
        sidebarState: "expanded",
        toggleSidebar: () =>
          set((s) => ({
            sidebarState: s.sidebarState === "expanded" ? "collapsed" : "expanded",
          })),
        setSidebarState: (state) => set({ sidebarState: state }),

        // Theme
        theme: "dark",
        setTheme: (theme) => set({ theme }),

        // Notifications
        notifications: [],
        addNotification: (n) =>
          set((s) => ({
            notifications: [
              ...s.notifications,
              { ...n, id: crypto.randomUUID(), createdAt: Date.now() },
            ],
          })),
        dismissNotification: (id) =>
          set((s) => ({
            notifications: s.notifications.filter((n) => n.id !== id),
          })),
        clearNotifications: () => set({ notifications: [] }),
      }),
      {
        name: "signalstack-ui-v1",
        // Only persist layout and theme preferences; notifications are transient
        partialize: (state) => ({
          sidebarState: state.sidebarState,
          theme: state.theme,
        }),
      }
    ),
    { name: "UIStore" }
  )
);