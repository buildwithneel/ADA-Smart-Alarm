import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusIndicator } from "@/components/ui/status-indicator";
import {
  heroEntrance,
  heroTextStagger,
  heroCtaEntrance,
} from "@/core/animations/variants";

export function LandingPage() {
  const comparison = [
    {
      feature: "Trigger Calculation",
      traditional: "Fixed, static manual time (e.g. 7:00 AM)",
      ada: "Continuous live ETA back-calculated from arrival target",
    },
    {
      feature: "Morning Traffic Spike",
      traditional: "You wake up at same time and arrive late",
      ada: "Automatically shifts alarm earlier to preserve on-time arrival",
    },
    {
      feature: "Adverse Weather",
      traditional: "Ignored until you step outside",
      ada: "Dynamically factors rain/fog into commute buffers",
    },
    {
      feature: "Manual Daily Changes",
      traditional: "Required every night before bed",
      ada: "Zero manual adjustment needed",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-brand-500/30">
      {/* Top Navigation */}
      <header className="border-b border-white/5 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between max-w-6xl">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl gradient-brand flex items-center justify-center text-white font-extrabold shadow-sm">
              A
            </div>
            <span className="font-extrabold text-base tracking-tight text-white">
              ADA
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="primary" size="sm" className="gap-1.5">
                Launch App
                <ArrowRight size={14} />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-6 py-16 md:py-24 max-w-5xl text-center space-y-12">
        <motion.div
          variants={heroEntrance}
          initial="initial"
          animate="animate"
          className="space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 shadow-sm">
            <StatusIndicator status="active" pulse />
            <span>Autonomous Location-Based Smart Alarm</span>
          </div>

          <motion.h1
            variants={heroTextStagger}
            initial="initial"
            animate="animate"
            className="text-4xl sm:text-6xl font-black tracking-tight text-slate-100 max-w-3xl mx-auto leading-tight"
          >
            Never manually set a morning alarm again.
          </motion.h1>

          <p className="text-base sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            ADA recalculates your exact wake-up time every 60 seconds based on live traffic,
            destination distance, and your morning routine. You pick when to arrive; ADA handles the rest.
          </p>

          <motion.div
            variants={heroCtaEntrance}
            initial="initial"
            animate="animate"
            className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2"
          >
            <Link to="/dashboard" className="w-full sm:w-auto">
              <Button size="lg" className="w-full gap-2 shadow-xl shadow-brand-500/20 font-bold">
                Launch ADA Dashboard
                <ArrowRight size={18} />
              </Button>
            </Link>
            <Link to="/alarms/new" className="w-full sm:w-auto">
              <Button variant="outline" size="lg" className="w-full">
                Create First Smart Alarm
              </Button>
            </Link>
          </motion.div>
        </motion.div>

        {/* Live Simulation Card */}
        <Card className="p-6 md:p-8 border-brand-500/20 bg-slate-900/60 backdrop-blur-xl max-w-2xl mx-auto text-left space-y-6 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                Live Dynamic Calculation Example
              </span>
            </div>
            <span className="text-xs text-slate-400 font-mono">CHARUSAT Campus</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Target Arrival</span>
              <span className="text-xl font-black text-slate-100">09:00 AM</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-white/5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Live Commute</span>
              <span className="text-xl font-black text-slate-100">38 min</span>
            </div>
            <div className="p-3.5 rounded-xl bg-brand-600/20 border border-brand-500/40">
              <span className="text-[10px] uppercase font-bold text-brand-300 block mb-1">ADA Wake Time</span>
              <span className="text-xl font-black text-brand-300">07:42 AM</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 text-center">
            If unexpected traffic adds 15 minutes to your route tomorrow morning, ADA triggers at <strong>07:27 AM</strong> automatically.
          </p>
        </Card>

        {/* Architecture Comparison Table */}
        <div className="max-w-3xl mx-auto space-y-4 pt-8 text-left">
          <h2 className="text-xl font-bold text-slate-100 text-center">
            Why Traditional Alarms Fail Commuters
          </h2>
          <div className="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900/40">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3 font-semibold">Scenario</th>
                  <th className="p-3 font-semibold">Traditional Alarm</th>
                  <th className="p-3 font-semibold text-brand-400">ADA Smart Alarm</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {comparison.map((row) => (
                  <tr key={row.feature} className="hover:bg-slate-800/30">
                    <td className="p-3 font-bold text-slate-200">{row.feature}</td>
                    <td className="p-3 text-slate-400">{row.traditional}</td>
                    <td className="p-3 text-slate-200 font-semibold">{row.ada}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-8 bg-slate-950 text-slate-500 text-xs">
        <div className="container mx-auto px-6 max-w-6xl flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 ADA (Adaptive Dynamic Alarm). Built for intelligent mobility.</p>
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="hover:text-slate-300">Dashboard</Link>
            <Link to="/destinations" className="hover:text-slate-300">Destinations</Link>
            <Link to="/settings" className="hover:text-slate-300">Settings</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
