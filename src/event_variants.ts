export const EVENT_VARIANTS = {
  notification: [
    { data: "notification-original", label: "Original · cyan crossing", detail: "One quick cyan crossing." },
    { data: "notification-return", label: "Out and back", detail: "A cyan glint crosses the bar and returns." },
    { data: "notification-echo", label: "Centre echo", detail: "A centre call sends two waves towards the edges." },
    { data: "notification-ample", label: "Wide echo", detail: "A bright centre call, one broad wave, then a softer echo." },
    { data: "notification-double", label: "Double halo", detail: "Two separate centre pulses send halos to the edges." },
    { data: "notification-beacon", label: "Return beacon", detail: "The edges answer a centre beacon and return to it." },
  ],
  achievement: [
    { data: "achievement-original", label: "Original · gold celebration", detail: "Three centre beats open into a full gold bar." },
    { data: "achievement-confetti", label: "Return + confetti", detail: "Gold opens, returns to centre and bursts into colours." },
    { data: "achievement-rebound", label: "Chromatic rebound", detail: "Two gold ribbons rebound from the edges and collide in colour." },
    { data: "achievement-constellation", label: "Constellation", detail: "Stars light in sequence, connect and radiate." },
    { data: "achievement-twoway", label: "Constellation round trip", detail: "A line connects the stars in both directions, flashing at each end." },
    { data: "achievement-supernova", label: "Supernova", detail: "Stars gather at centre, explode and leave a shimmering trail." },
  ],
  screenshot: [
    { data: "screenshot-original", label: "Original · ice shutter", detail: "Two icy blades close like a camera shutter." },
    { data: "screenshot-double", label: "Shutter + two flashes", detail: "A shutter closes; one central flash is followed by a wider flash." },
    { data: "screenshot-scan", label: "Scan + negative", detail: "A focus line scans, flashes, then leaves a fading blue imprint." },
    { data: "screenshot-bloom", label: "Expanding echoes", detail: "Each flash sends a soft echo outwards." },
    { data: "screenshot-ripple", label: "Ricochet echoes", detail: "Narrow echoes reach the edges and bounce back." },
  ],
} as const;

export type EventCategory = keyof typeof EVENT_VARIANTS;
