# GitHub Profile Setup

Upload the complete contents of this folder to the profile repository:

`MUHAMMADUSAMA64874/MUHAMMADUSAMA64874`

Required structure:

```text
README.md
assets/
  github-snake.svg
  github-snake-dark.svg
.github/
  workflows/
    snake.yml
```

## Activate the contribution snake

1. Open the profile repository on GitHub.
2. Open **Settings → Actions → General**.
3. Under **Workflow permissions**, select **Read and write permissions** and save.
4. Open the **Actions** tab.
5. Select **Generate Contribution Snake**.
6. Click **Run workflow**.

The included placeholder prevents a broken image or large empty space before the first workflow run. After the workflow succeeds, it replaces the placeholder with the live contribution snake and refreshes it daily.

## What was fixed

- Removed the unreliable remote trophy image that was displaying as a broken image.
- Replaced trophies with compact GitHub achievement cards using the achievements visible on the profile.
- Replaced the missing output-branch snake URL with repository-local SVG assets.
- Added a safe placeholder so the snake section never appears blank.
- Reduced large analytics spacing by removing the oversized summary card and using equal-height cards.
- Added a featured automation project section.
