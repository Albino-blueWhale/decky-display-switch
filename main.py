import asyncio
import json
import os
import pwd
import subprocess

import decky

# The bundled gamescope-display-switch CLI (copied from defaults/ when the plugin is packaged)
CLI = os.path.join(decky.DECKY_PLUGIN_DIR, "bin", "gamescope-display-switch")

# The boot safety net as a *user* service, so it needs no root: it runs before every Game Mode
# start (graphical-session-pre.target stops when unneeded, so it starts again with each session).
UNIT = "decky-display-switch-bootcheck.service"
# The same check installed system-wide by the CLI's install.sh
CLI_UNIT = "/etc/systemd/system/gamescope-display-switch-bootcheck.service"


def _user():
    return pwd.getpwnam(decky.DECKY_USER)


def _unit_path():
    return os.path.join(decky.DECKY_USER_HOME, ".config", "systemd", "user", UNIT)


def _env():
    user = _user()
    env = dict(os.environ)
    # Decky is a PyInstaller bundle: its library path breaks system programs such as systemctl
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    else:
        env.pop("LD_LIBRARY_PATH", None)
    # The CLI finds Game Mode's settings through HOME / XDG_CONFIG_HOME: point them at the user's own
    for name in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME"):
        env.pop(name, None)
    env["HOME"] = user.pw_dir
    env["USER"] = env["LOGNAME"] = user.pw_name
    env["XDG_RUNTIME_DIR"] = f"/run/user/{user.pw_uid}"
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    return env


def _as_user(cmd):
    # Without the "root" flag Decky already runs this backend as the user; this covers the other case
    if os.getuid() == 0:
        return ["runuser", "-u", decky.DECKY_USER, "--"] + cmd
    return cmd


async def _run(*cmd, timeout=15):
    proc = await asyncio.create_subprocess_exec(
        *_as_user(list(cmd)), env=_env(),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "timed out"
    return proc.returncode, out.decode(errors="replace").strip()


async def _systemctl_user(*args):
    return await _run("systemctl", "--user", *args)


class Plugin:
    async def get_status(self):
        code, out = await _run("bash", CLI, "--json")
        try:
            status = json.loads(out)
        except ValueError:
            decky.logger.error(f"--json failed ({code}): {out}")
            status = {"error": "cli_failed", "detail": out[-300:]}
        status["bootcheck"] = await self.get_bootcheck()
        return status

    async def switch(self):
        """Switch screens. Game Mode restarts, which also reloads this plugin's panel, so the CLI
        runs detached and nothing waits for it."""
        status = await self.get_status()
        if status.get("error") or status.get("next") == "none":
            return {"started": False, "status": status}
        log = open(os.path.join(decky.DECKY_PLUGIN_LOG_DIR, "switch.log"), "a")
        subprocess.Popen(_as_user(["bash", CLI]), env=_env(), stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        decky.logger.info(f"Switching {status.get('current')} -> {status.get('next')}")
        return {"started": True, "status": status}

    async def get_bootcheck(self):
        code, _ = await _systemctl_user("is-enabled", "--quiet", UNIT)
        return {"enabled": code == 0, "installed_by_cli": os.path.exists(CLI_UNIT)}

    async def set_bootcheck(self, enabled: bool):
        if enabled:
            path = _unit_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(f"""[Unit]
Description=Display Switch (Decky plugin): start Game Mode on a screen that is connected
Before=graphical-session-pre.target

[Service]
Type=oneshot
ExecStart=/usr/bin/bash "{CLI}" --boot-check

[Install]
WantedBy=graphical-session-pre.target
""")
            if os.getuid() == 0:
                user = _user()
                for p in (path, os.path.dirname(path)):
                    os.chown(p, user.pw_uid, user.pw_gid)
            await _systemctl_user("daemon-reload")
            code, out = await _systemctl_user("enable", UNIT)
        else:
            code, out = await _systemctl_user("disable", UNIT)
        if code != 0:
            decky.logger.error(f"set_bootcheck({enabled}) failed: {out}")
        return await self.get_bootcheck()

    async def _main(self):
        decky.logger.info(f"Display Switch loaded, CLI {CLI}")

    async def _unload(self):
        pass

    async def _uninstall(self):
        await _systemctl_user("disable", UNIT)
        try:
            os.remove(_unit_path())
        except FileNotFoundError:
            pass
        await _systemctl_user("daemon-reload")
