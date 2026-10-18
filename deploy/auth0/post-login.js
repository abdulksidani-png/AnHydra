/**
 * Auth0 Action. Trigger: Login / Post Login.
 *
 * Issues the two access-token claims the backend checks (app/auth.py, deploy/AUTH.md):
 *   https://anhydra.work/claims/token_kind = "user_access"
 *   https://anhydra.work/claims/admission  = "google" | "verified_edu"
 *
 * Admission policy:
 *   google        any login through the google-oauth2 connection.
 *   verified_edu  an email + password login whose address (a) ends in .edu, (b) is verified,
 *                 and (c) is on the administrator-controlled approved list in the Action
 *                 secret ALLOWED_EDU_EMAILS. The list is the "institutional membership"
 *                 evidence AUTH.md requires; the email suffix alone is not enough.
 *   anything else is refused here, with a message the sign-in page shows.
 *
 * Claims go ONLY into access tokens for our API (never ID tokens, never other APIs).
 * Client-credentials (machine) tokens never run this trigger, so they never get them.
 *
 * Action secrets (Actions > this Action > the key icon):
 *   ALLOWED_EDU_EMAILS   required for .edu sign-in. Comma- or space-separated, e.g.
 *                        "alice@ufl.edu, bob@ufl.edu". Empty or missing = no .edu admission.
 *   API_AUDIENCE         optional; defaults to https://anhydra.work/api. Must equal the
 *                        backend's AUTH0_AUDIENCE.
 */
const NAMESPACE = 'https://anhydra.work/claims/';
const DEFAULT_AUDIENCE = 'https://anhydra.work/api';
const GOOGLE_CONNECTION = 'google-oauth2';
const DATABASE_STRATEGY = 'auth0';

function normalise(email) {
  return typeof email === 'string' ? email.trim().toLowerCase() : '';
}

function isEdu(email) {
  const parts = email.split('@');
  return parts.length === 2 && parts[0] !== '' && parts[1].endsWith('.edu');
}

function approvedList(secret) {
  return new Set(String(secret || '').split(/[\s,]+/).map(normalise).filter(Boolean));
}

/** Pure decision, exported for the tests in actions.test.cjs. */
function admissionFor(event) {
  const connection = event.connection || {};
  if (connection.name === GOOGLE_CONNECTION && connection.strategy === 'google-oauth2') {
    return { admission: 'google' };
  }
  if (connection.strategy !== DATABASE_STRATEGY) {
    return { deny: 'This sign-in method is not enabled for AnHydra. Use Google or an approved .edu email.' };
  }
  const email = normalise(event.user && event.user.email);
  if (!isEdu(email)) {
    return { deny: 'Email sign-in is limited to approved .edu addresses. Use Google instead.' };
  }
  if (!(event.user && event.user.email_verified === true)) {
    return { deny: 'Verify your email first: open the link we sent you, then sign in again.' };
  }
  if (!approvedList(event.secrets && event.secrets.ALLOWED_EDU_EMAILS).has(email)) {
    return { deny: 'This .edu address is not on the AnHydra approved list. Use Google, or ask the team to add you.' };
  }
  return { admission: 'verified_edu' };
}

exports.onExecutePostLogin = async (event, api) => {
  const decision = admissionFor(event);
  if (decision.deny) {
    api.access.deny(decision.deny);
    return;
  }
  const audience = (event.secrets && event.secrets.API_AUDIENCE) || DEFAULT_AUDIENCE;
  // Logins that are not asking for an AnHydra API token get no AnHydra claims.
  if (!event.resource_server || event.resource_server.identifier !== audience) return;
  api.accessToken.setCustomClaim(NAMESPACE + 'token_kind', 'user_access');
  api.accessToken.setCustomClaim(NAMESPACE + 'admission', decision.admission);
};

exports.admissionFor = admissionFor;
