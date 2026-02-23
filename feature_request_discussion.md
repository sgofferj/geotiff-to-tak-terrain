# Feature Request Discussion: Interactive PreQuit Hook

**User:** Hey, is it possible for you to have a pre-quit hook which automatically saves relevant project info to GEMINI.md?

**Gemini CLI:** The Gemini CLI actually supports a mechanism called the **`SessionEnd` hook**. This is an external script that the CLI can trigger whenever you exit, clear a session, or logout.

However, there is a catch: because this hook runs as the CLI is shutting down, it operates on a "best effort" basis and doesn't allow for a conversational "back-and-forth" where I can think about our architectural changes and write a nuanced summary to `GEMINI.md`.

### The Best Alternative:
The highest-quality way to do this is to use a **"Wrap up" ritual**:
1. When you're done, just say: **"Wrap up this session"** or **"Update GEMINI.md and quit."**
2. I will then perform a final "sweep" of our entire conversation, identify the new "Golden Rules" (like our 8-worker sweet spot), and update the file before signing off.

**User:** Make a feature request for pre-quit hook which allows user interaction to your repo, please.

**Gemini CLI:** I'll use the `/bug` command to submit your feature request, as it's the established way to log issues and requests for the Gemini CLI.

**Feature Request:**
- **Title:** [Feature Request] Interactive `PreQuit` Hook for Session Wrap-up
- **Description:** Add a new lifecycle hook (e.g., `PreQuit`) that triggers when a user initiates an exit command (like `/quit` or `Ctrl+D`). Unlike the current `SessionEnd` hook, this hook should be **blocking and interactive**, allowing the agent to perform final tasks (like summarizing project context to `GEMINI.md`) and potentially interact with the user before the CLI process actually terminates. This would significantly improve cross-session efficiency by ensuring critical architectural decisions are archived automatically.

**User:** Clarify: have you submitted the request or do I still have to do it?

**Gemini CLI:** I have **not** submitted it yet. Because `/bug` is a special command built into the CLI interface that wraps me, I cannot trigger it myself from the "inside."

To submit the request, you just need to paste the following line into your terminal:

`/bug [Feature Request] Interactive PreQuit hook for automated GEMINI.md updates and session wrap-up.`
