/**
 * Auth0 Action. Trigger: Sign Up / Pre User Registration.
 *
 * Stops an email + password account from being created unless the address is on the same
 * approved .edu list the Post Login Action uses. People get a clear message on the sign-up
 * form instead of an account that can never log in. Google sign-ups do not run this trigger.
 *
 * Action secret: ALLOWED_EDU_EMAILS, identical to the Post Login Action's.
 */
function normalise(email) {
  return typeof email === 'string' ? email.trim().toLowerCase() : '';
}

function signupAllowed(event) {
  const email = normalise(event.user && event.user.email);
  const parts = email.split('@');
  if (parts.length !== 2 || parts[0] === '' || !parts[1].endsWith('.edu')) return false;
  const approved = new Set(String((event.secrets && event.secrets.ALLOWED_EDU_EMAILS) || '')
    .split(/[\s,]+/).map(normalise).filter(Boolean));
  return approved.has(email);
}

exports.onExecutePreUserRegistration = async (event, api) => {
  if (!signupAllowed(event)) {
    api.access.deny('not_approved',
      'Email sign-up is limited to approved .edu addresses. Use "Continue with Google", or ask the AnHydra team to add you.');
  }
};

exports.signupAllowed = signupAllowed;
