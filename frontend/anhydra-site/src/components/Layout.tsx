import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { AccountMenu } from "@/components/AccountMenu";
import { useSession } from "@/auth/session";
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
          <AccountMenu />
        </nav>
      </header>
      <LoginError />
      {children}
    </>
  );
}

// Auth0 sends a refused login back with an error instead of a session. Without this the page would
// look as if nothing happened.
function LoginError() {
  const session = useSession();
  const [dismissed, setDismissed] = useState<string | null>(null);
  if (session.mode !== "auth0" || !session.loginError || session.loginError === dismissed) return null;
  return (
    <div className="login-error" role="alert">
      <p>
        <strong>Couldn't log you in.</strong> {session.loginError}
      </p>
      <button type="button" className="ghost-btn" onClick={() => setDismissed(session.loginError)}>
        Dismiss
      </button>
    </div>
  );
}
