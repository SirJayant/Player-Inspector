# 🛡️ Clash Intel by VICTORIOUS

Honestly? I built this tool out of pure interest and a massive dose of vibe-coding late at night. I wanted a cleaner, smarter way to look at my clan's stats, track who is slacking on raid weekends, and see who can actually donate max super troops without guessing. 

Because it's a home-brewed tool, I wanted to make it 100% open-source so the community can use it, tweak it, and build on it.

---

## 🔒 The Scam-Free Guarantee (Read the Code Yourself)

Gaming communities are rightfully paranoid about phishing, credential harvesting, and account theft. Since I'm hosting a version of this online, people are bound to wonder if it's a trap. 

Here is exactly why this tool cannot steal your data:

* **No Hidden Databases:** There is no backend server. No database. No user tracking. No logging pipelines. The web traffic goes directly from the page you are looking at to the official Supercell API via the standard RoyaleAPI proxy (which everyone uses to bypass Supercell's fixed IP restriction).
* **Bring Your Own Key (BYOK):** If you run this tool on your own machine, you don't use my credentials. You generate a completely free, private API token from developer.clashofclans.com and paste it locally. I never see it, touch it, or store it.
* **100% Transparent:** The entire repository is right here. If you think something sketchy is happening, open up `clash_intel/client.py` and inspect the network connections yourself.

---

## 🚀 Cool Stuff It Does

* **🕵️ Player Inspector:** Checks deep metrics, total aggregate hero levels, active equipment loadouts, and figures out the exact army combinations a player runs in both casual multiplayer and competitive Legend leagues.
* **🏰 Clan & Raid Auditor:** Instantly builds a color-coded Capital Raid Slacker Report showing exactly who missed attacks and how much gold they left on the table. It also checks your latest war records.
* **🎯 Ping-A-Donor:** Type in the troop or spell you need and the tool auto-scans your clan members' inventories. It automatically factors in your clan level donation boost (+1 or +2 levels) to tell you exactly who can cook a maxed unit for you.

---

## 💻 Run It Privately in 60 Seconds

If you don't want to use the live web link, you can host the whole dashboard locally on your own computer using Python and Git.

### 1. Grab the code
```bash
git clone [https://github.com/SirJayant/Player-Inspector.git](https://github.com/SirJayant/Player-Inspector.git)
cd Player-Inspector

```

### 2. Grab dependencies

```bash
pip install -r requirements.txt

```

### 3. Fire it up

```bash
streamlit run app.py

```

### 4. Throw your key in

Your terminal will give you a local web link (usually http://localhost:8501). Open it, go to the sidebar, paste your Supercell developer token, and you are running your own private dashboard.

---

## 🔑 For Clan Leaders Hosting This for Members

If you want to deploy this app to the cloud (like Streamlit Community Cloud) so your clan members can use it easily without generating their own individual tokens, you can hide your personal key securely in the background:

1. Make a streamlit folder: `mkdir -p .streamlit`
2. Create your local secrets file: `touch .streamlit/secrets.toml`
3. Put your token inside it:
```toml
COC_TOKEN = "your_actual_supercell_token_here"

```



*Note: The `.streamlit/secrets.toml` file is already listed in the `.gitignore` so you won't accidentally leak your token if you push commits back to GitHub.*

```
