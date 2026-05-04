"use client";

import { useState } from "react";
import Home from "./Components/Home";
import Dashboard from "./Components/Dashboard";

export default function Page() {
  const [view, setView] = useState<"home" | "dashboard">("home");

  return (
    <>
      {view === "home" ? (
        <Home onNavigate={() => setView("dashboard")} />
      ) : (
        <Dashboard onNavigateHome={() => setView("home")} />
      )}
    </>
  );
}
