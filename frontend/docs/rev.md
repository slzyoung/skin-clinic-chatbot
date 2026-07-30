# Frontend Revisions for Backend

This document tracks frontend adjustments and new features that require backend support or awareness.

## 2026-07-28 - Time Limit Per Session
- Added a new configuration component for "Time Limit Per Session" in the Dashboard Configuration page.
- **Key Used:** `TIME_LIMIT_PER_SESSION` (String representing number of minutes, e.g. "5").
- Backend should ensure this configuration key is supported and handle it appropriately in the chat session logic (ending sessions after the specified time).

## 2026-07-30 - AI Prompt File Attachments
- Added a new configuration component for "AI Prompt File Attachments" in the Dashboard Configuration page.
- **Key Used:** `AI_PROMPT_FILE_ATTACHMENTS` (String representing boolean value, "true" or "false").
- Backend should ensure this configuration key is supported and handle it appropriately when receiving chat session prompts (allowing or rejecting file uploads based on this toggle).
