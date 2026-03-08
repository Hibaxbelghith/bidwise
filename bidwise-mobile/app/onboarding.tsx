import { useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  ScrollView,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { useRouter } from 'expo-router';

import { useThemeColor } from '@/hooks/use-theme-color';
import { updateProfile } from '@/src/services/auth';
import { useAuth } from '@/src/context/AuthContext';

// ── Step definitions ─────────────────────────────────────
const STEPS = [
  { title: 'What brings you to BidWise?', description: 'Select the types of opportunities you\'re looking for.' },
  { title: 'Where would you like to work?', description: 'Tell us your preferred location and work style.' },
  { title: 'Compensation expectations', description: 'What are your salary expectations? This stays private.' },
  { title: 'Work arrangement', description: 'What type of work arrangement do you prefer?' },
  { title: 'Target roles', description: 'What roles are you targeting? Add up to 5.' },
  { title: 'Profile visibility', description: 'Control who can see your profile.' },
];

// ── Options ──────────────────────────────────────────────
const OPPORTUNITY_OPTIONS = [
  { value: 'JOB', label: '💼  Jobs', desc: 'Full-time, part-time, contract', enabled: true },
  { value: 'INTERNSHIP', label: '🎓  Internships', desc: 'Internship & trainee programs', enabled: false },
  { value: 'RESEARCH', label: '📚  Research', desc: 'Academic & R&D opportunities', enabled: false },
  { value: 'FUNDING', label: '📈  Funding', desc: 'Grants, scholarships, funding', enabled: false },
];

const REMOTE_OPTIONS = [
  { value: 'ON_SITE', label: '🏢  On-site', desc: 'Work from the office' },
  { value: 'REMOTE', label: '🌐  Remote', desc: 'Work from anywhere' },
  { value: 'HYBRID', label: '🔄  Hybrid', desc: 'Mix of office & remote' },
];

const PERIOD_OPTIONS = [
  { value: 'YEARLY', label: 'per year' },
  { value: 'MONTHLY', label: 'per month' },
  { value: 'HOURLY', label: 'per hour' },
];

const EMPLOYMENT_OPTIONS = [
  { value: 'FULL_TIME', label: 'Full-time' },
  { value: 'PART_TIME', label: 'Part-time' },
  { value: 'CONTRACT', label: 'Contract' },
  { value: 'FREELANCE', label: 'Freelance' },
  { value: 'INTERNSHIP', label: 'Internship' },
];

const MAX_ROLES = 5;

// ── Initial data ─────────────────────────────────────────
interface OnboardingData {
  opportunity_types: string[];
  preferred_location: string;
  remote_preference: string | null;
  compensation_expectation: string;
  compensation_period: string | null;
  employment_types: string[];
  target_roles: string[];
  profile_visibility: boolean;
}

const initialData: OnboardingData = {
  opportunity_types: [],
  preferred_location: '',
  remote_preference: null,
  compensation_expectation: '',
  compensation_period: null,
  employment_types: [],
  target_roles: [],
  profile_visibility: true,
};

export default function OnboardingScreen() {
  const router = useRouter();
  const { loadUserProfile } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState<OnboardingData>(initialData);
  const [roleInput, setRoleInput] = useState('');

  const bg = useThemeColor({}, 'background');
  const text = useThemeColor({}, 'text');
  const muted = useThemeColor({}, 'muted');
  const tint = useThemeColor({}, 'tint');
  const card = useThemeColor({}, 'card');
  const border = useThemeColor({}, 'border');

  const step = STEPS[currentStep];
  const isLast = currentStep === STEPS.length - 1;

  // ── Helpers ────────────────────────────────────────────
  const toggleArray = (key: 'opportunity_types' | 'employment_types', value: string) => {
    setData((prev) => {
      const arr = prev[key];
      return { ...prev, [key]: arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value] };
    });
  };

  const addRole = () => {
    const trimmed = roleInput.trim();
    if (!trimmed || data.target_roles.length >= MAX_ROLES || data.target_roles.includes(trimmed)) return;
    setData((prev) => ({ ...prev, target_roles: [...prev.target_roles, trimmed] }));
    setRoleInput('');
  };

  const removeRole = (index: number) => {
    setData((prev) => ({ ...prev, target_roles: prev.target_roles.filter((_, i) => i !== index) }));
  };

  // ── Navigation ─────────────────────────────────────────
  const handleNext = async () => {
    if (isLast) {
      await finishOnboarding(false);
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) setCurrentStep((s) => s - 1);
  };

  const handleSkip = async () => {
    await finishOnboarding(true);
  };

  const finishOnboarding = async (skipData: boolean) => {
    try {
      setSaving(true);
      const payload: Record<string, unknown> = {
        onboarding_completed: true,
        last_onboarding_step: currentStep,
      };
      if (!skipData) {
        payload.opportunity_types = data.opportunity_types;
        payload.preferred_location = data.preferred_location || null;
        payload.remote_preference = data.remote_preference;
        payload.compensation_expectation = data.compensation_expectation ? parseInt(data.compensation_expectation, 10) : null;
        payload.compensation_period = data.compensation_period;
        payload.employment_types = data.employment_types;
        payload.target_roles = data.target_roles;
        payload.profile_visibility = data.profile_visibility;
      }
      await updateProfile(payload);
      await loadUserProfile();
      router.replace('/dashboard');
    } catch {
      router.replace('/dashboard');
    } finally {
      setSaving(false);
    }
  };

  // ── Step renderers ─────────────────────────────────────
  const renderStep0 = () => (
    <View style={styles.optionsGrid}>
      {OPPORTUNITY_OPTIONS.map((opt) => {
        const selected = data.opportunity_types.includes(opt.value);
        return (
          <TouchableOpacity
            key={opt.value}
            disabled={!opt.enabled}
            onPress={() => toggleArray('opportunity_types', opt.value)}
            activeOpacity={0.7}
            style={[
              styles.cardOption,
              { borderColor: selected ? tint : border, backgroundColor: selected ? tint + '15' : card },
              !opt.enabled && styles.disabledCard,
            ]}
          >
            {!opt.enabled && (
              <View style={[styles.soonBadge, { backgroundColor: border }]}>
                <Text style={[styles.soonBadgeText, { color: muted }]}>Soon</Text>
              </View>
            )}
            <Text style={styles.cardEmoji}>{opt.label.slice(0, 3)}</Text>
            <Text style={[styles.cardLabel, { color: opt.enabled ? text : muted }]}>{opt.label.slice(3)}</Text>
            <Text style={[styles.cardDesc, { color: muted }]}>{opt.desc}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );

  const renderStep1 = () => (
    <View style={{ gap: 24 }}>
      <View style={{ gap: 8 }}>
        <Text style={[styles.label, { color: text }]}>📍  Preferred location</Text>
        <TextInput
          style={[styles.input, { borderColor: border, color: text, backgroundColor: card }]}
          placeholder="e.g. Paris, London, New York"
          placeholderTextColor={muted}
          value={data.preferred_location}
          onChangeText={(v) => setData((p) => ({ ...p, preferred_location: v }))}
        />
      </View>
      <View style={{ gap: 8 }}>
        <Text style={[styles.label, { color: text }]}>Work style</Text>
        <View style={styles.remoteRow}>
          {REMOTE_OPTIONS.map((opt) => {
            const selected = data.remote_preference === opt.value;
            return (
              <TouchableOpacity
                key={opt.value}
                onPress={() => setData((p) => ({ ...p, remote_preference: selected ? null : opt.value }))}
                activeOpacity={0.7}
                style={[styles.remoteCard, { borderColor: selected ? tint : border, backgroundColor: selected ? tint + '15' : card }]}
              >
                <Text style={styles.cardEmoji}>{opt.label.slice(0, 3)}</Text>
                <Text style={[styles.remoteLabel, { color: text }]}>{opt.label.slice(3)}</Text>
                <Text style={[styles.cardDesc, { color: muted }]}>{opt.desc}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    </View>
  );

  const renderStep2 = () => (
    <View style={{ gap: 16 }}>
      <Text style={[styles.label, { color: text }]}>Desired minimum compensation</Text>
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}>
          <TextInput
            style={[styles.input, { borderColor: border, color: text, backgroundColor: card }]}
            placeholder="e.g. 55000"
            placeholderTextColor={muted}
            keyboardType="numeric"
            value={data.compensation_expectation}
            onChangeText={(v) => setData((p) => ({ ...p, compensation_expectation: v.replace(/[^0-9]/g, '') }))}
          />
        </View>
      </View>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {PERIOD_OPTIONS.map((opt) => {
          const selected = data.compensation_period === opt.value;
          return (
            <TouchableOpacity
              key={opt.value}
              onPress={() => setData((p) => ({ ...p, compensation_period: selected ? null : opt.value }))}
              activeOpacity={0.7}
              style={[styles.pill, { borderColor: selected ? tint : border, backgroundColor: selected ? tint : 'transparent' }]}
            >
              <Text style={[styles.pillText, { color: selected ? '#fff' : text }]}>{opt.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
      <Text style={[styles.hint, { color: muted }]}>Your compensation expectations are private and never shared.</Text>
    </View>
  );

  const renderStep3 = () => (
    <View style={{ gap: 16 }}>
      <View style={styles.pillsWrap}>
        {EMPLOYMENT_OPTIONS.map((opt) => {
          const selected = data.employment_types.includes(opt.value);
          return (
            <TouchableOpacity
              key={opt.value}
              onPress={() => toggleArray('employment_types', opt.value)}
              activeOpacity={0.7}
              style={[styles.pill, { borderColor: selected ? tint : border, backgroundColor: selected ? tint : 'transparent' }]}
            >
              <Text style={[styles.pillText, { color: selected ? '#fff' : text }]}>{opt.label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
      {data.employment_types.length > 0 && (
        <Text style={[styles.hint, { color: muted }]}>{data.employment_types.length} selected</Text>
      )}
    </View>
  );

  const renderStep4 = () => (
    <View style={{ gap: 16 }}>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <TextInput
          style={[styles.input, { flex: 1, borderColor: border, color: text, backgroundColor: card }]}
          placeholder="e.g. Frontend Developer"
          placeholderTextColor={muted}
          value={roleInput}
          onChangeText={setRoleInput}
          onSubmitEditing={addRole}
          editable={data.target_roles.length < MAX_ROLES}
        />
        <TouchableOpacity
          onPress={addRole}
          activeOpacity={0.7}
          disabled={!roleInput.trim() || data.target_roles.length >= MAX_ROLES}
          style={[styles.addBtn, { backgroundColor: tint, opacity: roleInput.trim() ? 1 : 0.4 }]}
        >
          <Text style={{ color: '#fff', fontSize: 20, fontWeight: '700' }}>+</Text>
        </TouchableOpacity>
      </View>
      {data.target_roles.length > 0 && (
        <View style={styles.pillsWrap}>
          {data.target_roles.map((role, i) => (
            <View key={i} style={[styles.roleBadge, { backgroundColor: tint + '20', borderColor: tint }]}>
              <Text style={[styles.roleBadgeText, { color: tint }]}>{role}</Text>
              <TouchableOpacity onPress={() => removeRole(i)} hitSlop={8}>
                <Text style={{ color: tint, fontSize: 16, fontWeight: '700' }}>✕</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      )}
      <Text style={[styles.hint, { color: muted }]}>{data.target_roles.length}/{MAX_ROLES} roles — press Enter or + to add</Text>
    </View>
  );

  const renderStep5 = () => (
    <TouchableOpacity
      onPress={() => setData((p) => ({ ...p, profile_visibility: !p.profile_visibility }))}
      activeOpacity={0.8}
      style={[styles.visibilityCard, { borderColor: data.profile_visibility ? tint : border, backgroundColor: data.profile_visibility ? tint + '10' : card }]}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
        <View style={[styles.visIcon, { backgroundColor: data.profile_visibility ? tint + '25' : border }]}>
          <Text style={{ fontSize: 22 }}>{data.profile_visibility ? '👁️' : '🙈'}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={[styles.visTitle, { color: text }]}>Allow recruiters to view my profile</Text>
          <Text style={[styles.visDesc, { color: muted }]}>
            {data.profile_visibility
              ? 'Your profile is visible to recruiters and hiring managers.'
              : 'Your profile is hidden. Only you can see it.'}
          </Text>
        </View>
        <Switch
          value={data.profile_visibility}
          onValueChange={(v) => setData((p) => ({ ...p, profile_visibility: v }))}
          trackColor={{ false: border, true: tint }}
          thumbColor="#fff"
        />
      </View>
    </TouchableOpacity>
  );

  const stepRenderers = [renderStep0, renderStep1, renderStep2, renderStep3, renderStep4, renderStep5];

  // ── Render ─────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      {/* Progress bar */}
      <View style={styles.progressContainer}>
        {STEPS.map((_, index) => (
          <View
            key={index}
            style={[
              styles.progressDot,
              { backgroundColor: index <= currentStep ? tint : border, flex: 1 },
            ]}
          />
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={[styles.stepLabel, { color: tint }]}>Step {currentStep + 1} of {STEPS.length}</Text>
        <Text style={[styles.title, { color: text }]}>{step.title}</Text>
        <Text style={[styles.subtitle, { color: muted }]}>{step.description}</Text>

        {stepRenderers[currentStep]()}
      </ScrollView>

      {/* Footer */}
      <View style={styles.footer}>
        {saving && <ActivityIndicator color={tint} style={{ marginBottom: 8 }} />}
        <View style={styles.footerRow}>
          {currentStep > 0 ? (
            <TouchableOpacity style={[styles.secondaryButton, { borderColor: border }]} onPress={handleBack} activeOpacity={0.7}>
              <Text style={[styles.secondaryButtonText, { color: text }]}>Back</Text>
            </TouchableOpacity>
          ) : (
            <View />
          )}

          <TouchableOpacity
            style={[styles.primaryButton, { backgroundColor: tint }]}
            onPress={handleNext}
            activeOpacity={0.8}
            disabled={saving}
          >
            <Text style={styles.primaryButtonText}>{isLast ? 'Finish' : 'Next'}</Text>
          </TouchableOpacity>
        </View>
        {/* Skip always visible */}
        <TouchableOpacity onPress={handleSkip} activeOpacity={0.7} style={styles.skipContainer} disabled={saving}>
          <Text style={[styles.skipText, { color: muted }]}>Skip for now</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60 },
  progressContainer: { flexDirection: 'row', gap: 6, paddingHorizontal: 32, marginBottom: 32 },
  progressDot: { height: 4, borderRadius: 2 },
  scrollContent: { paddingHorizontal: 32, paddingBottom: 32, flexGrow: 1 },
  stepLabel: { fontSize: 14, fontWeight: '600', marginBottom: 8 },
  title: { fontSize: 26, fontWeight: '700', marginBottom: 8 },
  subtitle: { fontSize: 15, lineHeight: 22, marginBottom: 32 },

  // Cards grid (step 0)
  optionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  cardOption: { width: '47%', borderWidth: 1.5, borderRadius: 14, padding: 18, alignItems: 'center', gap: 4 },
  disabledCard: { opacity: 0.45 },
  soonBadge: { position: 'absolute', top: 8, right: 8, borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  soonBadgeText: { fontSize: 10, fontWeight: '600' },
  cardEmoji: { fontSize: 24, marginBottom: 4 },
  cardLabel: { fontSize: 14, fontWeight: '600', textAlign: 'center' },
  cardDesc: { fontSize: 11, textAlign: 'center', lineHeight: 15 },

  // Remote (step 1)
  remoteRow: { flexDirection: 'row', gap: 10 },
  remoteCard: { flex: 1, borderWidth: 1.5, borderRadius: 12, padding: 14, alignItems: 'center', gap: 4 },
  remoteLabel: { fontSize: 13, fontWeight: '600', textAlign: 'center' },

  // Input
  label: { fontSize: 15, fontWeight: '600' },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15 },
  hint: { fontSize: 12 },

  // Pills (step 2, 3)
  pill: { borderWidth: 1.5, borderRadius: 50, paddingHorizontal: 18, paddingVertical: 10 },
  pillText: { fontSize: 14, fontWeight: '600' },
  pillsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },

  // Roles (step 4)
  addBtn: { width: 46, height: 46, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  roleBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderRadius: 50, paddingHorizontal: 14, paddingVertical: 8 },
  roleBadgeText: { fontSize: 14, fontWeight: '500' },

  // Visibility (step 5)
  visibilityCard: { borderWidth: 1.5, borderRadius: 16, padding: 20 },
  visIcon: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  visTitle: { fontSize: 15, fontWeight: '600', marginBottom: 4 },
  visDesc: { fontSize: 13, lineHeight: 18 },

  // Footer
  footer: { paddingHorizontal: 32, paddingBottom: 36, paddingTop: 12 },
  footerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  secondaryButton: { borderWidth: 1, borderRadius: 12, paddingVertical: 12, paddingHorizontal: 24 },
  secondaryButtonText: { fontSize: 16, fontWeight: '600' },
  primaryButton: { borderRadius: 12, paddingVertical: 12, paddingHorizontal: 32 },
  primaryButtonText: { color: '#ffffff', fontSize: 16, fontWeight: '600' },
  skipContainer: { alignItems: 'center', marginTop: 16 },
  skipText: { fontSize: 15 },
});
