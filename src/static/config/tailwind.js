tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "sans-serif",
        ],
      },
      colors: {
        action: {
          DEFAULT: "#0066cc",
          focus: "#0071e3",
          dark: "#2997ff",
        },
        ink: {
          DEFAULT: "#1d1d1f",
          80: "#333333",
          48: "#7a7a7a",
        },
        parchment: "#f5f5f7",
        pearl: "#fafafc",
        hairline: "#e0e0e0",
        divider: "#f0f0f0",
        tile: {
          1: "#272729",
          2: "#2a2a2c",
          3: "#252527",
        },
      },
      fontSize: {
        body: ["17px", { lineHeight: "1.47", letterSpacing: "-0.374px" }],
      },
    },
  },
};
