import { Sun, CloudRain, Wind, Thermometer } from "lucide-react";
import { Card } from "@/components/ui/card";

export interface WeatherCardProps {
  temperatureC?: number;
  condition?: string;
  bufferImpactMinutes?: number;
}

export function WeatherCard({
  temperatureC = 23,
  condition = "Clear Sky",
  bufferImpactMinutes = 0,
}: WeatherCardProps) {
  const isRain = condition.toLowerCase().includes("rain");

  return (
    <Card className="p-4 text-left border-white/10 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Route Micro-Weather
        </span>
        <span className="text-xs font-semibold text-emerald-400">
          {bufferImpactMinutes === 0 ? "No Delay" : `+${bufferImpactMinutes}m Buffer`}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
            {isRain ? <CloudRain size={20} /> : <Sun size={20} />}
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-100">{condition}</h4>
            <p className="text-xs text-slate-400">Low humidity • Visibility 10km</p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-2xl font-black text-slate-100">{temperatureC}°</span>
          <span className="text-[10px] text-slate-400 block font-medium">Celsius</span>
        </div>
      </div>

      <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1">
          <Thermometer size={12} className="text-slate-400" />
          Feels like 24°
        </span>
        <span className="flex items-center gap-1">
          <Wind size={12} className="text-slate-400" />
          8 km/h wind
        </span>
      </div>
    </Card>
  );
}
