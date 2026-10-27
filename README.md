# Display Switch (Decky plugin)

Switch **Game Mode** between a laptop's built-in screen and a TV, projector or monitor, from the
Quick Access menu, with a controller.

Built for **hybrid-GPU laptops** running Bazzite, ChimeraOS or other gamescope-session-plus
systems, where the HDMI port is wired to the dedicated GPU and the built-in screen to the
integrated one. On those machines Game Mode doesn't follow the cable on its own.

This plugin is a front end for
[gamescope-display-switch](https://github.com/Albino-blueWhale/gamescope-display-switch), which it
bundles, so nothing else needs installing.

## What's in the panel

- **Now using:** which screen Game Mode is on, read from the running Game Mode.
- **External:** the display that's plugged in, on any port. Updates every few seconds, so you
  see it the moment you plug in a cable.
- **Switch button:** restarts Game Mode on the other screen, after asking (a running game
  closes). Greyed out when nothing is plugged in, so you can't switch to a black screen.
- **Boot safety net:** if the saved display isn't connected when Game Mode starts (you left it
  set to a friend's TV), Game Mode starts on the built-in screen instead. It runs as a user
  service before each Game Mode start, so it needs no root.

**Which GPU do games use on the built-in screen?** Game Mode itself runs on the integrated GPU
there, but games can still render on the dedicated one. On Bazzite, **cardwire**'s Hybrid mode
(the default) already sends every game to the dedicated GPU, so there's nothing to set up. See
the [CLI's README](https://github.com/Albino-blueWhale/gamescope-display-switch#known-limits)
for other systems.

The plugin runs as your user, not as root. Switching restarts just the Game Mode session, and
SDDM (with `Relogin=true`, as on Bazzite) logs straight back in.

## Install

Until it's in the Decky store:

1. In Game Mode: Quick Access menu → Decky (plug icon) → gear icon → **General** → turn on
   **Developer mode**.
2. Open the new **Developer** tab and use **Install Plugin from URL** with:
   ```
   https://github.com/Albino-blueWhale/decky-display-switch/releases/latest/download/decky-display-switch.zip
   ```
   Or download that zip and use **Install Plugin from ZIP File**.

Already using the command-line version with its `install.sh`? That's fine. The plugin sees its
boot service and leaves the boot safety net to it.

## Building

```bash
pnpm install
pnpm build
```

Then package `plugin.json`, `package.json`, `main.py`, `LICENSE`, `dist/index.js` and
`defaults/bin/` (as `bin/`) into a folder named `decky-display-switch`.

The bundled `defaults/bin/gamescope-display-switch` is a copy of the CLI. Update it from the
CLI repo's `bin/` when the CLI changes.

## Tested on

| Laptop | GPUs | Decky | Result |
|---|---|---|---|
| Acer Predator PH317-54 | Intel UHD + Nvidia RTX 2060 | v3.3.1 | ✅ Switch both ways, status, boot check |

Reports from other machines are very welcome: open an issue with your laptop model and the
output of `bin/gamescope-display-switch --status` from the plugin folder
(`~/homebrew/plugins/decky-display-switch`).

## License

MIT. Parts that come from Decky's plugin template keep its BSD 3-Clause license; both are in
[LICENSE](LICENSE).
