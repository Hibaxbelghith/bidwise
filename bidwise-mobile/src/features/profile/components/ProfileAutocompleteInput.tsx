import { memo, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

import { useProfileAutocomplete } from '@/src/features/profile/hooks/useProfileAutocomplete';
import type { ProfileSuggestion, ProfileTermType } from '@/src/features/profile/types';
import {
  formatBusinessFamilyLabels,
  normalizeBusinessFamilyValues,
  isGarbageSkillInput,
  isInterestTermRejected,
  isKnownSkillTerm,
  isKnownRoleTerm,
  isRoleTermRejected,
  normalizeTermKey,
  normalizeTextList,
} from '@/src/features/profile/utils/profileValidation';

type ProfileAutocompleteInputProps = {
  label: string;
  termType: ProfileTermType;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder: string;
  maxItems?: number;
  emptyText?: string;
  colors: {
    tint: string;
    border: string;
    text: string;
    muted: string;
    card: string;
  };
};

const suggestionValue = (suggestion: ProfileSuggestion) => suggestion.value || suggestion.label || '';

function ProfileAutocompleteInput({
  label,
  termType,
  value,
  onChange,
  placeholder,
  maxItems = 20,
  emptyText = 'Not specified',
  colors,
}: ProfileAutocompleteInputProps) {
  const [query, setQuery] = useState('');
  const [message, setMessage] = useState('');
  const { suggestions, loading, error } = useProfileAutocomplete(termType, query, 8);
  const isRole = termType === 'role';
  const isSkill = termType === 'skill';
  const isInterest = termType === 'interest';

  const selected = useMemo(() => {
    const seen = new Set<string>();
    return normalizeTextList(value)
      .map((item) => {
        if (isInterest) return formatBusinessFamilyLabels([item])[0] || item;
        return item;
      })
      .filter((item) => {
        const key = normalizeTermKey(item);
        if (!item || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
  }, [isInterest, value]);

  const addCanonical = (rawValue: string) => {
    const canonical = rawValue.trim().replace(/\s+/g, ' ');
    if (!canonical || selected.length >= maxItems) return;

    if (isRole && isRoleTermRejected(canonical)) {
      setMessage(
        isKnownSkillTerm(canonical)
          ? `${canonical} is a skill, not a role.`
          : isKnownRoleTerm(canonical)
            ? `${canonical} is already normalized.`
            : 'Enter a specific role title.',
      );
      return;
    }
    if (isInterest && isInterestTermRejected(canonical)) {
      setMessage(
        isKnownSkillTerm(canonical)
          ? `${canonical} is a skill, not a sector.`
          : 'Choose a valid professional sector.',
      );
      return;
    }
    if (isSkill && isGarbageSkillInput(canonical)) {
      setMessage('Enter a recognizable skill name.');
      return;
    }

    const key = normalizeTermKey(canonical);
    if (selected.some((item) => normalizeTermKey(item) === key)) {
      setMessage(`${canonical} is already added.`);
      setQuery('');
      return;
    }

    onChange([...selected, canonical]);
    setQuery('');
    setMessage('');
  };

  const addFromInput = () => {
    const trimmed = query.trim();
    if (!trimmed || selected.length >= maxItems) return;

    const queryKey = normalizeTermKey(trimmed);
    const exactSuggestion = suggestions.find((suggestion) => {
      const valueKey = normalizeTermKey(suggestionValue(suggestion));
      return valueKey === queryKey;
    });

    if (exactSuggestion) {
      const valueToAdd = suggestionValue(exactSuggestion);
      if (isSkill) addCanonical(valueToAdd);
      else if (isInterest) {
        const canonicalInterest = normalizeBusinessFamilyValues([valueToAdd])[0] || valueToAdd;
        addCanonical(canonicalInterest);
      } else addCanonical(valueToAdd);
      return;
    }

    if (isSkill) {
      addCanonical(trimmed);
      return;
    }
    if (isInterest) {
      const canonicalInterest = normalizeBusinessFamilyValues([trimmed])[0] || trimmed;
      addCanonical(canonicalInterest);
      return;
    }
    addCanonical(trimmed);
  };

  const removeItem = (item: string) => {
    onChange(selected.filter((selectedItem) => selectedItem !== item));
  };

  return (
    <View style={styles.container}>
      <Text style={[styles.label, { color: colors.text }]}>{label}</Text>
      <View style={styles.inputRow}>
        <TextInput
          value={query}
          onChangeText={(text) => {
            setQuery(text);
            setMessage('');
          }}
          onSubmitEditing={addFromInput}
          placeholder={placeholder}
          placeholderTextColor={colors.muted}
          autoCapitalize="none"
          autoCorrect={false}
          editable={selected.length < maxItems}
          style={[styles.input, { backgroundColor: colors.card, borderColor: colors.border, color: colors.text }]}
        />
        <TouchableOpacity
          activeOpacity={0.75}
          onPress={addFromInput}
          disabled={!query.trim() || selected.length >= maxItems}
          style={[styles.addButton, { backgroundColor: colors.tint, opacity: query.trim() ? 1 : 0.4 }]}
          accessibilityRole="button"
        >
          {loading ? <ActivityIndicator size="small" color="#fff" /> : <Text style={styles.addText}>+</Text>}
        </TouchableOpacity>
      </View>

      {suggestions.length ? (
        <View style={styles.suggestionWrap}>
          {suggestions.map((suggestion) => {
            const item = suggestionValue(suggestion);
            if (!item) return null;
            return (
              <TouchableOpacity
                key={`${suggestion.id}-${item}`}
                activeOpacity={0.75}
                onPress={() =>
                  addCanonical(
                    isInterest
                      ? (normalizeBusinessFamilyValues([item])[0] || item)
                      : item,
                  )
                }
                style={[styles.suggestionChip, { borderColor: colors.border, backgroundColor: colors.card }]}
              >
                <Text style={[styles.suggestionText, { color: colors.text }]}>{item}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      ) : null}

      {message || error ? <Text style={[styles.message, { color: '#b45309' }]}>{message || error}</Text> : null}

      {selected.length ? (
        <View style={styles.selectedWrap}>
          {selected.map((item) => (
            <View key={item} style={[styles.selectedChip, { backgroundColor: colors.tint + '18', borderColor: colors.tint }]}>
              <Text style={[styles.selectedText, { color: colors.tint }]}>{item}</Text>
              <TouchableOpacity onPress={() => removeItem(item)} hitSlop={10}>
                <Text style={[styles.removeText, { color: colors.tint }]}>×</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      ) : (
        <Text style={[styles.emptyText, { color: colors.muted }]}>{emptyText}</Text>
      )}
    </View>
  );
}

export default memo(ProfileAutocompleteInput);

const styles = StyleSheet.create({
  container: {
    gap: 10,
  },
  label: {
    fontSize: 15,
    fontWeight: '700',
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  input: {
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    fontSize: 15,
    paddingHorizontal: 14,
    paddingVertical: 11,
  },
  addButton: {
    alignItems: 'center',
    borderRadius: 12,
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  addText: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
  },
  suggestionWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  suggestionChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  suggestionText: {
    fontSize: 13,
    fontWeight: '600',
  },
  selectedWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  selectedChip: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  selectedText: {
    fontSize: 13,
    fontWeight: '700',
  },
  removeText: {
    fontSize: 16,
    fontWeight: '800',
  },
  message: {
    fontSize: 12,
    lineHeight: 17,
  },
  emptyText: {
    fontSize: 13,
    fontStyle: 'italic',
  },
});
