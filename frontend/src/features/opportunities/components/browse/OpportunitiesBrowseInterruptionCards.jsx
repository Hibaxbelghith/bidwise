import { Link } from 'react-router-dom';
import { ArrowRight, FileText, SearchCheck, Sparkles, UserCheck } from 'lucide-react';

import { Button } from '../../../../components/ui/button.jsx';
import { useLanguage } from '../../../../i18n/LanguageContext.jsx';
import {
  getProfileCompletionScore,
  hasActiveResume,
} from '../../utils/recommendationUtils.js';

const normalizeList = (value) => (Array.isArray(value) ? value.filter(Boolean) : []);

const isCallsForTenderOnlyProfile = (user) => {
  const types = normalizeList(user?.profil?.opportunity_types).map((item) => String(item).trim().toUpperCase());
  return types.length === 1 && types[0] === 'CALLS_FOR_TENDER';
};

const getProfileStatus = (user) => {
  const profile = user?.profil || {};
  const completionScore = getProfileCompletionScore(user);
  const skills = normalizeList(profile.competences);
  const targetRoles = normalizeList(profile.target_roles);

  return {
    completionScore,
    hasResume: hasActiveResume(user),
    hasMissingSkills: skills.length === 0,
    hasMissingTargetRoles: targetRoles.length === 0,
    isProfileIncomplete:
      completionScore < 80 ||
      (completionScore < 100 && (skills.length === 0 || targetRoles.length === 0)),
    isProfileReady: completionScore >= 80 && skills.length > 0 && targetRoles.length > 0,
  };
};

export const buildBrowseInterruptionCards = ({ isUserAuthenticated, user, onShowMatches }) => {
  if (!isUserAuthenticated) {
    return [
      {
        key: 'guest',
        icon: Sparkles,
        color: 'blue', // All cards now use 'blue'
        title: 'Find opportunities that actually match you.',
        description:
          'Create a free profile to unlock AI-powered recommendations and personalized opportunity matching.',
        ctaLabel: 'Get Personalized Matches',
        to: '/login',
      },
    ];
  }

  if (isCallsForTenderOnlyProfile(user)) {
    return [];
  }

  const status = getProfileStatus(user);
  const cards = [];

  if (!status.hasResume) {
    cards.push({
      key: 'resume',
      icon: FileText,
      color: 'blue', // Changed from 'emerald' to 'blue'
      title: 'Upload your resume to improve recommendation accuracy.',
      description:
        'BidWise AI can analyze your resume and deliver stronger personalized matches.',
      ctaLabel: 'Upload Resume',
      to: '/profile',
    });
  }

  if (status.isProfileIncomplete) {
    const missingParts = [];
    if (status.hasMissingTargetRoles) missingParts.push('target roles');
    if (status.hasMissingSkills) missingParts.push('skills');

    cards.push({
      key: 'profile',
      icon: UserCheck,
      color: 'blue', // Changed from 'amber' to 'blue'
      title: 'Your profile needs more recommendation signals.',
      description: missingParts.length
        ? `Add ${missingParts.join(' and ')} to unlock more relevant opportunities.`
        : 'Review your profile to unlock more relevant opportunities.',
      ctaLabel: 'Review Profile',
      to: '/profile',
    });
  }

  if (status.isProfileReady && status.hasResume && typeof onShowMatches === 'function') {
    cards.push({
      key: 'matches',
      icon: SearchCheck,
      color: 'blue',
      title: 'Search smarter, not harder.',
      description: 'Get a personalized list of opportunities matched to your profile.',
      ctaLabel: 'See Your Matches',
      onClick: onShowMatches,
    });
  }

  return cards;
};

// Simplified card styles - only blue now
const cardStyles = {
  blue: {
    gradient: 'from-blue-600 to-indigo-500',
    soft: 'from-blue-50 to-indigo-100',
    icon: 'text-blue-600',
    glow: 'bg-blue-500/5 group-hover:bg-blue-500/10',
    shadow: 'shadow-blue-500/20 hover:shadow-blue-500/30',
  },
};

const OpportunitiesBrowseInterruptionCard = ({ card }) => {
  const { t } = useLanguage();
  const Icon = card.icon;
  const styles = cardStyles.blue; // Always use blue styles
  const ctaClassName = [
    'group relative overflow-hidden rounded-xl bg-gradient-to-r px-6 py-2.5 text-sm font-medium text-white shadow-lg transition-all duration-300 hover:scale-[1.02] hover:shadow-xl active:scale-[0.98] sm:w-auto',
    styles.gradient,
    styles.shadow,
  ].join(' ');
  const content = {
    guest: {
      title: t('opportunities.guestCardTitle'),
      description: t('opportunities.guestCardDesc'),
      ctaLabel: t('opportunities.personalizedMatches'),
    },
    resume: {
      title: t('opportunities.resumeCardTitle'),
      description: t('opportunities.resumeCardDesc'),
      ctaLabel: t('opportunities.uploadResume'),
    },
    profile: {
      title: t('opportunities.profileCardTitle'),
      description: t('opportunities.profileCardDesc'),
      ctaLabel: t('opportunities.reviewProfile'),
    },
    matches: {
      title: t('opportunities.searchSmarterTitle'),
      description: t('opportunities.searchSmarterDesc'),
      ctaLabel: t('opportunities.seeYourMatches'),
    },
  }[card.key] || {};
  const title = content.title || card.title;
  const description = content.description || card.description;
  const ctaLabel = content.ctaLabel || card.ctaLabel;

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-neutral-200/80 bg-white shadow-lg transition-all duration-500 hover:border-neutral-300 hover:shadow-2xl">
      <div className={`absolute inset-0 bg-gradient-to-br ${styles.soft} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />
      <div className={`absolute -inset-1 bg-gradient-to-r ${styles.gradient} opacity-0 blur-xl transition-all duration-500 group-hover:opacity-20`} />
      <div className={`absolute -right-16 -top-16 h-32 w-32 rounded-full ${styles.glow} transition-all duration-700 group-hover:scale-150`} />
      <div className={`absolute -bottom-16 -left-16 h-32 w-32 rounded-full ${styles.glow} transition-all delay-100 duration-700 group-hover:scale-150`} />

      <div className="relative p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-1 gap-4">
            <div className="relative">
              <div className={`absolute -inset-1 rounded-2xl bg-gradient-to-r ${styles.gradient} opacity-0 blur-lg transition-all duration-500 group-hover:opacity-30`} />
              <div className={`relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${styles.soft} transition-all duration-300 group-hover:scale-110`}>
                <Icon className={`h-5 w-5 ${styles.icon}`} aria-hidden="true" />
              </div>
            </div>

            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-bold leading-tight text-neutral-900 lg:text-xl">
                {title}
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-neutral-500">
                {description}
              </p>
            </div>
          </div>

          <div className="flex shrink-0">
            {card.to ? (
              <Button asChild className={ctaClassName}>
                <Link to={card.to}>
                  {ctaLabel}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                </Link>
              </Button>
            ) : (
              <Button type="button" className={ctaClassName} onClick={card.onClick}>
                {ctaLabel}
                <ArrowRight className="ml-2 h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </article>
  );
};

export default OpportunitiesBrowseInterruptionCard;
