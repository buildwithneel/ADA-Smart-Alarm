import { Variants, Transition } from "framer-motion";

/**
 * ADA Core Spring Physics & Timing Transitions
 * Tuned for 150-400ms duration with snappy tactile response.
 */
export const springPhysics: Record<string, Transition> = {
  snappy: { type: "spring", stiffness: 450, damping: 30 },
  gentle: { type: "spring", stiffness: 300, damping: 28 },
  bouncy: { type: "spring", stiffness: 500, damping: 22 },
  linearFast: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  linearStandard: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
};

/**
 * 1. Landing page hero entrance
 */
export const heroEntrance: Variants = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0, transition: springPhysics.gentle },
};

/**
 * 2. Hero text stagger
 */
export const heroTextStagger: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.05 },
  },
};

/**
 * 3. Hero CTA entrance
 */
export const heroCtaEntrance: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1, transition: springPhysics.snappy },
};

/**
 * 4. Navigation entrance
 */
export const navEntrance: Variants = {
  initial: { opacity: 0, y: -12 },
  animate: { opacity: 1, y: 0, transition: springPhysics.linearFast },
};

/**
 * 5. Page transitions
 */
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: springPhysics.linearStandard },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
};

/**
 * 6. Sidebar entrance
 */
export const sidebarEntrance: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0, transition: springPhysics.gentle },
};

/**
 * 7. Mobile bottom navigation transition
 */
export const mobileNavVariants: Variants = {
  initial: { y: 60, opacity: 0 },
  animate: { y: 0, opacity: 1, transition: springPhysics.snappy },
};

/**
 * 8. Dashboard greeting entrance
 */
export const greetingEntrance: Variants = {
  initial: { opacity: 0, x: -16 },
  animate: { opacity: 1, x: 0, transition: springPhysics.gentle },
};

/**
 * 9. Next alarm card entrance
 */
export const nextAlarmCardEntrance: Variants = {
  initial: { opacity: 0, y: 20, scale: 0.97 },
  animate: { opacity: 1, y: 0, scale: 1, transition: springPhysics.gentle },
};

/**
 * 10. Next alarm card hover
 */
export const cardHoverVariants: Variants = {
  rest: { y: 0, scale: 1 },
  hover: { y: -2, transition: springPhysics.linearFast },
};

/**
 * 11. ETA number transition
 */
export const etaNumberVariants: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: springPhysics.snappy },
};

/**
 * 12 & 13. Destination card entrance & hover
 */
export const destinationCardVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: springPhysics.gentle },
  hover: { y: -3, transition: springPhysics.snappy },
};

/**
 * 14. Quick action pill hover
 */
export const quickActionHover: Variants = {
  rest: { scale: 1 },
  hover: { scale: 1.04, transition: springPhysics.snappy },
  tap: { scale: 0.96 },
};

/**
 * 15 & 16. Button press & loading
 */
export const buttonPressVariants: Variants = {
  rest: { scale: 1 },
  tap: { scale: 0.97 },
};

/**
 * 17 & 18. Alarm card entrance & hover
 */
export const alarmCardVariants: Variants = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: springPhysics.gentle },
  hover: { y: -2, transition: springPhysics.linearFast },
};

/**
 * 19. Alarm enable switch transition
 */
export const switchThumbVariants: Variants = {
  off: { x: 2 },
  on: { x: 22, transition: springPhysics.snappy },
};

/**
 * 20. Alarm status transition
 */
export const statusPillVariants: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: { opacity: 1, scale: 1, transition: springPhysics.snappy },
};

/**
 * 21. Timeline line animation
 */
export const timelineLineVariants: Variants = {
  initial: { scaleY: 0, originY: 0 },
  animate: { scaleY: 1, transition: { duration: 0.6, ease: "easeOut" } },
};

/**
 * 22. Timeline node animation
 */
export const timelineNodeVariants: Variants = {
  initial: { scale: 0 },
  animate: { scale: 1, transition: springPhysics.bouncy },
};

/**
 * 23. Timeline item stagger
 */
export const timelineStagger: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
};

/**
 * 24. Create-alarm form entrance
 */
export const formEntranceVariants: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: springPhysics.gentle },
};

/**
 * 25. Form field focus animation
 */
export const fieldFocusVariants: Variants = {
  unfocused: { borderColor: "rgba(255, 255, 255, 0.08)" },
  focused: { borderColor: "rgba(99, 102, 241, 0.8)", transition: { duration: 0.15 } },
};

/**
 * 26. Form validation error shake
 */
export const validationShakeVariants: Variants = {
  idle: { x: 0 },
  error: {
    x: [-6, 6, -4, 4, -2, 2, 0],
    transition: { duration: 0.35 },
  },
};

/**
 * 27. Dropdown entrance
 */
export const dropdownVariants: Variants = {
  initial: { opacity: 0, y: -6, scale: 0.96 },
  animate: { opacity: 1, y: 0, scale: 1, transition: springPhysics.snappy },
  exit: { opacity: 0, y: -4, scale: 0.96, transition: { duration: 0.1 } },
};

/**
 * 28 & 29. Modal entrance & exit
 */
export const modalVariants: Variants = {
  initial: { opacity: 0, scale: 0.95, y: 12 },
  animate: { opacity: 1, scale: 1, y: 0, transition: springPhysics.snappy },
  exit: { opacity: 0, scale: 0.96, y: 8, transition: { duration: 0.15 } },
};

/**
 * 30 & 31. Toast entrance & exit
 */
export const toastVariants: Variants = {
  initial: { opacity: 0, y: 16, scale: 0.94 },
  animate: { opacity: 1, y: 0, scale: 1, transition: springPhysics.snappy },
  exit: { opacity: 0, y: 12, scale: 0.95, transition: { duration: 0.15 } },
};

/**
 * 32. Empty-state entrance
 */
export const emptyStateVariants: Variants = {
  initial: { opacity: 0, scale: 0.92 },
  animate: { opacity: 1, scale: 1, transition: springPhysics.gentle },
};

/**
 * 33. Skeleton shimmer
 */
export const shimmerVariants: Variants = {
  animate: {
    backgroundPosition: ["200% 0", "-200% 0"],
    transition: { repeat: Infinity, duration: 1.6, ease: "linear" },
  },
};

/**
 * 34. Loading spinner
 */
export const spinnerVariants: Variants = {
  animate: {
    rotate: 360,
    transition: { repeat: Infinity, duration: 0.8, ease: "linear" },
  },
};

/**
 * 35. Settings section entrance
 */
export const settingsSectionVariants: Variants = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: springPhysics.gentle },
};

/**
 * 36. Settings switch animation
 */
export const switchContainerVariants: Variants = {
  off: { backgroundColor: "rgba(255, 255, 255, 0.1)" },
  on: { backgroundColor: "#4f46e5" },
};

/**
 * 37. Theme transition
 */
export const themeTransitionVariants: Variants = {
  initial: { opacity: 0.6, rotate: -20 },
  animate: { opacity: 1, rotate: 0, transition: springPhysics.snappy },
};

/**
 * 38. Profile menu animation
 */
export const profileMenuVariants: Variants = {
  initial: { opacity: 0, y: -8, scale: 0.95 },
  animate: { opacity: 1, y: 0, scale: 1, transition: springPhysics.snappy },
  exit: { opacity: 0, y: -6, scale: 0.95, transition: { duration: 0.1 } },
};

/**
 * 39. Command palette animation
 */
export const commandPaletteVariants: Variants = {
  initial: { opacity: 0, scale: 0.96, y: -16 },
  animate: { opacity: 1, scale: 1, y: 0, transition: springPhysics.snappy },
  exit: { opacity: 0, scale: 0.97, y: -10, transition: { duration: 0.12 } },
};

/**
 * 40. Search result stagger
 */
export const searchResultStagger: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.02 },
  },
};

/**
 * 41. Activity timeline animation
 */
export const activityItemVariants: Variants = {
  initial: { opacity: 0, x: -12 },
  animate: { opacity: 1, x: 0, transition: springPhysics.gentle },
};

/**
 * 42. Traffic status radar pulse
 */
export const trafficRadarVariants: Variants = {
  pulse: {
    scale: [1, 1.4, 1],
    opacity: [0.9, 0.3, 0.9],
    transition: { duration: 2.2, repeat: Infinity, ease: "easeInOut" },
  },
};

/**
 * 43. Weather card transition
 */
export const weatherCardVariants: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1, transition: springPhysics.snappy },
};

/**
 * 44. Scroll reveal
 */
export const scrollRevealVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: springPhysics.gentle },
};

/**
 * 45. Mobile bottom nav active indicator pill
 */
export const activeIndicatorVariants: Variants = {
  initial: { scale: 0.8 },
  animate: { scale: 1, transition: springPhysics.snappy },
};

/**
 * 46. Delete confirmation animation
 */
export const deleteConfirmVariants: Variants = {
  initial: { opacity: 0, scale: 0.9, y: 10 },
  animate: { opacity: 1, scale: 1, y: 0, transition: springPhysics.snappy },
  exit: { opacity: 0, scale: 0.92, transition: { duration: 0.12 } },
};

/**
 * 47. Success-state checkmark animation
 */
export const successCheckVariants: Variants = {
  initial: { pathLength: 0, opacity: 0 },
  animate: { pathLength: 1, opacity: 1, transition: { duration: 0.4, ease: "easeOut" } },
};

/**
 * 48. Error state icon pulse
 */
export const errorIconVariants: Variants = {
  initial: { scale: 0.8, opacity: 0 },
  animate: { scale: 1, opacity: 1, transition: springPhysics.bouncy },
};
