# Dungeon World Online v1.0.0 · Public Release

This is the **first public release** of Dungeon World Online. Development-only experimental/internal release branding has been removed, and the public version line begins at **v1.0.0**.

## Release highlights

- English-default Korean / English UI and built-in game data
- Windows x64 launcher with browser-based play screens
- Server-side enforcement that only the currently opened campaign can be joined
- Campaign player capacity selectable from 2–8 seats, GM excluded, with a default of 4 and server-side enforcement
- Character, move, spell, race-feature, inventory, NPC, monster, session, and log tools
- Explainable Move Effect / Cross-Class Access editing and player choices
- Ordinary acquisition paths exclude unclassified special spells
- Separate Ammo inventory resources with migration from older weapon fields
- Local-file BGM and sound effects
- DWPack import/export plus Korean and English core packs
- Translation coverage for dynamic UI, tooltips, summaries, and help text
- Stable CSS-based information icons instead of font-dependent circled glyphs
- Spacing and readability improvements across forms, dialogs, settings, and sound controls

## Final English-mode localization fixes

- Fixed built-in class, race, move, spell, and monster-folder names remaining in Korean inside dynamically composed English sentences.
- Re-audited first-character destiny selection, deletion confirmations, multiclass prompts, monster tags, XP labels, spell-level validation, tooltips, and translated server errors.
- Dynamic `title`, `placeholder`, `aria-label`, and `data-tip` attribute changes are now localized in English mode as well.
- Fixed native confirmation dialogs that could show literal `\n` instead of an actual line break.
- User-authored Korean proper names remain unchanged rather than being machine-translated.

## Final rules and gameplay fixes

- Corrected maximum Load to use the Strength modifier rather than the raw Strength score. Coin weight is now included consistently in server-side inventory summaries.
- Damage rolls are floored at 0 without changing ordinary non-damage roll totals.
- Fixed monster **best-of damage** so offensive skill actually rolls twice and keeps the higher result, and reset stale modifier/roll-mode state when using dice presets.
- Permanent magical armor quick creation now applies the `magical` tag together with Armor 4.
- Reworked class spellcasting into data-driven profiles: how spells are known, prepared, limited, auto-known at level 0, learned at start/level-up, and labeled is stored as class data rather than keyed to class names.
- Cross-class spellcasting access now inherits the source class profile, including nested cases such as acquiring a move that itself grants access to another class.
- Fixed Bestiary Reveal English labels and added a GM **Reveal All** action that confirms once and saves all reveal fields immediately.

## Final integrity audit and core-data completion

- Expanded the bundled bestiary to **154 monsters**, including 14 Planar Powers, with matching Korean/English Core DWPacks.
- Only monster folders are draggable for ordering. Monsters themselves are moved explicitly through the monster editor's Area / Folder field.
- Base advanced moves, multiclass tiers, expansion Legendary Moves, and expansion Class Moves now share one cumulative advanced-move point pool; unused points never expire.
- The `players can add multiclass moves` campaign rule is now enforced by both the UI and server.
- Ability-growth points are server-validated, and configured ability-score minimum/maximum values now act as real character-editing rules. Rule changes that would invalidate existing characters are rejected.
- Class/character damage dice now match the actual roller (`D4/D6/D8/D10/D12`), preventing unsupported saved dice from creating a non-working roll action.
- `Play next when finished` now stops at the end of the BGM list; only `Repeat playlist` wraps back to the first track.
- Expansion-class limits support 0–99, cannot be bypassed by re-offering a previously declined grant, and cannot be lowered below active/pending grants.
- Class/race renames now update dependent cross-class spell/race references, while edited class moves prune stale hidden selections that would otherwise keep consuming points.
- Fixed English-mode rule saves accidentally persisting the translated default currency label `Coin` in place of the canonical Korean default value.


## Final rules-save / English bestiary hotfix

- Fixed the GM Rules save path throwing `r is not defined`; the save handler now binds the current campaign-rules object before reading unchanged values.
- Versioned the English UI/content catalogs with the current BUILD_ID and load them with `no-store`, preventing an older browser-cached translation catalog from being mixed with newer JavaScript/data.
- All **154 bundled monsters** now carry explicit English display metadata. The English monster-setting and monster names were rechecked against the English Dungeon World SRD, including `Cavern Dwellers`, `The Lower Depths`, `Folk of the Realm`, `Planar Powers`, `Denizens of the Swamp`, and `The Dark Woods`.
- Corrected source-aligned names such as `Guardsman`, `Fool`, and `Hunter`, and rechecked the Goblin Orkaster entry and the English Core DWPack.
- English monster UI basics such as `Create Monster`, field labels, roll-mode help, tags, instinct, special qualities, moves, descriptions, and bestiary controls now load against the same build-specific catalogs.

## Distribution cleanup

- Removes development-only internal branding and standardizes public release naming.
- Identifies **ShellRoman** as the copyright holder for project software under the MIT License.
- Consolidates Dungeon World, Korean public-edition, SRD 5.1, and Unlimited Dungeons / Distant Shore notices in `THIRD_PARTY_NOTICES.md`.
- Adds Korean translator attribution to the Korean core DWPack manifest.
- Adds `AI_USE_NOTICE.md` to disclose generative-AI-assisted development.
- Updates the in-app license/source help to match the bundled notices.

## Compatibility

- App version: **1.0.0**
- Database schema: **20**
- DWPack format: **1**
- BUILD_ID: **`bbf02338d0f83dc9`**

Sequential migrations remain available for campaigns created with development schemas 13 through 19. Schema 20 adds campaign player capacity and safely migrates existing campaigns based on their enabled player count.

- The public launcher uses the `DungeonWorldOnline` user-data path, with one-time migration or safe fallback for older development-build data.

## Final UI polish

- Fine-tuned the inner insets and borders of the d4/d6/d8/d10/d12 dice so their outlines appear more visually consistent.
