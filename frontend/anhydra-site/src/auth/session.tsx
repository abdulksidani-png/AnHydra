import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { AccountError, fetchAccount, type AccountFailure, type AccountProfile } from "@/auth/account";
import { clearAccessTokenProvider, setAccessTokenProvider, tokenEpoch } from "@/auth/token";

// What every page knows about who is using the site. "public" and "misconfigured" mirror the build
// mode; "auth0" carries the signed-in person and the state of their AnHydra account.
export type Viewer = { name: string | null; picture: string | null; emailUnverified: boolean };

export type Account =
  | { status: "none" }
  | { status: "loading" }
  | { status: "ready"; profile: AccountProfile }
  | { status: "error"; kind: AccountFailure; message: string };

export type Session =
  | { mode: "public" }
  | { mode: "misconfigured"; missing: string[] }
  | {
      mode: "auth0";
      checking: boolean;
      viewer: Viewer | null;
      account: Account;
      loginError: string | null;
      signIn: (returnTo?: string) => void;
      signOut: () => void;
      retry: () => void;
    };

const SessionContext = createContext<Session>({ mode: "public" });

export function useSession(): Session {
  return useContext(SessionContext);
}

export function StaticSession({ session, children }: { session: Session; children: ReactNode }) {
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

// Installs the token provider for the signed-in subject, resolves /me for it, and throws both away
// on sign-out or identity change, so a late answer for one person never fills in the next.
export function Auth0Session({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated, user, error, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0();
  const subject = isAuthenticated ? (user?.sub ?? null) : null;
  const [account, setAccount] = useState<Account>({ status: "none" });
  const run = useRef(0);

  const load = useCallback(async () => {
    const id = ++run.current;
    const epoch = tokenEpoch();
    setAccount({ status: "loading" });
    try {
      const { profile } = await fetchAccount();
      if (id === run.current && epoch === tokenEpoch()) setAccount({ status: "ready", profile });
    } catch (e) {
      if (id !== run.current || epoch !== tokenEpoch()) return;
      const known = e instanceof AccountError;
      setAccount({ status: "error", kind: known ? e.kind : "failed", message: known ? e.message : "Could not load your account." });
    }
  }, []);

  useEffect(() => {
    run.current += 1;
    if (!subject) {
      clearAccessTokenProvider();
      setAccount({ status: "none" });
      return;
    }
    setAccessTokenProvider(() => getAccessTokenSilently());
    void load();
    return () => {
      run.current += 1;
      clearAccessTokenProvider();
    };
  }, [subject, getAccessTokenSilently, load]);

  // A refused login comes back as ?error=…&error_description=… on the redirect URL. Keep the message
  // (the page shows it) but take it out of the address bar, so a reload does not replay it.
  useEffect(() => {
    if (error && new URLSearchParams(window.location.search).has("error")) {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
  }, [error]);

  const signIn = useCallback(
    (returnTo?: string) => void loginWithRedirect({ appState: { returnTo: returnTo ?? window.location.pathname } }),
    [loginWithRedirect],
  );
  const signOut = useCallback(() => {
    run.current += 1;
    clearAccessTokenProvider();
    setAccount({ status: "none" });
    void logout({ logoutParams: { returnTo: window.location.origin } });
  }, [logout]);

  // Google accounts show their photo; email accounts get the initial placeholder.
  const viewer: Viewer | null = subject
    ? {
        name: user?.name || user?.email || null,
        picture: subject.startsWith("google-oauth2|") && user?.picture ? user.picture : null,
        emailUnverified: subject.startsWith("auth0|") && user?.email_verified === false,
      }
    : null;

  const session: Session = {
    mode: "auth0",
    checking: isLoading,
    viewer,
    account,
    loginError: error?.message ?? null,
    signIn,
    signOut,
    retry: () => void load(),
  };
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}
