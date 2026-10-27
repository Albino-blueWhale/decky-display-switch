import {
  ButtonItem,
  ConfirmModal,
  Field,
  PanelSection,
  PanelSectionRow,
  ToggleField,
  showModal,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useEffect, useState } from "react";
import { FaTv } from "react-icons/fa";

type Screen = { port: string; card: string; gpu: string };
type BootCheck = { enabled: boolean; installed_by_cli: boolean };
type Status = {
  error?: string;
  detail?: string;
  builtin?: Screen;
  external?: Screen | null;
  connected_externals?: string[];
  current?: "laptop" | "external" | "unknown";
  output?: string | null;
  next?: "laptop" | "external" | "none";
  bootcheck: BootCheck;
};

const getStatus = callable<[], Status>("get_status");
const switchDisplay = callable<[], { started: boolean; status: Status }>("switch");
const setBootcheck = callable<[enabled: boolean], BootCheck>("set_bootcheck");

const REFRESH_MS = 3000; // picks up a display being plugged in while the panel is open

function screenName(status: Status, which: string | undefined) {
  if (which === "laptop") return `Built-in screen (${status.builtin?.port})`;
  if (which === "external") {
    const port = status.output?.split(",")[0] || status.external?.port;
    return `External display${port ? ` (${port})` : ""}`;
  }
  return "Unknown (settings missing)";
}

function confirmSwitch(status: Status) {
  const target = screenName(status, status.next);
  showModal(
    <ConfirmModal
      strTitle="Switch display?"
      strDescription={`Game Mode restarts on: ${target}. A running game will close.`}
      strOKButtonText="Switch"
      onOK={async () => {
        const result = await switchDisplay();
        if (!result.started) {
          toaster.toast({ title: "Display Switch", body: "No external display connected." });
        }
      }}
    />
  );
}

function Content() {
  const [status, setStatus] = useState<Status | undefined>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    const refresh = () => getStatus().then((s) => alive && setStatus(s)).catch(() => {});
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  if (!status) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <Field label="Checking screens…" />
        </PanelSectionRow>
      </PanelSection>
    );
  }

  if (status.error) {
    const text =
      status.error === "no_builtin_screen"
        ? "No built-in screen found. This plugin is for laptops and handhelds."
        : `Couldn't read the screens. ${status.detail ?? ""}`;
    return (
      <PanelSection>
        <PanelSectionRow>
          <Field description={text} />
        </PanelSectionRow>
      </PanelSection>
    );
  }

  const others = (status.connected_externals ?? []).filter((p) => p !== status.external?.port);
  const buttonText =
    status.next === "external"
      ? `Switch to ${status.external?.port}`
      : status.next === "laptop"
        ? "Switch to built-in screen"
        : "Plug in a display to switch";

  return (
    <>
      <PanelSection title="Display">
        <PanelSectionRow>
          <Field label="Now using" description={screenName(status, status.current)} />
        </PanelSectionRow>
        <PanelSectionRow>
          <Field
            label="External"
            description={
              status.external
                ? `${status.external.port} connected${others.length ? ` (also: ${others.join(", ")})` : ""}`
                : "Nothing plugged in"
            }
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" disabled={status.next === "none"} onClick={() => confirmSwitch(status)}>
            {buttonText}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
      <PanelSection title="Boot safety net">
        <PanelSectionRow>
          {status.bootcheck.installed_by_cli ? (
            <Field description="Installed by the command-line version of gamescope-display-switch." />
          ) : (
            <ToggleField
              label="Start on a connected screen"
              description="If the saved display is unplugged, Game Mode starts on the built-in screen instead of a black one."
              checked={status.bootcheck.enabled}
              disabled={busy}
              onChange={async (on) => {
                setBusy(true);
                const bootcheck = await setBootcheck(on);
                setStatus({ ...status, bootcheck });
                setBusy(false);
              }}
            />
          )}
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}

export default definePlugin(() => ({
  name: "Display Switch",
  titleView: <div className={staticClasses.Title}>Display Switch</div>,
  content: <Content />,
  icon: <FaTv />,
}));
