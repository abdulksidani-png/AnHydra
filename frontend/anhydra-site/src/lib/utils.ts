import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["btn", "btn-xs", "badge"] }],
      "font-weight": [{ font: ["btn", "badge"] }],
      // The theme's radius tokens, so a className radius (rounded-3xl on a Card) replaces the default.
      rounded: [{ rounded: ["btn", "badge", "card", "input"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
