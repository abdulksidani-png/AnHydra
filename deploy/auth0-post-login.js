/**
 * Auth0 Post Login Action for AnHydra. Paste into Auth0: Actions > Library > Create Action >
 * "Login / Post Login", deploy it, then add it to the Login flow (Actions > Flows > Login).
 *
 * It adds two signed claims to the API access token, which the backend requires (deploy/AUTH.md):
 *   token_kind  "user_access" on every end-user login. Post Login never runs for machine
 *               (client-credentials) tokens, so those can never carry it.
 *   admission   "google" for the Google connection, "verified_email" for an email/password account
 *               whose address Auth0 has verified. Anything else gets no admission claim, and the
 *               backend answers 403, so an unverified email account cannot score until verified.
 *
 * NAMESPACE must equal the backend's AUTH0_CLAIM_NAMESPACE exactly, trailing slash included.
 */
const NAMESPACE = "https://anhydra.work/claims/";

exports.onExecutePostLogin = async (event, api) => {
  api.accessToken.setCustomClaim(NAMESPACE + "token_kind", "user_access");

  let admission = null;
  if (event.connection.strategy === "google-oauth2") {
    admission = "google";
  } else if (event.connection.strategy === "auth0" && event.user.email_verified === true) {
    admission = "verified_email";
  }
  if (admission) {
    api.accessToken.setCustomClaim(NAMESPACE + "admission", admission);
  }
};
