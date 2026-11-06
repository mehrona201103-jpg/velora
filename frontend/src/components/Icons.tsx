import React from 'react'

type P = { size?: number; className?: string }

const s = (size = 20) => ({ width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const })

export const IconHome = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z"/></svg>
)
export const IconSearch = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
)
export const IconUser = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5"/></svg>
)
export const IconCart = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M6 6h15l-1.5 9h-12z"/><path d="M6 6L5 3H2"/><circle cx="9" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/></svg>
)
export const IconHeart = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M12 21s-7-4.5-9.5-8.5C.5 9 2.5 5 6.5 5c2 0 3.5 1.2 4.5 2.5C12 6.2 13.5 5 15.5 5c4 0 6 4 4 7.5C19 16.5 12 21 12 21z"/></svg>
)
export const IconHeartFill = ({ size, className }: P) => (
  <svg width={size||20} height={size||20} viewBox="0 0 24 24" className={className} fill="currentColor"><path d="M12 21s-7-4.5-9.5-8.5C.5 9 2.5 5 6.5 5c2 0 3.5 1.2 4.5 2.5C12 6.2 13.5 5 15.5 5c4 0 6 4 4 7.5C19 16.5 12 21 12 21z"/></svg>
)
export const IconCamera = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M4 8h3l2-2h6l2 2h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>
)
export const IconTruck = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M1 7h13v10H1z"/><path d="M14 10h4l3 3v4h-7"/><circle cx="5.5" cy="18.5" r="1.5"/><circle cx="16.5" cy="18.5" r="1.5"/></svg>
)
export const IconStore = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M3 9l1.5-5h15L21 9"/><path d="M3 9v11h18V9"/><path d="M9 20v-6h6v6"/></svg>
)
export const IconCard = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M6 15h4"/></svg>
)
export const IconStar = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M12 3l2.5 6.5H21l-5 4.2 1.8 6.3L12 16.5 6.2 20l1.8-6.3-5-4.2h6.5z"/></svg>
)
export const IconCheck = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M5 13l4 4L19 7"/></svg>
)
export const IconLock = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
)
export const IconFingerprint = ({ size, className }: P) => (
  <svg {...s(size)} className={className}>
    <path d="M12 11a3 3 0 0 0-3 3v1"/><path d="M12 7a7 7 0 0 0-7 7v1"/>
    <path d="M12 3a11 11 0 0 0-8 3"/><path d="M12 15v3"/><path d="M15 14a3 3 0 0 1 1 2.2V18"/>
    <path d="M19 14a7 7 0 0 1-1.2 4"/><path d="M20 10a11 11 0 0 1 0 2"/>
  </svg>
)
export const IconAdmin = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
)
export const IconLogout = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>
)
export const IconPackage = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M12 2L3 7v10l9 5 9-5V7z"/><path d="M12 22V12"/><path d="M3 7l9 5 9-5"/></svg>
)
export const IconChat = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M21 12a8 8 0 0 1-11.5 7.2L3 21l1.8-5.3A8 8 0 1 1 21 12z"/></svg>
)
export const IconArrow = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></svg>
)
export const IconClose = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M6 6l12 12M18 6L6 18"/></svg>
)
export const IconBank = ({ size, className }: P) => (
  <svg {...s(size)} className={className}><path d="M3 10l9-6 9 6"/><path d="M5 10v8h14v-8"/><path d="M3 18h18"/><path d="M9 14v4M15 14v4"/></svg>
)
