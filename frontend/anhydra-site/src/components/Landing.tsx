import { Link } from "@tanstack/react-router";
import { Backdrop } from "@/components/Backdrop";
import { useSession } from "@/auth/session";

export function Landing() {
  const session = useSession();
  // Signed out, the button goes straight to sign-in and returns to /screen afterwards.
  const signedOut = session.mode === "auth0" && !session.checking && !session.viewer;
  return (
    <div className="landing">
      <Backdrop />
      <section className="wow" aria-labelledby="wow-title">
        <h1 id="wow-title" className="wow-title">
          A tardigrade can lose nearly all of its water, stop, and come back
        </h1>
        <p className="scroll-cue" aria-hidden="true">
          scroll
          <span />
        </p>
      </section>
      <section className="line-block last">
        <p className="line scrub">Paste a protein. Find out if it can survive total drying.</p>
        <Link
          to="/screen"
          viewTransition
          className="screen-btn cta scrub"
          onClick={(e) => {
            if (signedOut && session.mode === "auth0") {
              e.preventDefault();
              session.signIn("/screen");
            }
          }}
        >
          Screen a sequence <span className="arrow" aria-hidden="true">→</span>
        </Link>
        <p className="credit">Electron micrograph of a tardigrade: everviz, behance.net/everviz</p>
      </section>
    </div>
  );
}
