---
name: seven-android-release-gates
description: Validate Android packaging, storage access, lifecycle and release evidence.
---
# Seven Android Release Gates
1. Inspect the actual Android project, build configuration, target SDK, permissions and storage access framework (SAF) flows.
2. Test supported API levels on a real emulator/device when available; never infer emulator success from browser tests.
3. Verify create/save/export/import, force-stop/reopen, rotation/resume, keyboard and back navigation.
4. Capture screenshots and logs with build SHA, device/API, command, and result.
5. Validate APK existence, package identity, signature and checksum only after build gates pass.
6. Clearly mark unrun tests and environment blockers; do not call a build release-ready based on compile success alone.
