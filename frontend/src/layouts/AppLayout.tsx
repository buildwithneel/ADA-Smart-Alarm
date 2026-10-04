import { useState } from "react";
import { Outlet } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { DesktopSidebar } from "@/components/navigation/DesktopSidebar";
import { TopNavbar } from "@/components/navigation/TopNavbar";
import { BottomNav } from "@/components/common/BottomNav";
import { CommandPalette } from "@/components/ui/command-palette";
import { NotificationDrawer } from "@/components/navigation/NotificationDrawer";
import { ToastContainer } from "@/components/ui/toast";
import { pageVariants } from "@/core/animations/variants";
import { ApiNotificationRepository } from "@/core/repositories/api/ApiNotificationRepository";

export function AppLayout() {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["unread-notifications-count"],
    queryFn: () => ApiNotificationRepository.getUnreadCount(),
    refetchInterval: 30000,
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex antialiased selection:bg-brand-500/30">
      {/* Desktop Sidebar (visible on lg screens) */}
      <DesktopSidebar onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          unreadCount={unreadCount}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full pb-24 lg:pb-12">
          <AnimatePresence mode="wait">
            <motion.div
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Mobile Bottom Navigation (visible on mobile & tablet) */}
      <div className="lg:hidden">
        <BottomNav />
      </div>

      {/* Global Modals & Drawers */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />

      <NotificationDrawer
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
      />

      <ToastContainer />
    </div>
  );
}
