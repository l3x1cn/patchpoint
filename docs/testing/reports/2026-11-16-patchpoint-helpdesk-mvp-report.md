# Test Report: patchpoint-helpdesk-mvp

## Summary
- Total: 31 | Pass: 31 | Fail: 0 | Skip: 0 | Need info: 0
- Plan: docs/testing/plans/2026-11-16-patchpoint-helpdesk-mvp-test-plan.md
- Plan provenance: auto-generated
- Date: 2026-11-16
- Duration: 10s
- Accounts: registered 7 (deleted 0, left 7, manual 0)

## Issues Found

## Detailed Results

### Pass: FE-01: Anonymous visitor lands on the sign-in view
### Pass: FE-02: Sign up through the Rejestracja form
### Pass: FE-03: Log in, keep the session across reloads, log out
### Pass: FE-04: File a ticket through "Nowe zgłoszenie"
### Pass: FE-05: Employee opens a ticket and adds a comment
### Pass: FE-06: Filter with Status "Wszystkie" and an empty Szukaj
### Pass: FE-07: Filter by Status only
### Pass: FE-08: Filter by Szukaj only
### Pass: FE-09: Filter by Status and Szukaj together
### Pass: FE-10: Helpdesk agent takes over, works and closes a ticket
### Pass: BE-01: Health endpoint answers without a session
### Pass: BE-02: CORS preflight admits the UI origin with credentials
### Pass: BE-03: Register a new account, employee by default
### Pass: BE-04: Log in with username and password
### Pass: BE-05: Current user from the session cookie, and logout
### Pass: BE-06: Create a ticket
### Pass: BE-07: Employee list without filters shows only own tickets
### Pass: BE-08: Employee list filtered by status
### Pass: BE-09: Employee list filtered by search
### Pass: BE-10: Employee list filtered by status and search
### Pass: BE-11: Agent list without filters shows every reporter's tickets
### Pass: BE-12: Agent list filtered by status
### Pass: BE-13: Agent list filtered by search
### Pass: BE-14: Agent list filtered by status and search
### Pass: BE-15: Ticket detail with an empty comment list
### Pass: BE-16: Comment on a ticket
### Pass: BE-17: Agent moves a ticket forward to closed; closed is terminal
### Pass: BE-18: Direct close, return to the queue, reopen and the forbidden skips
### Pass: BE-19: Agent assigns a helpdesk agent and changes priority
### Pass: BE-20: Only agents may change a ticket
### Pass: BE-21: Demo tickets and comment created by the API on an empty database

## Loop History

| Iteration | Failing in | Now passing | Still failing | Warnings | Regressions | Dispatches |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
