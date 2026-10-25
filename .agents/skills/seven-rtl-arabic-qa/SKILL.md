---
name: seven-rtl-arabic-qa
description: Validate Arabic localization, RTL layout and bidirectional text.
---
# Seven RTL Arabic QA
1. Prefer logical CSS properties (margin-inline, padding-inline, inset-inline-start) and direction-aware layout.
2. Set direction at the correct component boundary; do not reverse every icon or numeric value blindly.
3. Test Arabic-only, English-only, mixed Arabic/Latin, numbers, punctuation, long names and user-generated text.
4. Check dialogs, menus, model/provider labels, forms, navigation, scroll position, and text alignment.
5. Verify RTL at narrow phone widths and with keyboard/focus; avoid clipped text and overlapping controls.
6. Preserve stored content exactly; presentation direction must not mutate saved strings.
