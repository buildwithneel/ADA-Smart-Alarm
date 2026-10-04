import React from "react";
import { Navigation, ShieldCheck, Clock, MapPin } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";

import { Button } from "@/components/ui/button";

export interface LocationPermissionDialogProps {
  isOpen: boolean;
  isPermanentlyDenied?: boolean;
  onClose: () => void;
  onAllow: () => void;
}

export const LocationPermissionDialog: React.FC<LocationPermissionDialogProps> = ({
  isOpen,
  isPermanentlyDenied = false,
  onClose,
  onAllow,
}) => {
  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={isPermanentlyDenied ? "Location Permission Disabled" : "Enable Location for Dynamic Alarms"}
      description="ADA calculates real-time traffic delays from your starting point."
    >
      <div className="space-y-4 text-left">
        {/* Privacy by Design Highlights */}
        <div className="space-y-3 p-3.5 rounded-xl bg-slate-950/70 border border-white/5 text-xs">
          <div className="flex items-start gap-2.5">
            <Clock size={16} className="text-brand-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-200 block">Why it's requested</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                ADA measures real-time road conditions between where you are and your destination so your alarm wakes you at the exact optimal minute.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <MapPin size={16} className="text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-200 block">When it's used</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Only evaluated on-demand during alarm scheduling and route estimation. Never tracked when ADA is idle.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <ShieldCheck size={16} className="text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-200 block">Privacy Guarantee</span>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Your location trail is never saved to a database. All origin coordinates remain strictly in-memory.
              </p>
            </div>
          </div>
        </div>

        {/* If permanently denied, show browser instructions */}
        {isPermanentlyDenied ? (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
            <p className="font-semibold mb-1">To enable location in your browser:</p>
            <ol className="list-decimal list-inside space-y-1 text-[11px] text-amber-200/90">
              <li>Click the lock or site settings icon in your URL address bar.</li>
              <li>Toggle <strong>Location</strong> permissions to <strong>Allow</strong>.</li>
              <li>Refresh or retry in ADA to calculate live commute times.</li>
            </ol>
          </div>
        ) : null}

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            {isPermanentlyDenied ? "Close" : "Not Now"}
          </Button>
          {!isPermanentlyDenied ? (
            <Button
              type="button"
              variant="primary"
              onClick={onAllow}
              className="gap-1.5 font-bold"
            >
              <Navigation size={14} />
              Allow Location Access
            </Button>
          ) : (
            <Button
              type="button"
              variant="primary"
              onClick={onAllow}
              className="gap-1.5 font-bold"
            >
              Retry After Enabling
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
};
