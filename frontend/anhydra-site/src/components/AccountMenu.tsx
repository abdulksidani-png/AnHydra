import { useEffect, useRef, useState } from "react";
import { useSession } from "@/auth/session";

function Silhouette() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true" focusable="false">
      <circle cx="12" cy="8.5" r="4" />
      <path d="M4 20.5c0-4.1 3.6-7 8-7s8 2.9 8 7v.5H4z" />
    </svg>
  );
}

// Top-right account control. Signed out: a silhouette whose menu offers "Log in". Signed in: the
// Google photo, or the first letter of the name for email accounts, with the name and "Log out".
// Opens on hover and on click, so it works with a mouse, a keyboard and a touchscreen.
export function AccountMenu() {
  const session = useSession();
  const [open, setOpen] = useState(false);
  const [brokenPicture, setBrokenPicture] = useState<string | null>(null);
  const root = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", key);
    };
  }, [open]);

  if (session.mode !== "auth0") return null;
  const { viewer, checking } = session;
  const label = viewer ? `Account: ${viewer.name ?? "signed in"}` : "Account: signed out";

  return (
    <div className="account" ref={root} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="avatar" aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {viewer?.picture && viewer.picture !== brokenPicture ? (
          <img src={viewer.picture} alt="" referrerPolicy="no-referrer" width={36} height={36} onError={() => setBrokenPicture(viewer.picture)} />
        ) : viewer ? (
          <span aria-hidden="true">{(viewer.name ?? "?").trim().charAt(0).toUpperCase()}</span>
        ) : (
          <Silhouette />
        )}
      </button>
      {open ? (
        <div className="account-menu" role="menu">
          {viewer ? <p className="account-name">{viewer.name ?? "Signed in"}</p> : null}
          <button
            type="button"
            role="menuitem"
            className="ghost-btn"
            disabled={checking}
            onClick={() => {
              setOpen(false);
              if (viewer) session.signOut();
              else session.signIn();
            }}
          >
            {checking ? "Checking…" : viewer ? "Log out" : "Log in"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
