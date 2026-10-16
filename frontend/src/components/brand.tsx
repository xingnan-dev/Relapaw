import type { CSSProperties, SVGProps } from "react";
import journalStickerSheet from "../assets/relapaw-journal-stickers.png";

export function BrandMark({ className = "", ...props }: SVGProps<SVGSVGElement>) {
  return <svg className={["brand-symbol", className].filter(Boolean).join(" ")} viewBox="0 0 48 48" fill="none" aria-hidden="true" {...props}>
    <defs><linearGradient id="relapaw-mark" x1="7" y1="6" x2="40" y2="42"><stop stopColor="#9EDBD2"/><stop offset=".48" stopColor="#C7B8DE"/><stop offset="1" stopColor="#E8B5CC"/></linearGradient></defs>
    <g><path d="M15.2 23.8c-4.1 1.7-6.7 5.3-6 9.3.8 4.7 6 7.8 10.8 5.4 1.5-.7 2.6-1.8 4-1.8s2.5 1.1 4 1.8c4.8 2.4 10-.7 10.8-5.4.7-4-1.9-7.6-6-9.3-3.1-1.3-4.8-4.3-8.8-4.3s-5.7 3-8.8 4.3Z" fill="url(#relapaw-mark)"/><ellipse cx="13" cy="16" rx="4.3" ry="5.3" transform="rotate(-24 13 16)" fill="url(#relapaw-mark)"/><ellipse cx="23" cy="11.7" rx="4.2" ry="5.4" fill="url(#relapaw-mark)"/><ellipse cx="34.5" cy="16" rx="4.3" ry="5.3" transform="rotate(24 34.5 16)" fill="url(#relapaw-mark)"/></g>
    <path d="M18.4 29.2c2.1-2 4-3 5.6-3s3.5 1 5.6 3" stroke="white" strokeWidth="2.2" strokeLinecap="round" opacity=".86"/>
  </svg>;
}

export function BrandAtmosphere() {
  return <svg className="brand-atmosphere" viewBox="0 0 1200 820" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <filter id="garden-blur"><feGaussianBlur stdDeviation="34"/></filter><filter id="garden-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><filter id="paper-line"><feTurbulence type="fractalNoise" baseFrequency=".018" numOctaves="2" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="4"/></filter>
      <radialGradient id="garden-rose"><stop stopColor="#EAB4CC" stopOpacity=".56"/><stop offset="1" stopColor="#F2D9E4" stopOpacity="0"/></radialGradient><radialGradient id="garden-blue"><stop stopColor="#B8DDE1" stopOpacity=".48"/><stop offset="1" stopColor="#D9ECEC" stopOpacity="0"/></radialGradient><radialGradient id="garden-violet"><stop stopColor="#CABBE1" stopOpacity=".5"/><stop offset="1" stopColor="#E3DCEE" stopOpacity="0"/></radialGradient><linearGradient id="memory-light" x1="80" y1="710" x2="1120" y2="130" gradientUnits="userSpaceOnUse"><stop stopColor="#8CCFC7" stopOpacity=".08"/><stop offset=".42" stopColor="#FFF9D7" stopOpacity=".88"/><stop offset=".7" stopColor="#D6BDE4" stopOpacity=".54"/><stop offset="1" stopColor="#E8B3C9" stopOpacity=".08"/></linearGradient>
    </defs>
    <g filter="url(#garden-blur)" className="garden-washes"><ellipse cx="90" cy="650" rx="270" ry="230" fill="url(#garden-blue)"/><ellipse cx="1075" cy="190" rx="290" ry="225" fill="url(#garden-violet)"/><ellipse cx="1040" cy="700" rx="285" ry="190" fill="url(#garden-rose)"/><ellipse cx="230" cy="90" rx="220" ry="140" fill="url(#garden-rose)"/></g>
    <g className="memory-path" filter="url(#garden-glow)"><path d="M40 720C220 610 215 452 405 438S690 520 805 382 948 172 1165 130"/><path d="M160 790C302 675 390 645 527 638 720 628 781 514 887 420"/></g>
    <g className="garden-sketch" filter="url(#paper-line)"><path d="M72 690c34-80 72-148 121-207m-61 113c-33-5-58-20-77-46m91 15c31-10 55-29 72-56m-54 30c-12-42-9-77 8-106m20 76c30-2 58-15 82-39"/><path d="M1060 760c-12-84-4-155 25-214m-19 91c-36-15-60-39-73-72m78 39c30-15 52-39 65-71m-52 13c2-48 17-86 46-115"/><path d="M111 432c-10-36 4-67 35-75 29-8 59 10 64 39 5 31-17 57-48 59-23 1-43-7-51-23Zm30-66c-20-24-24-51-11-81m48 75c14-29 34-49 61-58"/><path d="M1014 326c-30-9-48-34-41-61 7-28 37-44 65-34 29 11 41 43 27 69-10 19-29 29-51 26Zm-29-70c-24-13-42-33-51-59m99 32c1-32 13-57 36-77"/><path d="M214 725c18-26 41-30 61-12 18 16 17 37-2 59m-61-45c-18 10-34 26-46 48m109-61c19 4 37 15 52 32"/><path d="M932 707c21-33 49-39 73-17 22 20 19 48-7 72m-64-54c-25 12-44 31-57 57m128-73c23 2 44 13 61 31"/></g>
    <g className="chalk-accent"><path d="M296 139v25m-12.5-12.5h25M905 103v19m-9.5-9.5h19M1095 512v24m-12-12h24"/><path d="m251 207 5 10 11 2-8 8 2 11-10-5-10 5 2-11-8-8 11-2 5-10Z"/><circle cx="335" cy="684" r="4"/><circle cx="847" cy="572" r="3"/></g>
  </svg>;
}

export type NavIconName = "today" | "understand" | "timeline" | "us";
export function NavIcon({ name }: { name: NavIconName }) {
  const common = { width: 30, height: 30, viewBox: "0 0 32 32", fill: "none", stroke: "currentColor", strokeWidth: 1.42, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  if (name === "today") return <svg {...common} className="nav-character nav-character--today">
    <path className="nav-character__body" d="M7.2 23.8c-1.3-4.7-.3-11.7 2.5-15.6l3.9 3.1c1.6-.5 3.5-.5 5.1 0l3.9-3c2.5 4 3.5 10.8 2.2 15.5-3.9 2.7-13.7 2.8-17.6 0Z" />
    <path d="m20.4 18.8 6.7-5.4 1.7 2.1-6.8 5.3m5.1-7.4 1.2-.9 1.7 2.1-1.2.9" /><circle cx="13.2" cy="16" r=".7" fill="currentColor" stroke="none"/><circle cx="19.1" cy="16" r=".7" fill="currentColor" stroke="none"/><path d="m15.1 18.2 1.1.8 1.2-.8" /><path className="nav-character__spot" d="M12 10.2c2.1-1.8 5.8-2.1 8.1-.2l-1.2 2.1h-5.8L12 10.2Z" />
  </svg>;
  if (name === "understand") return <svg {...common} className="nav-character nav-character--understand">
    <path className="nav-character__body" d="M8 24.5c-1.1-4.7-.5-11.5 1.6-15.6 3.3-1.6 9.1-1.5 12.4.1 2 4.1 2.6 10.8 1.5 15.4-3.9 2.5-11.7 2.6-15.5.1Z" /><path d="M9.4 10.2C5.7 8 3.7 10 4.3 13.6c.5 3 2.4 4.7 5 4.1m13.1-7.4c3.8-2.2 5.7-.2 5.1 3.4-.5 3-2.4 4.7-5 4" /><circle cx="13" cy="14.8" r=".7" fill="currentColor" stroke="none"/><circle cx="19" cy="14.8" r=".7" fill="currentColor" stroke="none"/><path d="M15.2 17.2c.6.5 1.2.5 1.8 0" /><path d="M7 21.3h6v6H7zm12 0h6v6h-6z" /><path className="nav-character__spot" d="M13.2 7.5c.5-2 1.6-3 3.1-3 1.7 0 2.8 1.1 3.2 3.1-2.1-.7-4.2-.7-6.3-.1Z" />
  </svg>;
  if (name === "timeline") return <svg {...common} className="nav-character nav-character--timeline">
    <path className="nav-character__body" d="M8.1 24.1c-1.2-4.8-.4-11.7 2-15.8 3.4-1.3 8.1-1.2 11.4.2 2.2 4 2.9 10.8 1.7 15.6-3.8 2.7-11.2 2.7-15.1 0Z" /><path d="M12 8.3c-.3-2.7-1.4-4.4-3.2-5.2m6.5 4.7c.1-3.1 1-5.1 2.7-6m.4 6.6c1.2-2.4 2.8-3.7 4.8-4" /><circle cx="12.8" cy="14.9" r=".7" fill="currentColor" stroke="none"/><circle cx="18.6" cy="14.9" r=".7" fill="currentColor" stroke="none"/><path d="m14.7 17.2 1.1.8 1.2-.8M23 22c3.3.6 5.1 2.3 5.4 5"/><circle cx="27.7" cy="27.2" r="1.4"/><path className="nav-character__spot" d="M7.4 21.3c2.1 1 4.1 1.4 6.2 1.4l-1 3.2c-2-.2-3.6-.8-4.9-1.8l-.3-2.8Z" />
  </svg>;
  return <svg {...common} className="nav-character nav-character--us">
    <path className="nav-character__body" d="M3.8 23.5c-.7-4.8.3-10.3 2.7-13.7 2.7-1.3 6.4-1.2 9 .2 2 3.6 2.5 8.7 1.5 13-3.4 2.4-9.9 2.6-13.2.5Zm13.4-.4c-1-4.4-.4-9.6 1.7-13.2 2.8-1.4 6.3-1.3 9 .1 1.5 3.9 1.8 9 .5 13.4-3.1 2.3-8 2.3-11.2-.3Z" /><circle cx="9" cy="15.2" r=".65" fill="currentColor" stroke="none"/><circle cx="12.8" cy="15.2" r=".65" fill="currentColor" stroke="none"/><circle cx="22" cy="15.2" r=".65" fill="currentColor" stroke="none"/><circle cx="25.8" cy="15.2" r=".65" fill="currentColor" stroke="none"/><path d="M9.8 18c.7.5 1.5.5 2.2 0m10.8 0c.7.5 1.5.5 2.2 0M5.6 21.2c7 2.1 14 2.1 21-.1" /><path className="nav-character__spot" d="M7.1 20.4c5.9 1.8 12 1.8 18.2 0l.6 2.4c-6.4 2-12.9 2-19.4 0l.6-2.4Z" />
  </svg>;
}

export type PetSketchScene = "today" | "understand" | "timeline" | "us";

export type JournalDoodleName = "clock" | "observe" | "thought" | "home" | "profile" | "promise" | "privacy";
export type JournalStickerName = "cat" | "dog" | "bow" | "cup" | "star" | "spiral";
export function JournalSticker({ name, className = "" }: { name: JournalStickerName; className?: string }) {
  return <span className={["journal-sticker", `journal-sticker--${name}`, className].filter(Boolean).join(" ")} style={{ "--journal-sticker-sheet": `url(${journalStickerSheet})` } as CSSProperties} aria-hidden="true" />;
}

export function JournalDoodle({ name, material = "draw", className = "" }: { name: JournalDoodleName; material?: "draw" | "sticker"; className?: string }) {
  const art = {
    clock: <><circle cx="32" cy="32" r="17"/><path d="M32 21v12l8 5M19 14l-5 6m31-6 5 6"/><path className="journal-doodle__accent" d="M25 8c5-3 12-3 17 0"/></>,
    observe: <><path d="M8 33c12-17 36-17 48 0-12 17-36 17-48 0Z"/><circle cx="32" cy="33" r="8"/><circle className="journal-doodle__accent" cx="34" cy="31" r="2"/><path d="M13 16c5-4 10-6 15-6m21 7c-4-4-9-6-14-7"/></>,
    thought: <><path d="M14 15c10-8 29-7 36 3 7 10 0 23-13 25-5 1-10 0-14-2l-10 6 3-11c-8-7-7-15-2-21Z"/><path className="journal-doodle__accent" d="M24 27c2-5 10-6 14-2 3 4 1 9-4 11m0 5v1"/></>,
    home: <><path d="m10 31 22-19 22 19M16 27v25h32V27M27 52V37h11v15"/><path className="journal-doodle__accent" d="M44 14c5 2 8 6 9 11M12 16c3-3 6-5 10-6"/></>,
    profile: <><path d="M14 51c2-12 9-19 18-19s16 7 18 19"/><circle cx="32" cy="21" r="10"/><path d="m24 14-5-7 10 5m11 2 6-7-11 5"/><path className="journal-doodle__accent" d="M26 22h1m10 0h1m-10 5c3 2 6 2 9 0"/></>,
    promise: <><path d="M11 44c8-9 14-13 21-13 8 0 14 4 21 13M20 31V17l9 7m15 7V17l-9 7"/><path className="journal-doodle__accent" d="M25 42c5 3 10 3 15 0M26 14c2-5 7-5 9 0 3-5 8-3 7 2-1 5-8 9-8 9s-10-5-8-11Z"/></>,
    privacy: <><path d="M16 28h32v25H16zM22 28v-7c0-7 4-11 10-11s10 4 10 11v7"/><path d="M32 38v7"/><circle className="journal-doodle__accent" cx="32" cy="37" r="3"/><path className="journal-doodle__accent" d="m48 13 2 4 4 2-4 2-2 4-2-4-4-2 4-2 2-4Z"/></>,
  }[name];
  return <span className={["journal-doodle", `journal-doodle--${material}`, `journal-doodle--${name}`, className].filter(Boolean).join(" ")} aria-hidden="true"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">{art}</svg></span>;
}

export function PetBotanicalSketch({ scene, className = "" }: { scene: PetSketchScene; className?: string }) {
  const story = {
    today: <>
      <path className="pet-sketch-wash" d="M27 130c9-49 47-84 102-84 57 0 99 31 104 72 4 32-16 43-51 43H72c-32 0-50-8-45-31Z" />
      <g className="pet-sketch-line" strokeLinecap="round" strokeLinejoin="round">
        <path d="M75 135c8-36 32-53 68-49 27 3 45 19 49 48" />
        <path d="M102 88 94 64l22 15m43 8 13-22-25 14" />
        <path d="M112 111c12-7 25-5 34 5-8 9-23 10-34-5Z" /><path d="m127 113 1 8m-9 0c6 5 13 5 19-1" />
        <circle cx="106" cy="101" r="2.4" /><circle cx="154" cy="101" r="2.4" />
        <path d="M53 142h166M56 132c6-9 15-14 25-16m111 2c10 3 18 9 24 18" />
        <path d="m157 70 35-27 8 10-36 25m28-35 8-6 8 10-8 6" />
        <path d="M55 105h35M48 113h43M48 121h31" />
      </g>
      <g className="pet-sketch-detail" strokeLinecap="round"><path d="M39 92c13-9 26-11 39-6m127 11c8 2 15 6 21 12" /><path d="m67 66 4 8 9 1-7 6 2 9-8-5-8 5 2-9-7-6 9-1 4-8Z" /></g>
    </>,
    understand: <>
      <path className="pet-sketch-wash" d="M25 121c5-43 38-75 91-80 59-6 108 23 117 69 6 34-16 48-56 49H76c-34 0-54-8-51-38Z" />
      <g className="pet-sketch-line" strokeLinecap="round" strokeLinejoin="round">
        <path d="M39 82h70l-7 64H47L39 82Zm112 0h70l-8 64h-55l-7-64Z" /><path d="M54 82c10-19 27-29 50-31m61 31c7-18 22-29 46-33" />
        <path d="M73 66 66 45l19 14m94 6 12-20-23 12" /><circle cx="78" cy="75" r="2.3" /><circle cx="180" cy="75" r="2.3" />
        <path d="M64 104c9-7 20-7 29 0m-22 8c5 4 10 4 15 0m81-8c10-7 21-7 31 0m-22 8c5 4 11 4 16 0" />
        <path d="M23 151h215M117 63c6 9 10 21 11 35m-8-8 8 8 7-9" />
      </g>
      <g className="pet-sketch-detail" strokeLinecap="round"><path d="M52 130c11 4 22 4 34 0m77 0c12 4 23 4 35 0" /><path d="M112 38c5-5 11-8 17-8m-1 0 3-8m-3 8 9 2" /></g>
    </>,
    timeline: <>
      <path className="pet-sketch-wash" d="M24 128c10-48 48-84 101-86 59-2 105 32 108 76 2 30-18 42-53 43H72c-34-1-53-9-48-33Z" />
      <g className="pet-sketch-line" strokeLinecap="round" strokeLinejoin="round">
        <path d="M27 143c31-4 47-12 72-10 27 2 40 13 63 10 19-2 29-12 52-14" />
        <circle cx="49" cy="139" r="5.5" /><circle cx="99" cy="133" r="5.5" /><circle cx="162" cy="143" r="5.5" /><circle cx="214" cy="129" r="5.5" />
        <path d="M79 99c4-27 24-44 50-43 30 1 49 22 48 50" /><path d="m101 62-4-22 20 17m39 9 14-20-25 12" />
        <path d="M113 84c11-7 24-6 34 4-8 9-23 10-34-4Z" /><circle cx="106" cy="77" r="2.3" /><circle cx="154" cy="77" r="2.3" />
        <path d="m127 87 1 8m-9 0c6 5 13 5 19 0M25 153h213" />
      </g>
      <g className="pet-sketch-detail" strokeLinecap="round"><path d="M44 112c-1-12 2-22 10-30m144 2c10-7 20-10 31-8" /><path d="M63 84c5-5 11-7 18-8m103-25c7 3 12 8 16 15" /></g>
    </>,
    us: <>
      <path className="pet-sketch-wash" d="M25 126c8-45 43-80 98-84 60-4 106 28 111 73 4 32-17 45-53 46H75c-34 0-54-9-50-35Z" />
      <g className="pet-sketch-line" strokeLinecap="round" strokeLinejoin="round">
        <path d="M39 132c10-27 29-41 56-41 27 0 46 14 56 41M143 132c9-25 27-38 52-38 25 0 43 13 53 38" />
        <path d="M61 96c2-25 16-40 36-40 19 0 33 13 36 37M78 61l-4-20 18 15m27 7 13-18-22 12" />
        <path d="M85 79c8-5 17-4 25 4-6 7-17 7-25-4Z" /><circle cx="79" cy="73" r="2.1" /><circle cx="118" cy="73" r="2.1" /><path d="m96 82 1 7m-8 0c5 4 11 4 16 0" />
        <path d="M160 100c3-24 16-38 35-38 19 0 33 13 36 37m-53-32-3-18 16 13m25 7 11-17-20 11" />
        <path d="M184 84c8-5 16-4 23 3-6 7-16 7-23-3Z" /><circle cx="178" cy="78" r="2" /><circle cx="218" cy="78" r="2" /><path d="m195 87 1 7m-8 0c5 4 11 4 16 0M25 151h216" />
      </g>
      <g className="pet-sketch-detail" strokeLinecap="round"><path d="m66 122 10 5 11-5m112 2 10 5 10-5" /><path d="M125 31c5-7 11-7 16 0 5-7 12-5 13 1 1 8-13 15-13 15s-17-8-16-16Z" /></g>
    </>,
  }[scene];
  return <svg className={["pet-botanical-sketch", `pet-botanical-sketch--${scene}`, className].filter(Boolean).join(" ")} viewBox="0 0 260 170" fill="none" aria-hidden="true">
    {story}
  </svg>;
}
