import { useEffect, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';

const FALLBACK_LOGO = require('../../../../assets/images/icon.png');

interface OpportunityLogoProps {
  logoUrl: string;
  borderColor: string;
  cardColor: string;
  size?: number;
}

export default function OpportunityLogo({
  logoUrl,
  borderColor,
  cardColor,
  size = 48,
}: OpportunityLogoProps) {
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    setImageError(false);
  }, [logoUrl]);

  const useRemoteImage = Boolean(logoUrl) && !imageError;

  return (
    <View
      style={[
        styles.logoWrap,
        {
          width: size,
          height: size,
          borderColor,
          backgroundColor: cardColor,
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
