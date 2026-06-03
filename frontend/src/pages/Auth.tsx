import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "../stores/useAppStore";
import axios from "axios";
import { KeyRound, Mail, User as UserIcon, Brain, ArrowRight, Loader2 } from "lucide-react";

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setToken, checkAuth } = useAppStore();


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        const res = await axios.post("/auth/login", { email, password });
        setToken(res.data.access_token);
        localStorage.setItem("refresh_token", res.data.refresh_token);
      } else {
        await axios.post("/auth/signup", { email, password, full_name: fullName });
        // Auto-login after signup
        const res = await axios.post("/auth/login", { email, password });
        setToken(res.data.access_token);
        localStorage.setItem("refresh_token", res.data.refresh_token);
      }

      await checkAuth();
      navigate("/");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Authentication failed. Try again.");
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 p-4 font-sans text-white">
      {/* Background blobs */}
      <div className="absolute top-0 -left-40 h-96 w-96 rounded-full bg-violet-600/10 blur-3xl" />
      <div className="absolute bottom-0 -right-40 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />

      {/* Main card */}
      <div className="glass-panel w-full max-w-md rounded-2xl p-8 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400">
            <Brain className="h-8 w-8" />
          </div>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-white">
            Knowledge Hub AI
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            {isLogin ? "Welcome back! Access your isolated workspaces." : "Create your account and start querying."}
          </p>
        </div>

        {error && (
          <div className="mt-6 rounded-lg bg-red-950/50 border border-red-800/40 p-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {!isLogin && (
            <div>
              <label className="text-xs font-medium text-slate-300">Full Name</label>
              <div className="relative mt-1">
                <UserIcon className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  required
                  placeholder="John Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900/60 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-slate-300">Email Address</label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
              <input
                type="email"
                required
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-900/60 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300">Password</label>
            <div className="relative mt-1">
              <KeyRound className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-900/60 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-lg transition-transform hover:scale-[1.01] hover:from-violet-500 hover:to-indigo-500 active:scale-[0.99] disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                {isLogin ? "Sign In" : "Register"}
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>


        <p className="mt-6 text-center text-xs text-slate-400">
          {isLogin ? "New to Knowledge Hub?" : "Already have an account?"}{" "}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="font-medium text-violet-400 hover:underline"
          >
            {isLogin ? "Create an account" : "Sign in here"}
          </button>
        </p>
      </div>
    </div>
  );
}
