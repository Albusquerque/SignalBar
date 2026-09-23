import type { WeatherCondition } from "./types";

export const WEATHER_CONDITIONS: { data: WeatherCondition; label: string }[] = [
  { data: "clear_day", label: "Clear sky · sun" },
  { data: "clear_night", label: "Clear sky · moon + stars" },
  { data: "rain", label: "Rain" },
  { data: "cloud", label: "Cloud" },
  { data: "breaks", label: "Partly cloudy · day" },
  { data: "breaks_night", label: "Partly cloudy · night" },
  { data: "snow", label: "Snow" },
  { data: "storm", label: "Thunderstorm" },
];

export const WEATHER_VARIANTS: Record<WeatherCondition, { label: string; detail: string }[]> = {
  clear_day: [
    { label: "Sun glints", detail: "White-gold reflections travel across a gently sparkling yellow band." },
    { label: "Solar bloom", detail: "A white-yellow centre grows across a steady golden band, then recedes." },
  ],
  clear_night: [
    { label: "Quiet constellation", detail: "Three stationary stars share one slow, soft cycle." },
    { label: "Silver hush", detail: "A narrow silver centre breathes slowly into the surrounding night." },
  ],
  rain: [
    { label: "Bluewater", detail: "A continuous blue band holds while blue-white drops and short echoes land on it." },
    { label: "Pearl rain", detail: "Blue drops and short ripples interrupt a dimmer white band." },
  ],
  cloud: [
    { label: "Passing shadow", detail: "A wide shadow crosses a continuous soft-white sky, with a brief silver edge." },
    { label: "Passing shadows", detail: "A second shadow follows from the other side without crossing at the centre." },
  ],
  breaks: [
    { label: "Sun through clouds", detail: "The familiar sun opens through a soft-white cloud field, then closes." },
    { label: "Sun, fading clouds", detail: "White clouds fade all the way out as the yellow sun opens, then return." },
  ],
  breaks_night: [
    { label: "Moon through clouds", detail: "The familiar pale moon opens through dim-white clouds, then closes." },
    { label: "Moon, fading clouds", detail: "Dim-white clouds fade all the way out as the pale moon opens, then return." },
  ],
  snow: [
    { label: "Melting snowfall", detail: "Paired, then single gaps appear in a soft white field and fill back in." },
    { label: "Snow takes hold", detail: "White flakes gather until the whole bar is covered, then the scene starts again." },
  ],
  storm: [
    { label: "Pulse and echoes", detail: "A second lightning phrase follows the first, each with scattered echoes." },
    { label: "Storm break", detail: "A fast double strike returns once more after a pause." },
  ],
};
