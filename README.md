# our-news-podcast-feed
A RSS feed for an edited version of the Our News Podcast (unofficial)

## GitHub Pages RSS Feed

The RSS feed for this podcast is available at `https://charlieboi0.github.io/our-news-podcast-feed/feed.xml`

## Listening with RSS-friendly podcast apps

- 🍎 Apple Podcasts: [https://support.patreon.com/hc/en-us/articles/115000877506-Add-my-private-RSS-feed-to-the-Apple-Podcast-app](https://support.patreon.com/hc/en-us/articles/115000877506-Add-my-private-RSS-feed-to-the-Apple-Podcast-app#h_01JTQQR50FT62RA5EAKXBHWRBC)
- 📡 Pocket Casts: [https://strongcaster.com/add-podcast](https://strongcaster.com/add-podcast)

## Usage

1. Install Python dependencies:
   ```bash
   pip install -r scripts/requirements.txt
   ```
2. Install `ffmpeg` on your system.
3. Create a `.env` file in `scripts/` with the required API credentials:
   - `MODULATE_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `IA_ACCESS_KEY`
   - `IA_SECRET_KEY`

   In GitHub Actions, set these values as repository secrets with the same names.
4. Run the main processor from the repository root:
   ```bash
   python scripts/main.py
   ```
5. The script downloads the latest source episode, edits the audio, uploads the edited file to archive.org, and updates `feed.xml` with the new episode metadata.

