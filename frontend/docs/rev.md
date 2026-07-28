# Frontend Revisions for Backend

This document tracks frontend adjustments and new features that require backend support or awareness.

## 2026-07-28 - Time Limit Per Session
- Added a new configuration component for "Time Limit Per Session" in the Dashboard Configuration page.
- **Key Used:** `TIME_LIMIT_PER_SESSION` (String representing number of minutes, e.g. "5").
- Backend should ensure this configuration key is supported and handle it appropriately in the chat session logic (ending sessions after the specified time).
