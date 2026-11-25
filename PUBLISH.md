# Publishing Hibiki no Yoru to GitHub

## 1. Create the repository
Go to https://github.com/new and create a repository named `hibiki-no-yoru` under `eddie3333`. Make it public for the demo. (Keep personal seeds and campaign data out — they are gitignored.)

## 2. Push this folder
```
cd C:\Users\eddie\Documents\HibikiNoYoru
git remote set-url origin https://github.com/eddie3333/hibiki-no-yoru.git
git push -u origin main
```
You will be prompted to sign in to GitHub; use a personal access token (Settings -> Developer settings -> Tokens) with `repo` scope. Never store the token in the repo.

## 3. Create a release with the EXE
Tag a version and let the workflow build, or upload manually:
```
git tag v0.3.0
git push origin v0.3.0
```
The GitHub Actions workflow builds the Windows demo and publishes a release. For the personal edition, build locally with `python scripts/build.py --profile seed/profile.personal.json` and upload `dist/personal/*` to a private release or keep it local.

## 4. Update the app in-app
In the app, Inventory -> "Get latest version" opens the release page. Download the ZIP, then "Install downloaded update". Checksums verify file integrity.
