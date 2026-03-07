/**
 * App icons — Heroicons 2 (hi2) + VS Code Codicons (vsc).
 * Replaces emoji icons for consistent styling.
 * @see https://react-icons.github.io/react-icons/icons/hi2/
 * @see https://github.com/microsoft/vscode-codicons (via react-icons/vsc)
 */

import {
  HiFire,
  HiChartBar,
  HiRectangleStack,
  HiDocumentText,
  HiSparkles,
  HiExclamationTriangle,
  HiBolt,
  HiArrowPath,
  HiCog6Tooth,
  HiUser,
  HiSquares2X2,
  HiBookOpen,
  HiSun,
  HiMoon,
} from "react-icons/hi2";

const iconClass = "w-5 h-5";

export const Icons = {
  streak: <HiFire className={iconClass} />,
  chart: <HiChartBar className={iconClass} />,
  cards: <HiRectangleStack className={iconClass} />,
  quiz: <HiDocumentText className={iconClass} />,
  ai: <HiSparkles className={iconClass} />,
  insights: <HiChartBar className={iconClass} />,
  panic: <HiExclamationTriangle className={iconClass} />,
  conflicts: <HiBolt className={iconClass} />,
  sync: <HiArrowPath className={iconClass} />,
  settings: <HiCog6Tooth className={iconClass} />,
  profile: <HiUser className={iconClass} />,
  dashboard: <HiSquares2X2 className={iconClass} />,
  book: <HiBookOpen className={iconClass} />,
  offline: <HiBolt className={iconClass} />,
  sun: <HiSun className={iconClass} />,
  moon: <HiMoon className={iconClass} />,
  /** Larger AI icon for empty states (e.g. Chat) */
  aiLarge: <HiSparkles className="w-12 h-12" />,
};
