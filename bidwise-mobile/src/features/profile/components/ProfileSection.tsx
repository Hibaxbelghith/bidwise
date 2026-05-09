import { memo, useState, type ReactNode } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type ProfileSectionProps = {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  children: ReactNode;
  colors: {
    card: string;
    border: string;
    text: string;
    muted: string;
  };
};

function ProfileSection({
  title,
  description,
  defaultOpen = true,
  children,
  colors,
}: ProfileSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <View style={[styles.section, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <TouchableOpacity
        activeOpacity={0.75}
        onPress={() => setOpen((value) => !value)}
        style={styles.header}
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
      >
        <View style={styles.headerText}>
          <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
          {description ? <Text style={[styles.description, { color: colors.muted }]}>{description}</Text> : null}
        </View>
        <Text style={[styles.chevron, { color: colors.muted }]}>{open ? '−' : '+'}</Text>
      </TouchableOpacity>

      {open ? <View style={styles.body}>{children}</View> : null}
    </View>
  );
}

export default memo(ProfileSection);

const styles = StyleSheet.create({
  section: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  headerText: {
    flex: 1,
    gap: 4,
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
  },
  description: {
    fontSize: 13,
    lineHeight: 18,
  },
  chevron: {
    fontSize: 24,
    fontWeight: '600',
    lineHeight: 28,
  },
  body: {
    gap: 16,
    paddingTop: 16,
  },
});
