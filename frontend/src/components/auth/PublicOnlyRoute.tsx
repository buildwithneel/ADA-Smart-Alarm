import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/core/auth/AuthContext";
import { Spinner } from "@/components/ui/spinner";

interface PublicOnlyRouteProps {
  children?: React.ReactNode;
}

export const PublicOnlyRoute: React.FC<PublicOnlyRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 rounded-2xl gradient-brand flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-brand-500/25 animate-pulse">
          A
        </div>
        <div className="flex items-center gap-2 text-slate-400 text-sm font-medium">
          <Spinner size="sm" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};
