import { NavLink } from "react-router-dom";
import { Compass, Clock, PlusCircle, MapPin, Settings } from "lucide-react";
import { cn } from "@/core/utils/cn";

export function BottomNav() {
  const navItems = [
    { to: "/dashboard", label: "Today", icon: Compass },
    { to: "/alarms", label: "Alarms", icon: Clock },
    { to: "/alarms/new", label: "Create", icon: PlusCircle, isPrimary: true },
    { to: "/destinations", label: "Places", icon: MapPin },
    { to: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-800 bg-slate-950/90 backdrop-blur-xl">
      <div className="max-w-md mx-auto flex items-center justify-around h-16 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center justify-center gap-1 transition-all duration-200 select-none py-1 px-2.5 rounded-xl",
                  item.isPrimary
                    ? "text-brand-400 font-semibold"
                    : isActive
                    ? "text-brand-400 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div
                    className={cn(
                      "p-1 rounded-lg transition-transform duration-200",
                      isActive && !item.isPrimary && "scale-110",
                      item.isPrimary &&
                        "bg-brand-600 text-white p-2.5 rounded-full -mt-6 shadow-lg shadow-brand-500/40 border border-brand-400/40"
                    )}
                  >
                    <Icon size={item.isPrimary ? 22 : 18} />
                  </div>
                  <span className="text-[10px] tracking-tight">{item.label}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
