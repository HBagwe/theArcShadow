[app]

# (str) Title of your application
title = SplitExpense

# (str) Package name
package.name = splitexpense

# (str) Package domain (needed for android/ios packaging)
package.domain = org.bagwe

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db

# (str) Application versioning
version = 1.0.1

# (list) Application requirements
requirements = python3,kivy

# (str) Supported orientation (standard Android portrait)
orientation = portrait

# (bool) Fullscreen disabled so native Android status bar & notch are respected
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK / AAB will support
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then automatically accept the SDK license agreements
android.accept_sdk_license = True

# (list) The Android archs to build for (arm64-v8a covers all modern Android phones)
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Android window display mode
android.window_mode = normal

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug with compiler output)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
