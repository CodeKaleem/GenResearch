"use client";

import { useState, useEffect } from "react";
import { supabase } from "../lib/supabase";
import AdminDashboard from "./components/AdminDashboard";
import AdminLogin from "./components/AdminLogin";

type View = "loading" | "login" | "dashboard";

export default function Home() {
  const [view, setView] = useState<View>("loading");

  useEffect(() => {
    // Check initial session
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setView("dashboard");
      } else {
        setView("login");
      }
    };

    checkSession();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setView("dashboard");
      } else {
        setView("login");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  if (view === "loading") {
    return (
      <div style={{ 
        height: "100vh", 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "center",
        background: "#f5f0e8",
        fontFamily: "'Crimson Pro', Georgia, serif"
      }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            border: "3px solid rgba(139,105,20,0.1)", 
            borderTop: "3px solid #8b6914", 
            borderRadius: "50%", 
            animation: "spin 1s linear infinite",
            margin: "0 auto 16px" 
          }} />
          <div style={{ color: "#8b6914", fontSize: 14, letterSpacing: "0.1em", textTransform: "uppercase" }}>Initializing System...</div>
        </div>
        <style>{`
          @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  return (
    <>
      {view === "login" && (
        <AdminLogin 
          onLoginSuccess={() => setView("dashboard")} 
        />
      )}
      {view === "dashboard" && (
        <AdminDashboard />
      )}
    </>
  );
}


