# Code Review Request

## Changes:
1.  **CI/CD**: Updated `.github/workflows/docs.yml` to use `davidanson/markdownlint-cli2-action@v19` and added a `.markdownlint-cli2.yaml` configuration.
2.  **Documentation**:
    *   Created `docs/de/usage/outlook-macros.md` describing all Outlook VBA macros.
    *   Updated `docs/de/usage/email-workflow.md`:
        *   Linked to the new macros page.
        *   Clarified Phase 3 (Analysis) scope.
        *   Added a detailed Phase 6 explaining technical execution of all 6 actions.
    *   Updated `mkdocs.yml` navigation.

## Verification:
*   Documentation builds successfully with `mkdocs build`.
*   Verified file contents and links manually.
