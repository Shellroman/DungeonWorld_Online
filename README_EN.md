# Dungeon World Online v1.0.0

This is the **first public release** of an unofficial online play companion for Dungeon World 1st Edition. One GM opens a campaign with the Windows launcher, and players join from a browser.

- App version: **1.0.0**
- Database schema: **20**
- DWPack format: **1**
- Windows: **x64**
- BUILD_ID: **bbf02338d0f83dc9**


## Highlights

- **English / Korean** launcher, game UI, settings, help, and built-in classes, races, moves, spells, and monsters. English is the default language on a fresh install.
- **Per-browser language choice**, so people in the same campaign can use different interface languages. User-authored content remains in its original language.
- **Active-campaign enforcement**: a saved campaign cannot be joined, resumed, or accessed through the player API unless the GM has actually opened it.
- **Player capacity**: when creating a campaign, the GM chooses 2–8 player seats (GM excluded). The default is 4, and the server enforces the limit.
- **Character tools** for ability scores, HP, armor, damage, bonds, moves, spells, hold, notes, advancement, and the source of added features.
- **Move Effects / Cross-Class Access** with explanatory GM controls and player-facing previews for extra spells, lowered spell requirements, moves from other classes, and access to another class's spellcasting.
- **Spell safeguards** that keep special unclassified spells out of ordinary spell selection unless a rule explicitly grants one.
- **Text-first inventory** with structured values only where useful. Ammo is tracked as a separate inventory item rather than as a field on a weapon.
- **GM tools** for NPCs, monsters, bestiary reveals, quick creation, sessions/logs, player management, rules, DWPacks, and system settings.
- **Optional expansion classes** supplied as separate example packs instead of being inserted into every campaign.
- **File-backed audio** for BGM and sound effects. External video-link audio is not included.
- **LAN, invite-code, and reconnect support** for local and returning players.
- **DWPack** import/export for reusable campaign content.
- **Data-driven spellcasting profiles**: spell learning/preparation rules are stored as class data instead of being tied to hard-coded Wizard/Cleric names. Cross-class access can inherit another class's spellcasting profile, including nested access obtained through moves.
- **Rule-calculation fixes**: Load uses the Strength modifier, coin weight is consistent between client/server summaries, damage cannot fall below 0, and monster best-of damage rolls/presets now resolve correctly.
- **Bestiary reveal controls** with complete English labels and a one-click **Reveal All** action for the GM.
- **English bestiary/cache integrity**: all 154 built-in monsters carry explicit English display metadata, and localization catalogs are build-versioned so stale browser cache cannot mix Korean defaults into a newer build.
- **Custom-content translation safety**: bundled-content English translation is applied only to records with known built-in provenance; user-authored classes, races, moves, spells, monsters, and expansions keep exactly the text that was authored.

## Local and remote play

On the same home/venue network, players can use **Find on LAN** or a suitable invite code.

For players in different homes or on different networks, Dungeon World Online does not provide a central relay server. Use a virtual-LAN/VPN tool such as **Tailscale, ZeroTier, or Radmin VPN** so the GM and players can reach one another. The GM runs the host server, then shares the invite code that matches the VPN route or the GM's VPN address plus the campaign code. LAN auto-discovery may not cross every VPN, so direct address entry is the reliable fallback.

The GM's PC and Dungeon World Online host server must remain running while remote players are connected. Windows Firewall or the VPN's own network rules must also allow the connection.

## Data compatibility

Database schema is **20**. Sequential migration paths remain available for campaigns created with development schemas 13 through 19. Ammo previously stored directly on weapons is migrated into separate Ammo inventory entries while preserving current/maximum values. Schema 20 adds campaign player capacity; existing campaigns are migrated to a safe 4–8 seat limit based on their enabled player count.

Back up the host data directory before upgrading a long-running campaign.

## Bundled packs

- `DungeonWorld_1E_Core.dwpack` — Dungeon World 1E Korean core data
- `DungeonWorld_1E_Core_EN.dwpack` — Dungeon World 1E English core data
- `UnlimitedDungeons_DistantShore_Expansions.dwpack` — optional expansion-class examples, Korean
- `UnlimitedDungeons_DistantShore_Expansions_EN.dwpack` — optional expansion-class examples, English
- `DungeonWorld_DWPack_Reference.zip` — reference material for compatible packs

## Licenses and attribution

Dungeon World Online is an **unofficial fan-made tool** and is not an official Dungeon World product.

- Original project **software code**: MIT License — Copyright (c) 2026 ShellRoman
- Project-authored non-software explanatory material: CC BY 3.0 unless a file states otherwise
- Public Dungeon World game text: CC BY 3.0 — Sage LaTorra and Adam Koebel
- Korean public edition: CC BY 3.0 — Korean translation credited to Kim Seong-il / Choyeomyeong Publishing
- SRD 5.1 upstream material identified by Dungeon World's official license: CC BY 4.0 — Wizards of the Coast LLC
- Unlimited Dungeons / Distant Shore adapted examples: CC BY-SA 4.0 plus the applicable source attributions

See:

- `LICENSE` — MIT License for project software
- `THIRD_PARTY_NOTICES.md` — consolidated third-party and upstream notices
- `LICENSE_ATTRIBUTION_KO.md` — Korean attribution summary
- `AI_USE_NOTICE.md` — generative-AI development disclosure

## AI use disclosure

Generative AI was used as an assistive tool for code drafting and review, debugging, tests, translation/editing, and documentation. Final product decisions, integration, and review were performed by **ShellRoman**. The released application does not include an integration that sends user data to an external generative-AI service.

## Created by

Dungeon World Online was created by **ShellRoman**.
