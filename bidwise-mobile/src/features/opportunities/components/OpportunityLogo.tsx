import { useEffect, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const FALLBACK_LOGO = require('../../../../assets/images/icon.png');

interface OpportunityLogoProps {
  logoUrl: string;
  borderColor?: string;
  cardColor?: string;
  size?: number;
}

export default function OpportunityLogo({
  logoUrl,
  borderColor,
  cardColor,
  size = 48,
}: OpportunityLogoProps) {
  const [imageError, setImageError] = useState(false);
  const themeBorderColor = useThemeColor({}, 'border');
  const themeCardColor = useThemeColor({}, 'card');

  useEffect(() => {
    setImageError(false);
  }, [logoUrl]);

  const useRemoteImage = Boolean(logoUrl) && !imageError;
  const resolvedBorderColor = borderColor ?? themeBorderColor;
  const resolvedCardColor = cardColor ?? themeCardColor;

  return (
    <View
      style={[
        styles.logoWrap,
        {
          width: size,
          height: size,
          borderColor: resolvedBorderColor,
          backgroundColor: resolvedCardColor,
          borderRadius: Math.round(size * 0.27),
        },
      ]}
    >
      <Image
        source={useRemoteImage ? { uri: logoUrl } : FALLBACK_LOGO}
        style={{ width: size - 2, height: size - 2 }}
        resizeMode="cover"
        onError={() => setImageError(true)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  logoWrap: {
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
});
