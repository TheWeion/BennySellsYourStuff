<div align="center">

# Benny Sells Your Stuff (BSYS)

### An ESP-less addon mod for Sweet6Shooter's [(Benny Humbles You) and Steals Your Stuff](https://www.nexusmods.com/newvegas/mods/71112) that allows Benny to begin selling all that loot he took from an unlucky Courier.

### Talk about having a 18-carat run of bad luck!

</div>

___

With BHYSYS's `bStolenGear=1`, everything you owned ends up in a wall safe in the
Tops Presidential Suite. This mod makes the time you take to get it back matter.

From the moment you wake up at Doc Mitchell's, Benny is out there **fencing your
items and spending your caps**. Beeline to New Vegas and you'll recover almost
everything. Spend months collecting snowglobes and you'll come back to a much
lighter safe.

## How it works

**The clock** starts the first time BHYSYS populates the safe (i.e. the humbling)
and runs on the in-game calendar (immune to the vanilla `GameDaysPassed` freeze
bug). Benny gets a configurable grace period (default 1 day) to get settled
before the selling starts.

**The fence.** Benny's *permanent* Intelligence, Charisma and Luck are read live
from the actor. Nothing is hardcoded, so an overhaul that changes Benny changes
the simulation. Your Luck pushes back: every point you have over him lowers his
effective stats, and vice versa, weighted by `fLuckModWeight`.

- **Charisma** — how often he finds a buyer (sale attempts per day)
- **Intelligence** — whether he recognizes your most valuable item or grabs at
  random. This ramps in over his first week with the stash — it takes him a
  while to appraise it all, so a fast Courier rarely loses their best piece.
- **Luck** — every sale is a contested d20 + Luck roll (integer dice, ties go
  to you). Tie or beat him and the buyer walks; the item survives that attempt.
  The die size is tunable (`iLuckRollDie`) — smaller dice make the Luck gap
  count for more.

For the record: vanilla Benny is INT 3 / CHA 3 / LCK 5. He's a schemer, not a
merchant — with decent player Luck he's a genuinely mediocre fence. Checkered
suit tax.

**Escalation.** Both the sale rate and his caps spending scale up the longer you
take (`fEscalationPerWeek`, default +25% per week). When Benny wins a sale, the
**lot size** scales with how hard he won the luck roll: a narrow win moves one
unit, a crushing win against an unlucky Courier moves several. Cheap items
(< 25 caps) move in bigger lots, boosted by his Charisma. Caps in the safe
(BHYSYS `bCapRemoval=0`) drain daily, scaled by your Luck — but he'll never
touch the 130 caps he left with his own note. He's got style. (Don't want him
spending your caps at all? `bSpendCaps=0` in the `[Fencing]` section.)

**Time always counts.** The simulation settles calendar windows, not frames —
Waiting, Sleeping and fast travel are charged in full, at the correct
week-by-week escalation rates, the moment you wake up or arrive.

**It ends** — and the safe is frozen forever — when any of these happen:
1. Benny dies — at the Tops, at Caesar's tent, or on the cross
2. You talk him into the presidential suite meeting (Ring-a-Ding-Ding! stage 20)
3. Benny flees the Tops / ends up Caesar's captive (covers the Black Widow route)
4. Backstop: Benny is physically waiting in the presidential suite

Everything settles *before* you can reach the safe. Entering the suite forces a
final settlement — even if you break in early with a pickpocketed key — so you
never watch items vanish.

**Quest items are never sold.** Neither are the safe key or Benny's note. And
the `[Fencing]` section of the config decides which categories Benny will
touch at all — weapons, armor, power armor, aid, ammo, books, misc, weapon
mods, keys (off by default; even non-quest keys can gate content) and a
catch-all for the rest. Disable a category and those items sit safely in the
safe while he fences the rest.

## The Fencing Network

Benny's buyers are real. With `bPhysicalFencing=1` (the default), every item
he fences lands in an actual merchant's inventory somewhere in the Mojave —
weapons to Mick, energy to the Van Graffs, chems to Dixon, aid to the
Followers. He works the Strip and Freeside first; the longer he runs (and
the unluckier you are), the farther out your gear travels — Gun Runners,
Crimson Caravan, the 188, Novac, Primm, Goodsprings, the Mojave Outpost.
Walk into the right shop and buy it back at the counter, priced live by the
barter menu with your Barter skill and perks.

**Benny's Ledger.** When he dies, his body carries a handwritten ledger:
every sale, dated and priced, with the buyer's name and location — plus a
Luck-scaled cut of the caps he *actually* made fencing your gear
(`fRecoverCapsPctBase` + `fRecoverCapsPctPerLuck`). Buy an item back and its
entry's font will be emboldened out the next time you open the book.

**Vendor churn.** Merchants trade your gear onward every `fMigrateDays`
(default 7). Past `fGoneDays` (default 28) an item leaves the Mojave for
good — unless it's unique-protected (`bProtectUniques`): anything another
mod flags unique (JIP's `ToggleItemUnique`), plus anything at or above
`iUniqueValueFloor` per unit — the heuristic that catches vanilla uniques,
since the game data doesn't mark them. Protected items circulate between
fences forever.

**Tracking it down.** The ledger names each item's *first* buyer only. Once
goods move on, go back to that merchant and browse their wares — closing
the barter menu with your gear conspicuously absent starts the
conversation. After that first talk, simply speaking to the merchant offers
the topic directly, and the shop counter only pipes up again when something
*new* of yours has moved through. Persuade them
(deterministic `[Speech cur/req]` check — half price), intimidate them
(`[Strength]` check — free, but the karma hit lands whether or not it works,
and a failed attempt is locked forever), or just pay up. Prices and Speech
requirements scale with the item's value, your reputation with the fence's
people, and (caps only) your Barter skill; `bShowCheckValues=0` hides the
numbers. Bought intel is written onto the **last page of Benny's Ledger**,
in the Courier's own hand — every tip in one place, separate from Benny's
entries — and each line is a snapshot of what the fence told you: if the
goods move again, you'll need fresh intel. (The ledger only exists once
Benny's spree ends; intel bought before that is remembered and appears the
moment the book is written.)

## Requirements

- [xNVSE](https://github.com/xNVSE/NVSE/releases) 6.4.4+
- [JIP LN NVSE](https://www.nexusmods.com/newvegas/mods/58277) 57.30+
- [JohnnyGuitar NVSE](https://www.nexusmods.com/newvegas/mods/66927) 5.20
- [ShowOff NVSE](https://www.nexusmods.com/newvegas/mods/72541) 1.82+
- [SUP NVSE](https://www.nexusmods.com/newvegas/mods/73160) 8.55+
- [Plugins+ (pplus)](https://www.nexusmods.com/newvegas/mods/93634) 1.76+
- [(Benny Humbles You) and Steals Your Stuff](https://www.nexusmods.com/newvegas/mods/71112)
  with `bStolenGear=1` in `Data\Config\Humbling.ini`

If BHYSYS isn't installed, or `bStolenGear` is 0, the mod notices on every save
load and stays completely inert. It detects BHYSYS by resolving the safe
reference at runtime, so detection survives a renamed ESP.

## Installation

Install via the mod manager, it is best used on a save before the player travels from DC to the Mojave — installing post-humbling works (as long as `bStolenGear=1` at
install time), but the clock only starts at install time (Benny can't
retroactively sell what you didn't let him).

Mid-save **uninstallation** is safe: all state lives in JIP auxiliary variables in the co-save and is simply orphaned. If you later *reinstall* on the same save, the clock resumes where it froze and the gap settles as a catch-up. If you'd rather avoid that, leave `bEnabled=0` instead of uninstalling — disabling is a true pause, with no backlog and no escalation.

**Full** uninstallation is also possible by enabling `bUninstall=1` in the config and loading the save file, then Benny's selling antics will end cleanly as well as remove any AuxVars that were stored in the save.  Then create a hard save, exit and remove the mod. Items Benny already fenced to merchants stay in the world — they're ordinary base-game items in ordinary shop inventories, so nothing dangles.

## Configuration

Everything is tunable in `Data\Config\BennySellsYourStuff\Config.ini` — grace
period, sale rate, escalation, caps drain, luck weighting, smart-pick chance,
lot sizes, and the whole `[FencingNetwork]` (physical fencing, churn cadence,
despawn horizon, unique protection, intel pricing and checks, death payout).
`bDebug=1` logs every sale attempt to the console (target, pick mode, both
luck rolls, sold/saved, the buyer and Benny's take), every settlement with
Benny's effective stats, churn moves and buybacks as they happen, a full
fencing-network table on every load, and — when his spree ends — a ledger
table of everything he sold. See the comments in the INI.

## Translations

Player-facing text lives in `Data\Translations\<locale>.json`. At launch the
mod matches your Windows locale — full tag first (`en-GB.json`), then bare
language (`en.json`), then the `en.json` fallback. To translate, copy
`en.json` to your locale's filename and translate the values.

## Troubleshooting

**Installing or removing *any* Plugins+ kit mod (this one included) can break
the other kit mods in your load order.** You'll see `Failed to resolve
variable` / `Failed to extract parameter` errors from kits that worked fine
before, sometimes with another kit's forms in the decompiled error lines. It
isn't a bug in any of the kits. xNVSE 6.4.4+ keeps a persistent compiled-script
cache (`script_data_cache.bin` in the game root, keyed only by script source
text) that stores form references by numeric ID, while Plugins+ assigns
kit-created forms their IDs by load position. Change the kit set and those IDs
shift out from under the cached bytecode — which the cache can't detect, so the
stale IDs still resolve, just to the wrong forms.

**Fix: delete `script_data_cache.bin` from your game folder whenever you add
or remove a kit mod.** It's safe — the file regenerates on the next launch.
Alternatively, set `bNoScriptRunnerCaching = 1` under `[Release]` in
`Data\NVSE\nvse_config.ini` to disable the persistent cache entirely (not recommended for larger modlists).

## Compatibility

- Works with the TTW version of BHYSYS (the only one there is).
- Anything that edits Benny's stats is automatically respected.
- [Real Time Menus](https://www.nexusmods.com/newvegas/mods/94910) is fully
  supported. BSYS asks the game itself whether the open menu is paused (RTM
  hooks that query with its own live-menu logic), so Benny keeps working in
  exactly the menus you left unpaused (`bPause*=0`) — including inside other
  containers when `bPauseContainers=0`, and even if you edit
  `RealTimeMenus.ini` between launches. The one exception is the safe itself:
  he never touches it while you're looking inside, and that window settles the
  instant you close it. Without RTM, the mod runs purely in GameMode.

## Credits

- **Sweet6Shooter** — for (Benny Humbles You) and Steals Your Stuff
- **Demorome** — for the original Benny Humbles You
- **jazzisparis, xNVSE team, carxt, Demorome, Pistol Payback** — for the
  frameworks that make ESP-less modding possible

## License

GPL-3.0
