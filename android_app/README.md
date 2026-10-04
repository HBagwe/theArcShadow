# ⚡ SplitExpense - Android App & APK Build Guide

This directory contains the complete Android mobile application for **SplitExpense**, built with **Kivy** and ready for packaging into an installable `.apk` file using **Buildozer** and **GitHub Actions**.

---

## 📱 Mobile App Highlights
- **Mobile Dark Mode UI**: Deep `#0F172A` theme optimized for OLED/AMOLED smartphone displays.
- **Smart Allocation Engine**: Full to One, Paid for Others (Exclude Payer), Shared Equally, and Exact amounts.
- **1-Tap WhatsApp Reminders**: Direct `https://wa.me/` deep links with pre-filled debt details and UPI handles.
- **1-Tap UPI Payment Intents**: Direct `upi://pay?pa=...` links that trigger Google Pay, PhonePe, Paytm, or BHIM on Android.
- **Offline SQLite Database**: Automatically saves all expenses, groups, and settlements locally on the phone.

---

## 🚀 How to Get the `.apk` File (Free via GitHub Actions)

Because building an Android APK requires the full Android SDK (~5 GB), NDK, and Linux toolchains, we configured a cloud builder via **GitHub Actions** (`.github/workflows/build-apk.yml`).

### Step 1: Push this project to GitHub
If you haven't initialized Git yet:
```bash
git init
git add .
git commit -m "Add SplitExpense mobile app and APK build workflow"
```
Create a new repository on [GitHub](https://github.com/new) and push your code:
```bash
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
git branch -M main
git push -u origin main
```

### Step 2: Trigger the APK Build
1. Go to your GitHub repository in your browser.
2. Click on the **Actions** tab at the top.
3. Select **"Build SplitExpense Android APK"** from the left sidebar.
4. Click **"Run workflow"** ➔ **Run workflow**.

### Step 3: Download the `.apk` File
1. Once the workflow run completes (typically 8–12 minutes for the initial build), click on the completed run.
2. Under the **Artifacts** section at the bottom of the page, click on **`SplitExpense-Android-APK`**.
3. It will download a zip file containing `splitexpense-1.0.0-arm64-v8a-debug.apk`.

### Step 4: Install on Your Android Phone
1. Transfer the `.apk` to your Android device (via WhatsApp, Google Drive, USB, or email).
2. Tap the `.apk` file to install.
3. If prompted, toggle on *"Allow from this source"* (standard for sideloading `.apk` files outside Google Play).
4. Launch **SplitExpense** and enjoy!

---

## 💻 Optional: Local Build (Linux / Docker)
If you prefer building locally:
```bash
cd android_app
pip install --upgrade buildozer cython
buildozer android debug
```
The resulting `.apk` will be output to `android_app/bin/`.
