import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Image, StyleSheet } from 'react-native';

const logo = require('@/assets/images/bidwise-logo-web.png');

type AppLaunchSplashProps = {
  onFinish?: () => void;
};

export default function AppLaunchSplash({ onFinish }: AppLaunchSplashProps) {
  const [visible, setVisible] = useState(true);
  const opacity = useRef(new Animated.Value(1)).current;
  const logoProgress = useRef(new Animated.Value(0)).current;
  const glowProgress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.sequence([
      Animated.parallel([
        Animated.timing(logoProgress, {
          toValue: 1,
          duration: 900,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(glowProgress, {
          toValue: 1,
          duration: 1100,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ]),
      Animated.delay(180),
      Animated.timing(opacity, {
        toValue: 0,
        duration: 420,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]);

    animation.start(({ finished }) => {
      if (!finished) return;
      setVisible(false);
      onFinish?.();
    });

    return () => animation.stop();
  }, [glowProgress, logoProgress, onFinish, opacity]);

  if (!visible) return null;

  return (
    <Animated.View
      pointerEvents="auto"
      style={[StyleSheet.absoluteFill, styles.container, { opacity }]}
    >
      <Animated.View
        style={[
          styles.glow,
          {
            opacity: glowProgress.interpolate({
              inputRange: [0, 1],
              outputRange: [0.2, 0.7],
            }),
            transform: [{
              scale: glowProgress.interpolate({
                inputRange: [0, 1],
                outputRange: [0.75, 1.15],
              }),
            }],
          },
        ]}
      />

      <Animated.View
        style={[
          styles.logoWrap,
          {
            opacity: logoProgress,
            transform: [
              {
                scale: logoProgress.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.82, 1],
                }),
              },
              {
                translateY: logoProgress.interpolate({
                  inputRange: [0, 1],
                  outputRange: [10, 0],
                }),
              },
            ],
          },
        ]}
      >
        <Image source={logo} style={styles.logo} resizeMode="contain" />
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    zIndex: 999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff',
  },
  glow: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: '#dbeafe',
  },
  logoWrap: {
    width: 190,
    height: 92,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    width: 176,
    height: 76,
  },
});
