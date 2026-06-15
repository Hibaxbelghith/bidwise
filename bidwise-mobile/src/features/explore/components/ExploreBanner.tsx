import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

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

  return (
    <View style={styles.banner}>
      <View style={styles.bannerGlowTop} />
      <View style={styles.bannerGlowBottom} />

      <View style={styles.bannerTopRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{copy.eyebrow}</Text>
        </View>

      </View>

      <Text style={styles.title}>{copy.title}</Text>
      <Text style={styles.description}>{copy.description}</Text>

      <View style={styles.bannerFooter}>
        <View style={styles.bannerFooter}>
  {mode !== 'ready' && (
    <View>
      <Text style={styles.footerLabel}>BidWise mobile</Text>
      <Text style={styles.footerHint}>
        Explore first, then unlock stronger matches.
      </Text>
    </View>
  )}

  <TouchableOpacity
    activeOpacity={0.85}
    onPress={onPrimaryAction}
    style={styles.button}
  >
    <Text style={styles.buttonText}>{primaryLabel}</Text>
  </TouchableOpacity>
</View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    overflow: 'hidden',
    borderRadius: 22,
    padding: 18,
    backgroundColor: '#0f172a',
    gap: 10,
  },
  bannerGlowTop: {
    position: 'absolute',
    top: -30,
    right: -10,
    width: 140,
    height: 140,
    borderRadius: 999,
    backgroundColor: 'rgba(37, 99, 235, 0.36)',
  },
  bannerGlowBottom: {
    position: 'absolute',
    bottom: -40,
    left: -10,
    width: 150,
    height: 150,
    borderRadius: 999,
    backgroundColor: 'rgba(56, 189, 248, 0.18)',
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
    paddingVertical: 6,
    backgroundColor: 'rgba(255,255,255,0.10)',
  },
  badgeText: {
    color: '#dbeafe',
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  miniPill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: 'rgba(191, 219, 254, 0.14)',
  },
  miniPillText: {
    color: '#bfdbfe',
    fontSize: 11,
    fontWeight: '600',
  },
  title: {
    color: '#ffffff',
    fontSize: 22,
    lineHeight: 28,
    fontWeight: '700',
  },
  description: {
    color: '#cbd5e1',
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
  footerLabel: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
  },
  footerHint: {
    marginTop: 3,
    color: '#94a3b8',
    fontSize: 12,
  },
  button: {
    minHeight: 42,
    borderRadius: 14,
    paddingHorizontal: 16,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#1d4ed8',
    fontSize: 14,
    fontWeight: '700',
  },
});
