# Hibiki no Yoru — Resonance of the Night

A music-promotion workbench presented as a small RPG. Prepare three-edit quests, review a songbook and scorebook, open official publishing services, keep a posting ledger, and save your campaign.

## Two editions
- **Public demo**: fictional songs and illustrative performance numbers. No artist accounts, browser sessions, passwords, artist media or campaign records. Saves separately under `HibikiNoYoruDemo`. Start with every connection unconfirmed.
- **Personal campaign**: your own campaign, kept private. Preloaded with your artist context. Saves under `HibikiNoYoru`.

Saves and updates cannot cross editions.

## Download
Get the Windows ZIP from Releases, extract it, and open `HibikiNoYoru.exe`. Python is not required. Windows may identify this early, unsigned preview as an unrecognized application; the app is not code-signed.

## What works today
- Local RPG profile, quest plans, XP, song/style/result browsing and improvement journal.
- Open official Kashie, Buffer, Metricool, social account, LYRC and 0dB pages to sign in in your own browser. Connection badges record your confirmation, not verified OAuth access.
- Posting ledger, export verification log and backup receipts (local records).
- Export and restore a campaign save; download and install an edition-matched update ZIP. Updates are unsigned; checksums verify file integrity, not publisher authenticity.
- An optional six-second synthetic video test when FFmpeg and FFprobe are installed. No commercial footage or artist song is bundled.

This is a working prototype and guided interface, not an autonomous publishing service or Kashie replacement. It cannot directly sign in, render Kashie videos, schedule posts, fetch live analytics or verify account ownership. No subscription purchase occurs in the app. Browser sign-ins stay in your browser and cannot travel with the EXE.

## Build on Windows
Use Python 3.12 or newer: install requirements-build.txt, run `python -m unittest discover -s tests`, then `python scripts/build.py`. Public builds use only `seed/profile.json`. A personal seed can be supplied with `--profile` using a file outside this repository. Never commit it or upload personal build assets to public releases.

## Updates and next work
Save your campaign before updating. Get the new Windows ZIP from Releases and choose Install update in the app. Keep the old EXE until the new one opens successfully.

Next milestones: approved provider connections, real scheduling receipts and duplicate protection, timestamped metric imports, editable Resolve exports, independent local timing tools, beat/phrase suggestions, and independent footage collections. Observations from other products are recorded in the Observatory and kept separate from guesses.

## Name
"Hibiki no Yoru" (Resonance of the Night) — a Shin Megami Tensei-flavored title for a darker RPG feel.
