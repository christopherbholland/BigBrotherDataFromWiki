# Wiki pages

These files are the source for the repo's GitHub wiki. The wiki is a separate git repo that
the Claude session can't push to, so publish them by hand:

1. Turn on the wiki: **Settings → General → Features → Wikis**.
2. Open the **Wiki** tab and create the first page. Title it `Home` and paste `Home.md`.
3. Add a page titled `Screenshots` and paste `Screenshots.md`.

Images are linked from the repo's `main` branch (`docs/screenshots/`), so they show up once
this work is merged into `main`. If you publish from a different branch, replace `/main/`
in the links.
