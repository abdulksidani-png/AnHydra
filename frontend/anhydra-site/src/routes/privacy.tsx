import { Link, createFileRoute } from "@tanstack/react-router";
import settings from "@/config/settings.json";

export const Route = createFileRoute("/privacy")({
  head: () => settings.routes["/privacy"],
  component: PrivacyPage,
});

function PrivacyPage() {
  return (
    <main className="page about privacy mx-auto flex max-w-3xl flex-col gap-6 pb-16">
      <h1>Privacy</h1>
      <p className="muted small">Last updated 18 October 2026</p>

      <section className="flex flex-col gap-2">
        <h2>Signing in</h2>
        <p>
          Sign-in is handled by Auth0. If you sign in with Google, Auth0 receives your name, email address and
          profile photo from Google. If you sign up with an email address, Auth0 keeps your email and password;
          AnHydra never sees your password.
        </p>
        <p>
          AnHydra's own server keeps a small account record: an internal ID, the Auth0 identifier of your login,
          when the account was created and when it was last used. Your name and photo are shown in your browser
          but are not stored by AnHydra.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2>Sequences you screen</h2>
        <p>
          A sequence you screen is sent to AnHydra's server to be scored. It is not saved, and the server does not
          log it. To write the plain-language explanation, the score, the call, the nearest known protective
          protein and the features that drove the score are sent to Google's Gemini API. Your sequence itself is
          not.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2>Other services your browser contacts</h2>
        <p>
          AlphaFold DB (EMBL-EBI), for the predicted structure of the nearest known protein; Google Fonts, for the
          typefaces; Duda's image server, for the photo on the home page; and GitHub, for the team's profile
          pictures on the About page.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2>Stored in your browser</h2>
        <p>
          A note that you have seen the tutorial, and, only while you are signing in, the sequence you pasted, so
          it is back in the box when you return. Auth0 keeps its own sign-in session on its domain.
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2>What AnHydra does not do</h2>
        <p>No advertising, no analytics or tracking, and no selling or sharing of your information.</p>
      </section>

      <section className="flex flex-col gap-2">
        <h2>Deleting your account</h2>
        <p>
          Contact the team through the links on the <Link to="/about">About</Link> page. We will delete your
          AnHydra account record and your Auth0 login.
        </p>
      </section>
    </main>
  );
}
