# 🛡️ Clash Intel by VICTORIOUS

An open-source, high-performance analytics and structural auditing framework for Clash of Clans players and clan leaders. Built with Python, Asynchronous I/O, and Streamlit.

---

## 🔒 The Transparency Guarantee (Why You Can Trust This Tool)

In the gaming community, hyper-vigilance against phishing and token-stealing scams is fully justified. We built Clash Intel to be 100% open-source, auditable, and secure by design.

* **Zero Middlemen & No Harvesting:** This tool does not have a backend database, user tracking, or credential logging. All network requests go directly from your running instance to Supercell's official API via the standard RoyaleAPI CORS proxy layer.
* **Bring Your Own Key (BYOK):** When running this tool locally, you authenticate using your own personal Supercell API Token generated directly from developer.clashofclans.com. We never see, touch, or transmit your credentials.
* **Open Architecture:** Every line of code—from the asynchronous scraper to the UI rendering—is public. You are encouraged to inspect the repository files to verify exactly where your network traffic goes.

---

## 🚀 Features

* **🕵️ Player Inspector:** Deep-dive into account metrics, true hero power totals, equipment upgrade states, and offensive army link extraction.
* **🏰 Clan & Raid Auditor:** Instantly generate color-coded Capital Raid Slacker Reports, track missed attacks, inspect war logs, and audit clan member activity.
* **🎯 Ping-A-Donor:** Smart inventory scanning that calculates active clan level donation boosts (+1 or +2 levels) to find exactly which clan members can donate the maxed super troops or spells you need.

---

## 💻 60-Second Local Setup

Want to run this entirely on your own machine? You only need Python and Git.

### 1. Clone the Repository
```bash
git clone [https://github.com/SirJayant/Player-Inspector.git](https://github.com/SirJayant/Player-Inspector.git)
cd Player-Inspector

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

### 3. Launch the App

```bash
streamlit run app.py

```

### 4. Authenticate

Open the local URL generated in your terminal (usually http://localhost:8501). In the sidebar, paste your developer token from Supercell. That's it—you are running a private, isolated analytics node.

---

## 🔑 For Developers: Using Streamlit Secrets (st.secrets)

If you are hosting this framework on a cloud provider (like Streamlit Community Cloud) for your clan and want to provide a global token so your members don't have to input their own keys:

1. Create a `.streamlit` directory in your root folder: `mkdir -p .streamlit`
2. Create a `secrets.toml` file inside it: `touch .streamlit/secrets.toml`
3. Add your Supercell API key to the file:
```toml
COC_TOKEN = "your_actual_jwt_token_here"

```
