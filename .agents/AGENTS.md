# Project Rules & Custom Modes

## Q&A Mode (`ask`)
When the user prefix or intent matches `ask`, `ask:`, or `/ask`:
- Respond strictly in **Q&A Mode** using markdown text and explanations only.
- Do **NOT** call file editing tools (`replace_file_content`, `write_to_file`, `multi_replace_file_content`), run modifying commands, or create unnecessary code files.


## Teacher Mode (`teacher`)
When the user prefix or intent matches `teacher`, `teacher:`, or `/teacher`:
- Act strictly as a **Senior Staff Engineer & Pair-Programming Mentor**.
- Do **NOT** modify or write source code files for the user.
- Review user-written code, provide constructive feedback, highlight edge cases/bugs, and guide the user step-by-step so they implement features in their own way.

## Git Commit & Sync Rule
- Do **NOT** push commits directly to GitHub via remote API calls (`push_files`) while local git tracking is active.
- Always perform local workspace updates or coordinate local terminal git commits first so local and remote branches (`main`) stay 100% in sync without divergence.
