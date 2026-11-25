# XVOK Quest — early Windows preview

A music promotion workbench presented as a small RPG: prepare three-edit quests, review a songbook and scorebook, open official publishing services, and save your campaign.

## Public demo
The public edition contains fictional songs and illustrative performance numbers. It includes no XVOK account connections, browser sessions, passwords, artist media or campaign records. It saves separately in your Windows user folder under XVOKQuestDemo. The personal edition uses XVOKQuest instead. Saves and updates cannot cross editions.

Download the Windows ZIP from Releases, extract it, and open XVOKQuest.exe. Python is not required. Windows may identify this early, unsigned preview as an unrecognized application; the app is not code-signed.

## What works today
- Local RPG profile, quest plans, XP, song/style/result browsing and improvement journal.
- Open official Kashie, Buffer, Metricool and social account pages to sign in in your own browser. Connection badges record your confirmation, not verified OAuth access.
- Export and restore a campaign save; download and install an edition-matched update ZIP. Updates are unsigned; checksums verify file integrity, not publisher authenticity. Only use the project's official releases.
- An optional six-second synthetic video test when FFmpeg and FFprobe are installed. No commercial footage or artist song is bundled.

This is a working prototype and guided interface, not an autonomous publishing service or Kashie replacement. It cannot directly sign in, render Kashie videos, schedule posts, fetch live analytics or verify account ownership. No subscription purchase occurs in the app. Browser sign-ins stay in your browser and cannot travel with the EXE.

## Build on Windows
Use Python 3.13 or newer: install requirements-build.txt, run python -m unittest discover -s tests, then python scripts/build.py. Public builds use only seed/profile.json. A personal seed can be supplied with --profile using a file outside this repository. Never commit it or upload personal build assets to public releases.

## Updates and next work
Save your campaign before updating. Get the new Windows ZIP from Releases and choose Install update in the app. Keep the old EXE until the new one opens successfully. Improvement journal entries are saved requests, not automatic code changes.

Next milestones: approved provider connections, real scheduling receipts and duplicate protection, timestamped metric imports, editable Resolve exports and independent local timing tools. Observations from other products should be recorded separately from guesses; build independent implementations and use authorized media.
