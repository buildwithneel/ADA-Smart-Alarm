import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Mail, Lock, AlertCircle, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/core/auth/AuthContext";
import { toast } from "@/core/toast/useToast";

export function LoginPage() {
  const { signIn, signInWithGoogle, resetPassword } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Forgot password modal/state
  const [isForgotOpen, setIsForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isForgotLoading, setIsForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email || !password) {
      setErrorMessage("Please enter both your email address and password.");
      return;
    }

    try {
      setIsEmailLoading(true);
      await signIn(email, password);
      toast.success("Welcome back!", "Successfully signed in to ADA.");
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to sign in. Please verify your credentials.";
      setErrorMessage(msg);
      toast.error("Sign In Failed", msg);
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setErrorMessage(null);
    try {
      setIsGoogleLoading(true);
      await signInWithGoogle();
      toast.success("Welcome back!", "Google authentication successful.");
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google Sign-In failed. Please try again.";
      setErrorMessage(msg);
      toast.error("Google Sign-In Error", msg);
    } finally {
      setIsGoogleLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError(null);
    setForgotSuccess(false);

    if (!forgotEmail) {
      setForgotError("Please enter your email address.");
      return;
    }

    try {
      setIsForgotLoading(true);
      await resetPassword(forgotEmail);
      setForgotSuccess(true);
      toast.success("Reset Email Sent", "Check your inbox for password reset instructions.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unable to send password reset email.";
      setForgotError(msg);
    } finally {
      setIsForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12 selection:bg-brand-500/30">
      <div className="max-w-md w-full space-y-6 text-center">
        {/* Brand Logo Header */}
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-2xl gradient-brand flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-brand-500/25">
            A
          </div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight">Sign in to ADA</h1>
          <p className="text-xs text-slate-400">Adaptive Dynamic Alarm System</p>
        </div>

        <Card className="p-6 sm:p-8 text-left border-white/10 space-y-5 bg-slate-900/40 backdrop-blur-xl">
          {/* Error Banner with subtle shake animation */}
          <AnimatePresence mode="wait">
            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: -6, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -6, scale: 0.98 }}
                role="alert"
                aria-live="assertive"
                className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-rose-300 text-xs"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                <span className="leading-relaxed">{errorMessage}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Google Sign-In Provider Button */}
          <Button
            type="button"
            variant="outline"
            className="w-full h-11 border-slate-700/80 hover:bg-slate-800/60 text-slate-200 font-semibold gap-3 text-xs"
            onClick={handleGoogleLogin}
            disabled={isGoogleLoading || isEmailLoading}
            isLoading={isGoogleLoading}
          >
            {!isGoogleLoading && (
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.64v3.03h3.88c2.27-2.09 3.66-5.17 3.66-9.11z"
                />
                <path
                  fill="#34A853"
                  d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.03c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.26v3.13C3.26 21.36 7.33 24 12 24z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.28 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.58H1.26C.46 8.17 0 9.99 0 12s.46 3.83 1.26 5.42l4.02-3.13z"
                />
                <path
                  fill="#EA4335"
                  d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.26 6.58l4.02 3.13c.95-2.83 3.6-4.96 6.72-4.96z"
                />
              </svg>
            )}
            Continue with Google
          </Button>

          {/* Divider */}
          <div className="relative py-1">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <div className="relative flex justify-center text-[11px] uppercase font-bold text-slate-500">
              <span className="bg-slate-900/90 px-3">or continue with email</span>
            </div>
          </div>

          {/* Email / Password Form */}
          <form onSubmit={handleEmailLogin} className="space-y-4" noValidate>
            <div className="space-y-1.5 text-left">
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-300">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isEmailLoading || isGoogleLoading}
                  className="w-full bg-slate-900/60 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition-all"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <div className="flex items-center justify-between">
                <label htmlFor="login-password" className="block text-xs font-semibold text-slate-300">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setForgotEmail(email);
                    setIsForgotOpen(true);
                  }}
                  className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isEmailLoading || isGoogleLoading}
                  className="w-full bg-slate-900/60 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 rounded-xl pl-10 pr-10 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition-all"
                  required
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full font-bold gap-2 mt-2 h-11"
              isLoading={isEmailLoading}
              disabled={isEmailLoading || isGoogleLoading}
            >
              Sign In
              <ArrowRight size={16} />
            </Button>
          </form>

          <div className="pt-2 text-center">
            <Link to="/signup" className="text-xs text-slate-400 hover:text-slate-200">
              Don't have an account? <span className="text-brand-400 font-semibold hover:underline">Sign up</span>
            </Link>
          </div>
        </Card>

        {/* Forgot Password Drawer/Modal Overlay */}
        <AnimatePresence>
          {isForgotOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="max-w-sm w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4 text-left"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-100">Reset Password</h3>
                  <button
                    onClick={() => {
                      setIsForgotOpen(false);
                      setForgotError(null);
                      setForgotSuccess(false);
                    }}
                    className="text-slate-400 hover:text-slate-200 text-sm font-semibold"
                  >
                    ✕
                  </button>
                </div>

                <p className="text-xs text-slate-400">
                  Enter your registered email address and we'll send you instructions to reset your password.
                </p>

                {forgotSuccess ? (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-2.5 text-emerald-300 text-xs">
                    <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
                    <p>Password reset email sent! Please check your inbox and spam folder.</p>
                  </div>
                ) : (
                  <form onSubmit={handleForgotPassword} className="space-y-4">
                    {forgotError && (
                      <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                        <AlertCircle size={14} className="shrink-0" />
                        <span>{forgotError}</span>
                      </div>
                    )}
                    <div className="space-y-1.5">
                      <label htmlFor="forgot-email" className="block text-xs font-semibold text-slate-300">
                        Email Address
                      </label>
                      <input
                        id="forgot-email"
                        type="email"
                        placeholder="you@domain.com"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        disabled={isForgotLoading}
                        className="w-full bg-slate-950 border border-slate-800 focus:border-brand-500 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 outline-none"
                        required
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsForgotOpen(false)}
                        disabled={isForgotLoading}
                      >
                        Cancel
                      </Button>
                      <Button
                        type="submit"
                        variant="primary"
                        size="sm"
                        isLoading={isForgotLoading}
                        disabled={isForgotLoading}
                      >
                        Send Reset Link
                      </Button>
                    </div>
                  </form>
                )}
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        <Link to="/" className="inline-block text-xs text-slate-500 hover:text-slate-400">
          ← Back to home
        </Link>
      </div>
    </div>
  );
}
