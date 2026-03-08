const { withAndroidManifest } = require('@expo/config-plugins');

/**
 * Expo config plugin that forces android:usesCleartextTraffic="true"
 * on the <application> tag in AndroidManifest.xml.
 *
 * This allows HTTP (non-HTTPS) requests on Android 9+ for development.
 */
module.exports = function withCleartextTraffic(config) {
  return withAndroidManifest(config, (modConfig) => {
    const mainApplication = modConfig.modResults.manifest.application[0];
    mainApplication.$['android:usesCleartextTraffic'] = 'true';
    return modConfig;
  });
};
