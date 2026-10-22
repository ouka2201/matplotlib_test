/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        destructive: "var(--color-red)",
        'base-text': 'var(--color-black)',
        // black: 'var(--color-black)',
        gray: {
          dark: 'var(--color-gray-dark)',
          DEFAULT: 'var(--color-gray)',
          light: 'var(--color-gray-light)',
        },
        green: {
          DEFAULT: 'var(--color-green)',
          primary: 'var(--color-green-primary)',
        },
        // red: 'var(--color-red)',
        // pink: 'var(--color-pink)',
        // white: 'var(--color-white)',
        background: 'var(--color-background)',
        'white-pale': 'var(--color-white-pale)',
        disable: 'var(--color-disable)',
        'default-hover': 'var(--color-default-hover)',
        'default-clicked': 'var(--color-default-clicked)',
        'primary-hover': 'var(--color-primary-hover)',
        'primary-clicked': 'var(--color-primary-clicked)',
        'secondary-hover': 'var(--color-secondary-hover)',
        'secondary-clicked': 'var(--color-secondary-clicked)',
      },
      fontSize: {
        base: ['14px', { lineHeight: '150%' }],
        // base: 'var(--font-size-base)',
        sm: 'var(--font-size-sm)',
        md: 'var(--font-size-md)',
        lg: 'var(--font-size-lg)',
        xl: 'var(--font-size-xl)',
      },
      fontWeight: {
        normal: 'var(--font-weight-normal)',
        bold: 'var(--font-weight-bold)',
      },
      fontFamily: {
        sans: 'var(--default-font-family)',
      },
      height: {
        button: 'var(--button-height)',
      },
      spacing: {
        'button-x': 'var(--button-padding-x)',
        'button-gap': 'var(--button-gap)',
      },
      borderRadius: {
        button: 'var(--button-border-radius)',
      },
      // colors: {
      //   'gray-light': 'var(--color-gray-light)',
      //   border: "hsl(var(--border))",
      //   input: "hsl(var(--input))",
      //   ring: "hsl(var(--ring))",
      //   background: "hsl(var(--background))",
      //   foreground: "hsl(var(--foreground))",
      //   primary: {
      //     DEFAULT: "hsl(var(--primary))",
      //     foreground: "hsl(var(--primary-foreground))",
      //   },
      //   secondary: {
      //     DEFAULT: "hsl(var(--secondary))",
      //     foreground: "hsl(var(--secondary-foreground))",
      //   },
      //   destructive: {
      //     DEFAULT: "hsl(var(--destructive))",
      //     foreground: "hsl(var(--destructive-foreground))",
      //   },
      //   muted: {
      //     DEFAULT: "hsl(var(--muted))",
      //     foreground: "hsl(var(--muted-foreground))",
      //   },
      //   accent: {
      //     DEFAULT: "hsl(var(--accent))",
      //     foreground: "hsl(var(--accent-foreground))",
      //   },
      //   popover: {
      //     DEFAULT: "hsl(var(--popover))",
      //     foreground: "hsl(var(--popover-foreground))",
      //   },
      //   card: {
      //     DEFAULT: "hsl(var(--card))",
      //     foreground: "hsl(var(--card-foreground))",
      //   },
      // },
      // borderRadius: {
      //   lg: "var(--radius)",
      //   md: "calc(var(--radius) - 2px)",
      //   sm: "calc(var(--radius) - 4px)",
      // },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      zIndex: {
        '200': '200',
        '201': '201',
        'max': '2147483647', // 最大値
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
