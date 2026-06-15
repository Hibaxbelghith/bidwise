import { Ionicons } from '@expo/vector-icons';
import { Image, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

const bidwiseLogo = require('@/assets/images/bidwise-logo-web.png');

type AppHeaderProps = {
  title: string;
  showSearch?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onMenuPress?: () => void;
  onBackPress?: () => void;
  showBackButton?: boolean;
  placeholder?: string;
  backgroundColor: string;
  borderColor: string;
  cardColor: string;
  textColor: string;
  mutedColor: string;
  tintColor: string;
};

export default function AppHeader({
  title,
  showSearch = false,
  searchValue = '',
  onSearchChange,
  onMenuPress,
  onBackPress,
  showBackButton = false,
  placeholder = 'Search opportunities',
  backgroundColor,
  borderColor,
  cardColor,
  textColor,
  mutedColor,
  tintColor,
}: AppHeaderProps) {
  return (
    <View style={[styles.wrapper, { backgroundColor, borderColor }]}>
      <View style={styles.topRow}>
        <View style={styles.leftSlot}>
          {showBackButton ? (
            <TouchableOpacity
              accessibilityLabel="Go back"
              accessibilityRole="button"
              activeOpacity={0.8}
              onPress={onBackPress}
              style={[styles.iconButton, { borderColor, backgroundColor: cardColor }]}
            >
              <Ionicons name="arrow-back" size={18} color={textColor} />
            </TouchableOpacity>
          ) : (
            <View style={styles.brandRow}>
              <Image source={bidwiseLogo} style={styles.brandLogo} resizeMode="contain" />
            </View>
          )}
        </View>

        <Text numberOfLines={1} style={[styles.title, { color: textColor }]}>
          {title}
        </Text>

        {onMenuPress ? (
          <TouchableOpacity
            accessibilityLabel="Open menu"
            accessibilityRole="button"
            activeOpacity={0.8}
            onPress={onMenuPress}
            style={[styles.iconButton, { borderColor, backgroundColor: cardColor }]}
          >
            <Ionicons name="menu" size={20} color={textColor} />
          </TouchableOpacity>
        ) : (
          <View style={styles.rightSlot} />
        )}
      </View>

      {showSearch ? (
        <View style={[styles.searchRow, { backgroundColor: cardColor, borderColor }]}>
          <Ionicons name="search" size={16} color={mutedColor} />
          <TextInput
            value={searchValue}
            onChangeText={onSearchChange}
            placeholder={placeholder}
            placeholderTextColor={mutedColor}
            style={[styles.searchInput, { color: textColor }]}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderBottomWidth: 1,
    paddingTop: 52,
    paddingHorizontal: 16,
    paddingBottom: 12,
    gap: 12,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  leftSlot: {
    minWidth: 72,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandLogo: {
    width: 50,
    height: 50,
  },
  brandText: {
    fontSize: 16,
    fontWeight: '700',
  },
  title: {
    flex: 1,
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
  },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 12,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rightSlot: {
    width: 40,
    height: 40,
  },
  searchRow: {
    minHeight: 44,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    paddingVertical: 10,
  },
});
