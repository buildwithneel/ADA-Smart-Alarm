import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Mail, Lock, User, AlertCircle, Check } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/core/auth/AuthContext";
import { toast } from "@/core/toast/useToast";

export function SignupPage() {
  const { signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Password validation rules
  const hasMinLength = password.length >= 6;
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage("Please enter your full name.");
      return;
    }

    if (!email.trim()) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }

    if (!hasMinLength) {
      setErrorMessage("Password must be at least 6 characters long.");
      return;
    }

    if (!passwordsMatch) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    try {
      setIsEmailLoading(true);
      await signUp(email, password, name.trim());
      toast.success("Account Created!", "Welcome to ADA Adaptive Smart Alarm.");
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create account. Please try again.";
      setErrorMessage(msg);
      toast.error("Registration Failed", msg);
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleGoogleSignup = async () => {
    setErrorMessage(null);
    try {
      setIsGoogleLoading(true);
      await signInWithGoogle();
      toast.success("Welcome to ADA!", "Google registration successful.");
      navigate("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google Sign-Up failed. Please try again.";
      setErrorMessage(msg);
      toast.error("Google Sign-Up Error", msg);
    } finally {
      setIsGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 py-12 selection:bg-brand-500/30">
      <div className="max-w-md w-full space-y-6 text-center">
        {/* Logo Header */}
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-2xl gradient-brand flex items-center justify-center text-white font-extrabold text-xl shadow-lg shadow-brand-500/25">
            A
          </div>
          <h1 className="text-2xl font-black text-slate-100 tracking-tight">Create your account</h1>
          <p className="text-xs text-slate-400">Join ADA Adaptive Smart Alarm</p>
        </div>

        <Card className="p-6 sm:p-8 text-left border-white/10 space-y-5 bg-slate-900/40 backdrop-blur-xl">
          {/* Error Banner with shake animation */}
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

          {/* Google Sign-Up Provider Button */}
          <Button
            type="button"
            variant="outline"
            className="w-full h-11 border-slate-700/80 hover:bg-slate-800/60 text-slate-200 font-semibold gap-3 text-xs"
            onClick={handleGoogleSignup}
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
            Sign up with Google
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

          {/* Registration Form */}
          <form onSubmit={handleSignup} className="space-y-4" noValidate>
            <div className="space-y-1.5 text-left">
              <label htmlFor="signup-name" className="block text-xs font-semibold text-slate-300">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="signup-name"
                  type="text"
                  autoComplete="name"
                  placeholder="Alex Vance"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isEmailLoading || isGoogleLoading}
                  className="w-full bg-slate-900/60 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition-all"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <label htmlFor="signup-email" className="block text-xs font-semibold text-slate-300">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  placeholder="alex@domain.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isEmailLoading || isGoogleLoading}
                  className="w-full bg-slate-900/60 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition-all"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <label htmlFor="signup-password" className="block text-xs font-semibold text-slate-300">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="signup-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Minimum 6 characters"
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

              {/* Password strength checklist */}
              <div className="flex items-center gap-1.5 pt-1 text-[11px] text-slate-400">
                <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${hasMinLength ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-500"}`}>
                  <Check size={10} />
                </div>
                <span>At least 6 characters</span>
              </div>
            </div>

            <div className="space-y-1.5 text-left">
              <label htmlFor="signup-confirm-password" className="block text-xs font-semibold text-slate-300">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  id="signup-confirm-password"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isEmailLoading || isGoogleLoading}
                  className="w-full bg-slate-900/60 border border-slate-800 focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 rounded-xl pl-10 pr-10 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition-all"
                  required
                />
                <button
                  type="button"
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
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
              Create Account
              <ArrowRight size={16} />
            </Button>
          </form>

          <div className="pt-2 text-center">
            <Link to="/login" className="text-xs text-slate-400 hover:text-slate-200">
              Already have an account? <span className="text-brand-400 font-semibold hover:underline">Sign in</span>
            </Link>
          </div>
        </Card>

        <Link to="/" className="inline-block text-xs text-slate-500 hover:text-slate-400">
          ← Back to home
        </Link>
      </div>
    </div>
  );
}
