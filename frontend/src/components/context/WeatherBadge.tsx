import React from 'react';
import {
  Sun,
  Cloud,
  CloudRain,
  CloudLightning,
  Snowflake,
  CloudFog,
  Wind,
  AlertTriangle,
} from 'lucide-react';
import { WeatherCondition } from '@/core/types/context';

interface WeatherBadgeProps {
  condition?: WeatherCondition | string | null;
  conditionText?: string | null;
  temperatureC?: number | null;
  precipitationProbability?: number | null;
  isSevere?: boolean;
  attribution?: string | null;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const WeatherBadge: React.FC<WeatherBadgeProps> = ({
  condition = 'clear',
  conditionText,
  temperatureC,
  precipitationProbability,
  isSevere = false,
  attribution,
  className = '',
  size = 'md',
}) => {
  const normCond = (condition || 'clear').toLowerCase();
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  const getIcon = () => {
    if (isSevere) return <AlertTriangle className="text-amber-400 animate-pulse" />;
    switch (normCond) {
      case 'rain':
      case 'heavy_rain':
        return <CloudRain className="text-sky-400" />;
      case 'thunderstorm':
        return <CloudLightning className="text-amber-400" />;
      case 'snow':
        return <Snowflake className="text-blue-200" />;
      case 'fog':
        return <CloudFog className="text-slate-300" />;
      case 'windy':
        return <Wind className="text-teal-300" />;
      case 'cloudy':
        return <Cloud className="text-slate-400" />;
      case 'clear':
      default:
        return <Sun className="text-amber-400" />;
    }
  };

  const displayText = conditionText || normCond.charAt(0).toUpperCase() + normCond.slice(1);

  return (
    <div
      title={attribution ? `Data source: ${attribution}` : undefined}
      className={`inline-flex items-center gap-1.5 rounded-full font-medium backdrop-blur-md transition-all ${sizeClasses} ${
        isSevere
          ? 'bg-amber-950/40 text-amber-300 border border-amber-500/30'
          : normCond === 'rain' || normCond === 'heavy_rain' || normCond === 'thunderstorm'
          ? 'bg-sky-950/40 text-sky-200 border border-sky-500/30'
          : 'bg-white/5 text-slate-200 border border-white/10'
      } ${className}`}
    >
      <span className="flex-shrink-0">{getIcon()}</span>
      <span>{displayText}</span>
      {temperatureC !== undefined && temperatureC !== null && (
        <span className="text-slate-400">· {Math.round(temperatureC)}°C</span>
      )}
      {precipitationProbability !== undefined && precipitationProbability !== null && precipitationProbability > 0 && (
        <span className="text-sky-300 font-semibold">{precipitationProbability}% rain</span>
      )}
    </div>
  );
};
