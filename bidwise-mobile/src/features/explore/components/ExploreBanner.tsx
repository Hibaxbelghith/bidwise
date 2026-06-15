import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { useThemeColor } from '@/src/shared/hooks/use-theme-color';

export type ExploreBannerMode = 'guest' | 'incomplete_profile' | 'missing_cv' | 'ready';

type ExploreBannerProps = {
  mode: ExploreBannerMode;
  onPrimaryAction: () => void;
  primaryLabel: string;
};

const COPY: Record<ExploreBannerMode, { eyebrow: string; title: string; description: string }> = {
  guest: {
    eyebrow: 'Unlock BidWise AI',
    title: 'Login to receive smarter matches and IA assistant',
    description: 'Sign in to activate recommendations, AI assistant, and application tracking.',
  },
  incomplete_profile: {
    eyebrow: 'Profile incomplete',
    title: 'Complete your profile to unlock stronger recommendations',
    description: 'Add your skills, preferences, and target roles so BidWise can rank the right opportunities for you.',
  },
  missing_cv: {
    eyebrow: 'Resume missing',
    title: 'Upload your CV and let AI sharpen your matches',
    description: 'A resume gives BidWise more context about your experience and helps improve recommendation quality.',
  },
  ready: {
    eyebrow: 'AI ready',
    title: 'Your personalized matches are waiting in For You',
    description: 'Explore everything, or jump straight into your recommendation feed for the best-ranked opportunities.',
  },
};

export default function ExploreBanner({
  mode,
  onPrimaryAction,
  primaryLabel,
}: ExploreBannerProps) {
  const copy = COPY[mode];
  const textColor = useThemeColor({}, 'text');
  const mutedColor = useThemeColor({}, 'muted');
  const tintColor = useThemeColor({}, 'tint');
  const borderColor = useThemeColor({}, 'border');
  const bannerColor = useThemeColor({ light: '#eff6ff', dark: '#111d32' }, 'card');
  const badgeColor = useThemeColor({ light: '#dbeafe', dark: '#1e3a5f' }, 'card');

  return (
    <View style={[styles.banner, { backgroundColor: bannerColor, borderColor }]}>
      <View style={[styles.bannerGlowTop, { backgroundColor: `${tintColor}16` }]} />
      <View style={[styles.bannerGlowBottom, { backgroundColor: `${tintColor}0D` }]} />

      <View style={styles.bannerTopRow}>
        <View style={[styles.badge, { backgroundColor: badgeColor }]}>
          <Ionicons name="sparkles-outline" size={14} color={tintColor} />
          <Text style={[styles.badgeText, { color: tintColor }]}>{copy.eyebrow}</Text>
        </View>
      </View>

      <Text style={[styles.title, { color: textColor }]}>{copy.title}</Text>
      <Text style={[styles.description, { color: mutedColor }]}>{copy.description}</Text>

      <View style={styles.bannerFooter}>
        {mode !== 'ready' ? (
          <Text style={[styles.footerHint, { color: mutedColor }]}>
            Explore now. Personalize when ready.
          </Text>
        ) : (
          <View />
        )}

        <TouchableOpacity
          activeOpacity={0.85}
          onPress={onPrimaryAction}
          style={[styles.button, { backgroundColor: tintColor }]}
          accessibilityRole="button"
          accessibilityLabel={primaryLabel}
        >
          <Text style={styles.buttonText}>{primaryLabel}</Text>
          <Ionicons name="arrow-forward" size={16} color="#ffffff" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    overflow: 'hidden',
    borderRadius: 16,
    borderWidth: 1,
    padding: 18,
    gap: 10,
  },
  bannerGlowTop: {
    position: 'absolute',
    top: -45,
    right: -30,
    width: 150,
    height: 150,
    borderRadius: 999,
  },
  bannerGlowBottom: {
    position: 'absolute',
    bottom: -65,
    left: -35,
    width: 145,
    height: 145,
    borderRadius: 999,
  },
  bannerTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  title: {
    maxWidth: 420,
    fontSize: 21,
    lineHeight: 27,
    fontWeight: '800',
  },
  description: {
    fontSize: 13,
    lineHeight: 20,
  },
  bannerFooter: {
    marginTop: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  footerHint: {
    flex: 1,
    fontSize: 12,
    lineHeight: 17,
  },
  button: {
    minHeight: 42,
    borderRadius: 10,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    justifyContent: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
});
