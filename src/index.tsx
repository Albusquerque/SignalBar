import {
  DropdownItem,
  PanelSection,
  PanelSectionRow,
  SliderField,
  ToggleField,
  staticClasses,
} from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useCallback, useEffect, useRef, useState } from "react";
import { FaSignal } from "react-icons/fa";

import { getArtwork, getStatus, setArtworkSetting, setMode, setSetting, submitArtwork } from "./api";
import { sampleArtwork } from "./artwork";
import { PalettePreview } from "./components/PalettePreview";
import { useSteamState } from "./hooks/useSteamState";
import { performancePreview } from "./performance";
import type { ArtworkPayload, Status } from "./types";

const MODE_OPTIONS = [
  { data: "artwork", label: "Artwork" },
  { data: "performance", label: "Performance" },
  { data: "disabled", label: "Disabled" },
];

const ARTWORK_OPTIONS = [
  { data: "auto", label: "Auto (best row)" },
  { data: "center", label: "Centre" },
  { data: "lower", label: "Lower" },
  { data: "manual", label: "Manual" },
];

const ARTWORK_SOURCE_OPTIONS = [
  { data: "hero", label: "Library Hero (wide artwork)" },
  { data: "header", label: "Library Header" },
  { data: "capsule", label: "Library Capsule (vertical)" },
];

const PERFORMANCE_OPTIONS = [
  { data: "gpu", label: "GPU" },
  { data: "cpu", label: "CPU" },
  { data: "mixed", label: "CPU + GPU" },
];

const PALETTE_OPTIONS = [
  { data: "thermal", label: "Cyan → amber → red" },
  { data: "classic", label: "Green → yellow → red" },
  { data: "icefire", label: "Blue → violet → pink" },
];

const DIRECTION_OPTIONS = [
  { data: "same", label: "Both left → right" },
  { data: "mirrored", label: "Mirrored toward centre" },
];

function Content() {
  const [status, setStatusState] = useState<Status | null>(null);
  const [hero, setHero] = useState<ArtworkPayload | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const manualTimer = useRef<number | null>(null);
  const setStatus = (next: Status) => {
    setStatusState(next);
  };

  useEffect(() => {
    let alive = true;
    void getStatus().then((next) => alive && setStatus(next)).catch(console.warn);
    const timer = window.setInterval(() => {
      void getStatus().then((next) => alive && setStatus(next)).catch(() => undefined);
    }, 1000);
    return () => {
      alive = false;
      window.clearInterval(timer);
      if (manualTimer.current != null) window.clearTimeout(manualTimer.current);
    };
  }, []);

  const loadAndSampleArtwork = useCallback(async (appid: number) => {
    if (appid <= 0) {
      setHero(null);
      return;
    }
    const current = await getStatus();
    setStatus(current);
    const artwork = await getArtwork(appid, current.artwork_source);
    setHero(artwork);
    if (!artwork.found || !artwork.data_uri || !artwork.fingerprint || artwork.cached) {
      setStatus(await getStatus());
      return;
    }
    const mode = current.artwork_mode;
    const manualY = current.artwork_manual_y;
    const result = await sampleArtwork(artwork.data_uri, mode, manualY);
    const next = await submitArtwork(
      appid,
      artwork.fingerprint,
      result.colors,
      result.y,
      artwork.filename ?? "",
      artwork.source ?? current.artwork_source,
    );
    setStatus(next);
  }, []);

  const onGame = useCallback((appid: number) => {
    void loadAndSampleArtwork(appid).catch((error) => console.warn("[SignalBar] artwork sampling failed", error));
  }, [loadAndSampleArtwork]);
  useSteamState(onGame);

  if (!status) {
    return <PanelSection><PanelSectionRow>Loading SignalBar…</PanelSectionRow></PanelSection>;
  }
  if (!status.available) {
    return (
      <PanelSection title="SignalBar">
        <PanelSectionRow>
          <div style={{ fontSize: ".88em", opacity: 0.82 }}>
            No 17-pixel <code>valve-leds</code> light bar was found. SignalBar is idle and has made no hardware changes.
            {status.error ? <div style={{ marginTop: 6 }}>{status.error}</div> : null}
          </div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  const changeArtworkSetting = async (key: string, value: unknown) => {
    const next = await setArtworkSetting(status.game.appid, key, value);
    setStatus(next);
    if (next.game.appid > 0) await loadAndSampleArtwork(next.game.appid);
  };
  const changeManualPosition = (value: number) => {
    setStatus({ ...status, artwork_manual_y: value });
    if (manualTimer.current != null) window.clearTimeout(manualTimer.current);
    manualTimer.current = window.setTimeout(() => {
      manualTimer.current = null;
      void changeArtworkSetting("manual_y", value);
    }, 250);
  };
  const artColors = status.artwork.colors;
  const performanceColors = performancePreview(status);

  return (
    <>
      <PanelSection title="Status">
        <PanelSectionRow>
          <div style={{ width: "100%", fontSize: ".88em", lineHeight: 1.45 }}>
            <div><b>{status.active ? "Active" : "Suspended"}</b> · owner: {status.owner}</div>
            <div>Provider: {status.provider}</div>
            {status.game.appid > 0 || status.game.title ? (
              <div>{status.game.title || "Running game"} · AppID {status.game.appid || "unknown"}</div>
            ) : <div>No game running</div>}
            {status.suspension_reason ? <div style={{ opacity: 0.72 }}>{status.suspension_reason}</div> : null}
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label="Show debug details"
            checked={showDebug}
            onChange={setShowDebug}
          />
        </PanelSectionRow>
        {showDebug ? (
          <>
            <PanelSectionRow>
              <div style={{ width: "100%", fontSize: ".76em", opacity: 0.78, overflowWrap: "anywhere" }}>
                <div>LED path: {status.debug.led_path}</div>
                <div>Last write: {status.debug.last_write ? `${status.debug.last_write.toFixed(2)} monotonic` : "never"}</div>
                <div>Writes: {status.debug.writes}</div>
                <div>Last external: {status.debug.last_external ? status.debug.last_external.toFixed(2) : "never"}</div>
                <div>Cooldown: {status.debug.cooldown_remaining.toFixed(1)}s</div>
              </div>
            </PanelSectionRow>
            <PanelSectionRow>
              <ToggleField
                label="Reverse physical LED order"
                description="Enabled for the official Steam Machine orientation. Previews stay left-to-right."
                checked={status.reverse_led_order}
                onChange={async (value) => setStatus(await setSetting("reverse_led_order", value))}
              />
            </PanelSectionRow>
          </>
        ) : null}
      </PanelSection>

      <PanelSection title="Mode">
        <PanelSectionRow>
          <DropdownItem
            label="Display"
            rgOptions={MODE_OPTIONS}
            selectedOption={status.mode}
            onChange={async (option) => setStatus(await setMode(String(option.data)))}
          />
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Artwork">
        <PanelSectionRow>
          <DropdownItem
            label="Steam image"
            rgOptions={ARTWORK_SOURCE_OPTIONS}
            selectedOption={status.artwork_source}
            onChange={(option) => void changeArtworkSetting("source", String(option.data))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <DropdownItem
            label="Sample row"
            rgOptions={ARTWORK_OPTIONS}
            selectedOption={status.artwork_mode}
            onChange={(option) => void changeArtworkSetting("mode", String(option.data))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ fontSize: ".78em", opacity: 0.72 }}>
            {status.game.appid > 0
              ? status.artwork_custom
                ? `Saved for ${status.game.title || `AppID ${status.game.appid}`}`
                : "Using the default; your first change will be saved for this game."
              : "No game running: changes update the default for new games."}
          </div>
        </PanelSectionRow>
        {status.artwork_mode === "manual" ? (
          <PanelSectionRow>
            <SliderField
              label="Vertical position"
              value={Math.round(status.artwork_manual_y * 100)}
              min={15}
              max={90}
              step={1}
              showValue
              valueSuffix="%"
              onChange={(value) => changeManualPosition(value / 100)}
            />
          </PanelSectionRow>
        ) : null}
        {hero?.found && hero.data_uri ? (
          <PanelSectionRow>
            <img src={hero.data_uri} style={{ width: "100%", maxHeight: 92, objectFit: "cover", borderRadius: 4 }} />
          </PanelSectionRow>
        ) : null}
        <PanelSectionRow>
          <div style={{ width: "100%", fontSize: ".8em", opacity: 0.86 }}>
            {status.game.title || (status.game.appid > 0 ? `AppID ${status.game.appid}` : "No game selected")}
            {hero?.source_label ? ` · ${hero.source_label}` : ""}
            {status.artwork.sample_y != null ? ` · row ${Math.round(status.artwork.sample_y * 100)}%` : ""}
            <PalettePreview colors={artColors} />
          </div>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Performance">
        <PanelSectionRow>
          <DropdownItem
            label="Meter"
            rgOptions={PERFORMANCE_OPTIONS}
            selectedOption={status.performance_metric}
            onChange={async (option) => setStatus(await setSetting("performance_metric", String(option.data)))}
          />
        </PanelSectionRow>
        {status.performance_metric === "mixed" ? (
          <>
            <PanelSectionRow>
              <DropdownItem
                label="Fill direction"
                rgOptions={DIRECTION_OPTIONS}
                selectedOption={status.mixed_direction}
                onChange={async (option) => setStatus(await setSetting("mixed_direction", String(option.data)))}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <div style={{ fontSize: ".78em", opacity: 0.72 }}>
                CPU uses the left 8 LEDs, GPU the right 8, with the centre LED off. Choose two left-to-right meters or the mirrored layout that grows from both edges toward the centre.
              </div>
            </PanelSectionRow>
          </>
        ) : null}
        <PanelSectionRow>
          <div style={{ width: "100%", fontSize: ".84em" }}>
            CPU {status.performance.cpu_load == null ? "—" : `${Math.round(status.performance.cpu_load)}%`}
            {" · "}{status.performance.cpu_temperature == null ? "—" : `${Math.round(status.performance.cpu_temperature)}°C`}
            <br />
            GPU {status.performance.gpu_load == null ? "—" : `${Math.round(status.performance.gpu_load)}%`}
            {" · "}{status.performance.gpu_temperature == null ? "—" : `${Math.round(status.performance.gpu_temperature)}°C`}
            <PalettePreview colors={performanceColors} />
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <DropdownItem
            label="Temperature colours"
            rgOptions={PALETTE_OPTIONS}
            selectedOption={status.temperature_palette}
            onChange={async (option) => setStatus(await setSetting("temperature_palette", String(option.data)))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ fontSize: ".78em", opacity: 0.72 }}>
            Length shows load. Colour shows temperature: the palette starts at Cool temperature and reaches its final hot colour at Hot temperature, with a continuous blend between them.
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <SliderField
            label="Cool temperature"
            value={status.cool_temp_c}
            min={30}
            max={80}
            step={1}
            showValue
            valueSuffix="°C"
            onChange={async (value) => setStatus(await setSetting("cool_temp_c", value))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <SliderField
            label="Hot temperature"
            value={status.hot_temp_c}
            min={60}
            max={110}
            step={1}
            showValue
            valueSuffix="°C"
            onChange={async (value) => setStatus(await setSetting("hot_temp_c", value))}
          />
        </PanelSectionRow>
      </PanelSection>

    </>
  );
}

export default definePlugin(() => ({
  name: "SignalBar",
  titleView: <div className={staticClasses.Title}>SignalBar</div>,
  content: <Content />,
  icon: <FaSignal />,
  alwaysRender: true,
  onDismount() {
    console.log("[SignalBar] frontend dismounted");
  },
}));
