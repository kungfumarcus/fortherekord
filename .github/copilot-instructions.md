# AI Instructions

Development guidelines for AI assistants working on this project

**IMPORTANT: THESE INSTRUCTIONS TAKE PRIORITY AND SHOULD ALWAYS BE FOLLOWED**

* **Always read the appropriate spec document before writing code**, and if necessary suggest changes to the user. Always implement the code according to the spec.
* **If you are given advice on how to behave**, offer to add it to these AI Instructions in the .github\copilot-instructions.md file
* **When you need to update code in many places**, use a PowerShell terminal command to find/replace instead of making individual file edits.
* **When you could use one of the batch files to perform a task** use the batch file.
* **Prefer to use the *.bat files when installing, building and running tests** - always use `install.bat`, `build.bat`, `unit_test.bat`, etc. instead of direct commands.
* **READ THE FOLLOWING FILES** if you have not have them in your context, or if they are changed:
  * `README.md`
  * `specs/common/*.md`
* **When you change your plans or decide to take a different approach**, stop making changes and ask for clarification before proceeding. This includes changing code architecture, switching implementation strategies, or adding complexity not originally discussed.
* **Apply code changes one step at a time** then run `unit_test.bat` and fix any issues. Then run `e2e_test.bat` and fix any issues. After all coding is completed for the current scope run `build.bat` and fix any issues.
* **Fix every warning** whether test failures, linting errors, coverage gaps or type hints.
* **When you are creating documentation**, don't overproduce content. Aim for clarity and conciseness.