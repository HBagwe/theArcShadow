# 📱 Financial Flow & Wealth Stability Planner - Android Mobile App

This directory contains the production-grade Android mobile application for the **Financial Flow & Wealth Stability Planner**, built with **Kivy** and packaged for automatic compilation into an installable `.apk` file using **Buildozer** and **GitHub Actions**.

---

## ⚡ Mobile Highlights

- **Adaptive Screen Aspect Ratio**:
  - Dynamically adapts across all smartphone display aspect ratios (`16:9`, `18:9`, `19.5:9`, `20:9`, `21:9`) with density-independent scaling (`dp`, `sp`).
  - Native notch & status bar padding so inputs are never clipped behind camera cutouts or dynamic islands.
  - Soft-keyboard handling (`below_target`) prevents the on-screen Android keyboard from obscuring numeric entry boxes.
- **AMOLED Pitch Dark Theme**:
  - High-contrast pure black (`#000000`) & dark obsidian background with glowing neon accents (Electric Cyan, Emerald Green, Neon Rose, Gold).
- **Offline SQLite Database (`financial_flow.db`)**:
  - Automatically saves all entered incomes, multi-loans, credit cards, investments, term insurance, and expenses directly to local SQLite storage on the Android device.
  - Remembers all inputs across app launches so you never have to re-enter data.
- **Multi-Loan Amortization Engine**:
  - Track Primary Home Loans, Top-Ups, Vehicle, and Personal loans with paid % and leftover balances.
- **Credit Card Limit & Utilization Gauges**:
  - Real-time card limits, monthly balances, utilization %, active EMI installment tracking, and debt freedom dates.
- **Retirement & Term Insurance Adequacy**:
  - Track EPF, NPS, ULIP, SIP, FD/RD, plus a dedicated Term Life Insurance assessment comparing your life cover against the standard 10x–15x annual income benchmark.
- **Interactive What-If Optimizer**:
  - Real-time slider simulating how cutting discretionary expenses frees monthly cash flow and accelerates 5-year wealth compounding.

---

## 🚀 How to Get the `.apk` File (Built via GitHub Actions)

Because building an Android APK requires the full Android SDK (~5 GB), NDK, and Linux cross-compilation toolchains, cloud compilation is automated via **GitHub Actions** (`.github/workflows/build-apk.yml`).

### Step 1: Push Code to GitHub
Whenever you push to the repository:
```bash
git add .
git commit -m "Update Financial Flow Mobile App"
git push origin main
```

### Step 2: Cloud APK Compilation
1. Go to your repository on [GitHub](https://github.com/HBagwe/theArcShadow).
2. Click on the **Actions** tab at the top.
3. The workflow **"Build Financial Flow Android APK"** starts running automatically.
4. Compilation takes ~8–12 minutes on GitHub's Ubuntu runner.

### Step 3: Download & Install
1. Once the workflow completes, open the workflow run.
2. Under **Artifacts** at the bottom, click on **`FinancialFlow-Android-APK`**.
3. Transfer the downloaded `.apk` to your Android device (via WhatsApp, Google Drive, or USB).
4. Tap the APK to install on your phone!
