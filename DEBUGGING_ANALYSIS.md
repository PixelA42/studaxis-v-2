# Root Cause Analysis & Fixes

## Summary

Analysis and fixes for: (1) identical flashcard generation, (2) upload/resource system, (3) UI action failures.

---

## 1. Flashcard Generator Produces Identical Cards

### Root Causes

1. **Deterministic seed**: `variation_seed = int(time.time() * 1000) % 10000` could collide when requests were close together, and `% 10000` limited entropy.
2. **Weak variation prompt**: The prompt asked to "vary" but did not explicitly instruct the model to avoid repeating previous questions.
3. **Temperature**: 0.9 with a narrow seed range sometimes produced similar outputs for the same topic.

### Fixes Applied

| File | Change |
|------|--------|
| `backend/ai_integration_layer.py` | Use `random.randint(1, 2_147_483_647)` for seed; stronger variation wording; temperature 0.95. |
| `backend/main.py` (`_generate_single_flashcard_via_ollama`) | Same seed strategy and variation instructions. |
| `backend/flashcards_system/generator.py` | Added variation instructions and random seed for consistency. |

---

## 2. Upload / Resource System Not Working

### Root Causes

1. **Silent failures**: Errors were logged only with `print`, making backend issues hard to detect.
2. **No user feedback**: On failure, the UI showed an inline error but no notification tray entry.
3. **Potential flow confusion**: Users drop files → click "Synchronize Library" → upload runs. Flow is correct but errors were easy to miss.

### Fixes Applied

| File | Change |
|------|--------|
| `backend/main.py` (`textbooks_upload`) | Use `logging` with INFO/ERROR levels; clearer error handling and HTTPException messages. |
| `frontend/src/pages/Textbooks.tsx` | Use `useNotification`; push error and success notifications. |
| `frontend/src/components/FlashcardSourceSelector.tsx` | Push notification on textbook upload and generation failures. |

### API Flow (verified)

- Frontend: `uploadTextbook` / `uploadTextbookWithProgress` → POST `/api/textbooks/upload` with `FormData` and `file` key.
- Backend: `UploadFile = File(...)` expects multipart form field `file`.
- Paths: CORS allows localhost:5173; Vite proxy forwards `/api` to port 6782.

---

## 3. General UI Action Failures

### Root Causes

1. **Errors not surfaced**: API errors were caught but not pushed to the notification tray.
2. **Button handlers**: Handlers existed and called APIs correctly; the main problem was missing user feedback on failure.

### Fixes Applied

| File | Change |
|------|--------|
| `FlashcardSourceSelector.tsx` | Add `useNotification` and `push` on all generation/upload failures. |
| `Textbooks.tsx` | Add success and error notifications for uploads. |

---

## Files Modified

- `backend/ai_integration_layer.py` – flashcard variation + random seed
- `backend/main.py` – textbook upload logging, flashcard variation seed
- `backend/flashcards_system/generator.py` – variation instructions + random seed
- `frontend/src/pages/Textbooks.tsx` – notification on upload success/failure
- `frontend/src/components/FlashcardSourceSelector.tsx` – notifications on all generation/upload failures

---

## Testing Recommendations

1. **Flashcards**: Generate for the same topic 2–3 times; expect different cards.
2. **Upload**: Drop PDF/PPTX on Textbooks page → click "Synchronize Library"; expect success or error notification.
3. **Flashcard sources**: Use Textbook, Web Link, File, Paste; on failure, expect an error notification in the tray.
