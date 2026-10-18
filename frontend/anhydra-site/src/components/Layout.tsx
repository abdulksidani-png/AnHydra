import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import "@/anhydra.css";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          AnHydra
        </Link>
        <nav aria-label="Main">
          <Link to="/" activeOptions={{ exact: true }} activeProps={{ "aria-current": "page" }}>
            Home
          </Link>
          <Link to="/screen" activeProps={{ "aria-current": "page" }}>
            Screen
          </Link>
          <Link to="/about" activeProps={{ "aria-current": "page" }}>
            About
          </Link>
        </nav>
      </header>
      {children}
    </>
  );
}
