import React, { useState, useEffect, useRef } from "react";
import { Search, MapPin, Loader2, X } from "lucide-react";
import { GeocodingResult } from "@/core/maps/models/GeocodingResult";
import { locationApiClient } from "@/core/api/locationClient";
import { cn } from "@/core/utils/cn";

export interface DestinationSearchInputProps {
  id?: string;
  label?: string;
  placeholder?: string;
  initialValue?: string;
  onSelect: (result: GeocodingResult) => void;
  error?: string;
  className?: string;
}

export const DestinationSearchInput: React.FC<DestinationSearchInputProps> = ({
  id = "destination-search",
  label = "Destination",
  placeholder = "Search places, landmarks (e.g. CHARUSAT)...",
  initialValue = "",
  onSelect,
  error,
  className,
}) => {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<GeocodingResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  // Synchronize initial value changes from external sources
  useEffect(() => {
    if (initialValue !== query) {
      setQuery(initialValue);
    }
  }, [initialValue]);

  // Debounced search (300ms) to prevent provider request flooding
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const results = await locationApiClient.searchGeocoding(query, 5);
        setSuggestions(results);
        setIsOpen(results.length > 0);
        setSelectedIndex(-1);
      } catch (err) {
        console.error("Geocoding autocomplete failed:", err);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener to dismiss suggestion dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (item: GeocodingResult) => {
    setQuery(item.formattedAddress);
    setIsOpen(false);
    onSelect(item);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[selectedIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={cn("relative space-y-1.5 text-left w-full", className)}>
      {label && (
        <label htmlFor={id} className="block text-xs font-semibold text-slate-300">
          {label}
        </label>
      )}

      <div className="relative">
        <Search
          size={16}
          className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
        />

        <input
          id={id}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          className={cn(
            "w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors shadow-inner",
            error && "border-rose-500 focus:border-rose-500"
          )}
        />

        {isLoading ? (
          <Loader2
            size={14}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 animate-spin text-brand-400"
          />
        ) : query ? (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setSuggestions([]);
              setIsOpen(false);
            }}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            aria-label="Clear destination query"
          >
            <X size={14} />
          </button>
        ) : null}
      </div>

      {error && <p className="text-[11px] text-rose-400 font-medium">{error}</p>}

      {/* Autocomplete Suggestions Dropdown */}
      {isOpen && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full mt-1.5 z-50 bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden backdrop-blur-md divide-y divide-slate-800">
          {suggestions.map((item, idx) => (
            <button
              key={item.placeId || `${item.latitude}-${item.longitude}-${idx}`}
              type="button"
              onClick={() => handleSelect(item)}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={cn(
                "w-full px-3.5 py-2.5 text-left flex items-start gap-2.5 transition-colors text-xs",
                selectedIndex === idx
                  ? "bg-brand-600/20 text-white"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              )}
            >
              <MapPin size={14} className="text-brand-400 mt-0.5 shrink-0" />
              <div className="flex-1 truncate">
                <span className="font-semibold block truncate">
                  {item.formattedAddress.split(",")[0]}
                </span>
                <span className="text-[10px] text-slate-400 block truncate">
                  {item.formattedAddress}
                </span>
              </div>
              <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                {item.provider}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
