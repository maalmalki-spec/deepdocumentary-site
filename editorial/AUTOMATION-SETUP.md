# Documentary pipeline setup

This workflow runs daily at 05:15 UTC and can be triggered manually. It generates **up to two bilingual draft JSON files per run** on a new pull-request branch. It **never publishes** an article automatically.

## Required setup
1. In GitHub repository Settings → Secrets and variables → Actions, create repository secret `OPENAI_API_KEY` (requires a paid API account; ChatGPT subscription does not include API credits).
2. Ensure Actions are enabled and workflow permissions permit pull requests. GitHub may require Settings → Actions → General → Allow GitHub Actions to create and approve pull requests.
3. Optional: repository variable `OPENAI_MODEL` (default `gpt-4.1-mini`).
4. Run the workflow manually once and inspect the Actions logs and resulting pull request. The scheduler is only dependable after the workflow is enabled on the default branch.
5. An editor must verify all claims, original sources, copyright/licensing, image URLs, Arabic/English quality, and article layout before manually publishing to `articles/` and linking from the home page.

## Costs and limitations
- OpenAI API calls incur usage-based charges. Set API project spend limits; workflow generates at most two draft calls per run, with a 20-minute job timeout.
- GitHub Actions quotas may apply.
- Model output is **not fact-checked** or web-researched. No images are downloaded, and no content is automatically approved.
- Workflow skips existing `articles/<slug>.html` and `editorial/generated/<slug>.json` files. Existing Apollo 11 HTML draft is not automatically detected because it lives at `editorial/drafts/`; editorial review should avoid duplicates.
- Drafts are stored in pull-request branches, not automatically merged.
