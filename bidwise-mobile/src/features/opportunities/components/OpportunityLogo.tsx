import { useEffect, useState } from 'react';
import { Image, type ImageSourcePropType, StyleSheet, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

const FALLBACK_LOGO = require('../../../../assets/images/icon.png');
const SOURCE_LOGOS = {
  haicop: require('../../../../assets/images/sources/haicop.png'),
  emploiTunisie: require('../../../../assets/images/sources/emploiTunisie.png'),
  keejob: require('../../../../assets/images/sources/keejob_logo.jpg'),
  linkedin: require('../../../../assets/images/sources/linkedin_icon.webp'),
} as const;

interface OpportunityLogoProps {
  logoUrl: string;
  sourceName?: string | null;
  borderColor?: string;
  cardColor?: string;
  size?: number;
}

function getSourceLogo(sourceName?: string | null): ImageSourcePropType | null {
  const normalized = String(sourceName || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
  if (!normalized) return null;
  if (
    normalized.includes('marchespublics') ||
    normalized.includes('marches publics') ||
    normalized.includes('marche public') ||
    normalized.includes('haicop') ||
    normalized === 'projet'
  ) {
    return SOURCE_LOGOS.haicop;
  }
  if (normalized.includes('emploitunisie')) return SOURCE_LOGOS.emploiTunisie;
  if (normalized.includes('keejob')) return SOURCE_LOGOS.keejob;
  if (normalized.includes('linkedin')) return SOURCE_LOGOS.linkedin;
  return null;
}

export default function OpportunityLogo({
  logoUrl,
  sourceName,
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

  const localSourceLogo = getSourceLogo(sourceName);
  const useRemoteImage = Boolean(logoUrl) && !imageError;
  const imageSource = useRemoteImage ? { uri: logoUrl } : localSourceLogo || FALLBACK_LOGO;
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
        source={imageSource}
        style={{ width: size - 2, height: size - 2 }}
        resizeMode={useRemoteImage ? 'cover' : 'contain'}
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
