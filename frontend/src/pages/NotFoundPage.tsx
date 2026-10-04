import { Link } from "react-router-dom";
import { Compass, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6 space-y-4">
      <div className="w-16 h-16 rounded-3xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
        <Compass size={32} />
      </div>
      <div>
        <h1 className="text-3xl font-black text-slate-100">404</h1>
        <p className="text-sm text-slate-400 mt-1">Page not found or route does not exist.</p>
      </div>
      <Link to="/">
        <Button variant="primary" className="gap-2 mt-2">
          <Home size={16} />
          Return to Dashboard
        </Button>
      </Link>
    </div>
  );
}
