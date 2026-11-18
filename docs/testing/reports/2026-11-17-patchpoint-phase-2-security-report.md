# Test Report: patchpoint-phase-2-security

## Summary
- Total: 39 | Pass: 39 | Fail: 0 | Skip: 0 | Need info: 0
- Plan: docs/testing/plans/2026-11-17-patchpoint-phase-2-security-test-plan.md
- Plan provenance: auto-generated
- Date: 2026-11-17
- Duration: 14s
- Accounts: registered 9 (deleted 0, left 9, manual 0)

## Issues Found

## Detailed Results

### Pass: FE-01: Sign-up shows the API's validation errors as text and creates an employee
### Pass: FE-02: Sign-in keeps the session cookie away from page scripts; sign-out ends it and resets the view
### Pass: FE-03: A session ended outside the page sends the next action back to sign-in
### Pass: FE-04: Names and ticket data from the API render as plain text
### Pass: FE-05: Agent assigns, changes the status and comments in the detail panel
### Pass: FE-06: Agent sees a refused status change as text and keeps working
### Pass: FE-07: Select lists come from the label maps; field limits and pagination controls
### Pass: FE-08: The Content Security Policy is loaded and enforced
### Pass: FE-09: Failed sign-ins show one message, and the sixth attempt is locked out
### Pass: FE-10: A list longer than one page moves between pages with "Następna" and "Poprzednia"
### Pass: BE-01: Health reports only its status and carries the API security headers
### Pass: BE-02: API documentation is not exposed
### Pass: BE-03: Preflight from the UI origin is allowed with credentials
### Pass: BE-04: Preflight from the UI origin asking for a forbidden header or method is refused
### Pass: BE-05: Preflight from a foreign origin is refused without an allow-origin header
### Pass: BE-06: Foreign-origin preflight asking for a forbidden header is refused
### Pass: BE-07: Simple requests from the UI origin carry the allow-origin and credentials headers
### Pass: BE-08: Simple requests from a foreign origin get no allow-origin header
### Pass: BE-09: Request bodies above 64 KiB are refused before authentication
### Pass: BE-10: Sign-up creates an employee with an Argon2id password hash
### Pass: BE-11: Sign-up refuses a role field and creates no account
### Pass: BE-12: Correct credentials return only the user and a hashed, time-limited session
### Pass: BE-13: A wrong password for an existing account gets the generic 401
### Pass: BE-14: An unknown username gets the identical 401 and is still counted
### Pass: BE-15: Five failures lock the username even for the correct password
### Pass: BE-16: A locked username stays locked for further wrong passwords
### Pass: BE-17: An unknown username is locked exactly like a real one
### Pass: BE-18: A successful login resets the failure count
### Pass: BE-19: Logout ends the session on the server
### Pass: BE-20: Search terms match literally, and neither search nor status widens an employee's scope
### Pass: BE-21: The ticket list pages with limit and offset inside fixed bounds
### Pass: BE-22: An employee reads and comments on an own ticket but cannot change it
### Pass: BE-23: An employee gets 404 for another employee's ticket, exactly as for a missing one
### Pass: BE-24: An agent reads, comments on and updates an own ticket
### Pass: BE-25: An agent updates an employee's ticket, keeping fields it does not send
### Pass: BE-26: A missing ticket id answers 404 to an employee
### Pass: BE-27: A missing ticket id answers 404 to an agent
### Pass: BE-28: Ticket and comment fields enforce their length limits and refuse unknown keys
### Pass: BE-29: Ticket ids outside 1…2⁶³−1 are rejected with 422, never a server error

## Loop History

| Iteration | Failing in | Now passing | Still failing | Warnings | Regressions | Dispatches |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
