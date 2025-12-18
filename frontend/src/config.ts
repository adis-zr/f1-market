/**
 * Application Branding Configuration
 *
 * This file contains all branding-related constants for the application.
 * Update these values to rebrand the application for different sports or markets.
 */

export const appConfig = {
  /**
   * The name of the application
   */
  name: 'GridStock',

  /**
   * Short description used on login and other public-facing pages
   */
  description: 'Trade on racing outcomes',

  /**
   * Login page configuration
   */
  login: {
    title: 'GridStock',
    emailStepDescription: 'Enter your email to receive a login code',
    otpStepDescription: 'Enter the 6-digit code sent to your email',
  },

  /**
   * Logo and icon configuration
   * Can be extended to include logo URLs, favicons, etc.
   */
  branding: {
    // Future: Add logo paths, colors, etc.
    // logoUrl: '/assets/logo.png',
    // iconUrl: '/assets/icon.png',
    // primaryColor: '#e10600',
  },
} as const;

/**
 * Type-safe access to app config
 */
export type AppConfig = typeof appConfig;
