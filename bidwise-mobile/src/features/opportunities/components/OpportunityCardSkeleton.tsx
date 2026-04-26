import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

interface OpportunityCardSkeletonProps {
  cardColor: string;
  borderColor: string;
  skeletonBase: string;
  skeletonSoft: string;
}

export default function OpportunityCardSkeleton({
  cardColor,
  borderColor,
  skeletonBase,
  skeletonSoft,
}: OpportunityCardSkeletonProps) {
  const opacity = useRef(new Animated.Value(0.55)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 650,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.55,
          duration: 650,
          useNativeDriver: true,
        }),
      ]),
    );

    loop.start();

    return () => {
      loop.stop();
    };
  }, [opacity]);

  return (
    <Animated.View style={{ opacity }}>
      <View style={[styles.card, { backgroundColor: cardColor, borderColor }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.logoWrap, { borderColor, backgroundColor: cardColor }]}>
            <View
              style={[
                styles.skeletonBlock,
                { width: 40, height: 40, borderRadius: 12, backgroundColor: skeletonBase },
              ]}
            />
          </View>

          <View style={[styles.cardHeaderTextWrap, { gap: 8 }]}>
            <View
              style={[
                styles.skeletonBlock,
                { width: '90%', height: 16, backgroundColor: skeletonBase },
              ]}
            />
            <View
              style={[
                styles.skeletonBlock,
                { width: '60%', height: 12, backgroundColor: skeletonSoft },
              ]}
            />
          </View>
        </View>

        <View style={styles.chipsRow}>
          <View
            style={[
              styles.skeletonBlock,
              { width: 90, height: 26, borderRadius: 999, backgroundColor: skeletonSoft },
            ]}
          />
          <View
            style={[
              styles.skeletonBlock,
              { width: 80, height: 26, borderRadius: 999, backgroundColor: skeletonSoft },
            ]}
          />
          <View
            style={[
              styles.skeletonBlock,
              { width: 100, height: 26, borderRadius: 999, backgroundColor: skeletonSoft },
            ]}
          />
        </View>

        <View
          style={[
            styles.skeletonBlock,
            { width: '55%', height: 12, marginBottom: 8, backgroundColor: skeletonSoft },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '45%', height: 12, marginBottom: 10, backgroundColor: skeletonSoft },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '95%', height: 12, marginBottom: 6, backgroundColor: skeletonSoft },
          ]}
        />
        <View
          style={[
            styles.skeletonBlock,
            { width: '70%', height: 12, backgroundColor: skeletonSoft },
          ]}
        />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  logoWrap: {
    width: 48,
    height: 48,
    borderRadius: 13,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  cardHeaderTextWrap: {
    flex: 1,
  },
  chipsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  skeletonBlock: {
    borderRadius: 8,
  },
});
