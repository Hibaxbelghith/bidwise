import { memo, useCallback, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Eye,
  ShieldCheck,
  ShieldOff,
  UserCheck,
  UserX,
} from 'lucide-react';

import { Badge } from '../../../components/ui/badge.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card.jsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../../components/ui/table.jsx';
import { toast } from 'sonner';
import { AdminUsersSuspendModal } from './AdminUsersSuspendModal';
import { ConfirmModal } from '../components/ConfirmModal.jsx';

import { formatDate } from '../components/opportunities/opportunity.Utils.js';
import { formatDateTime } from '../components/dashboard/dashboard.Utils.js';

import AdminUsersSkeleton from './AdminUsersSkeleton.jsx';

const getRoleLabel = (user) => {
  if (user.is_admin) return 'ADMIN';
  if (user.account_type === 'organization') return 'PROMOTEUR';
  return 'CANDIDAT';
};

const getRoleClassName = (user) => {
  if (user.is_admin) {
    return 'border-blue-200 bg-blue-50 text-blue-700';
  }
  if (user.account_type === 'organization') {
    return 'border-purple-200 bg-purple-50 text-purple-700';
  }
  return 'border-green-200 bg-green-50 text-green-700';
};

const statusClassName = (user) => {
  if (user.is_suspended) {
    return 'border-orange-200 bg-orange-50 text-orange-700';
  }
  return 'border-green-200 bg-green-50 text-green-700';
};

const statusLabel = (user) => {
  if (user.is_suspended) return 'SUSPENDED';
  return 'ACTIVE';
};

const ariaSortFor = (ordering, field) => {
  if (ordering === field) return 'ascending';
  if (ordering === `-${field}`) return 'descending';
  return 'none';
};

const sortIconFor = (ordering, field) => {
  if (ordering === field) return ArrowUp;
  if (ordering === `-${field}`) return ArrowDown;
  return ArrowUpDown;
};

const AdminUsersTable = ({
  users,
  count,
  ordering,
  onToggleOrdering,
  isLoading,
  isInitialLoading,
  isRefreshing,
  actionUserId,
  currentAdminUser,
  onToggleAdmin,
  onSuspendUser,
  onReactivateUser,
}) => {
  const [suspendModalUser, setSuspendModalUser] = useState(null);
  const [suspendError, setSuspendError] = useState(null);
  const [detailsUser, setDetailsUser] = useState(null);
  
  // Modal de confirmation
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    type: null,
    user: null,
    title: '',
    message: '',
    confirmLabel: '',
    variant: 'danger',
  });
  const [isActionLoading, setIsActionLoading] = useState(false);

  // Vérifier si l'utilisateur est l'admin actuel (connexion)
  const isCurrentAdmin = useCallback((user) => {
    if (!currentAdminUser || !user) return false;
    return currentAdminUser.id === user.id || currentAdminUser.email === user.email;
  }, [currentAdminUser]);

  // Vérifier si on peut modifier le rôle admin
  const canToggleAdmin = useCallback((user) => {
    if (isCurrentAdmin(user)) {
      toast.error('Vous ne pouvez pas modifier votre propre rôle administrateur.');
      return false;
    }
    return true;
  }, [isCurrentAdmin]);

  // Vérifier si on peut suspendre l'utilisateur
  const canSuspendUser = useCallback((user) => {
    if (isCurrentAdmin(user)) {
      toast.error('Vous ne pouvez pas suspendre votre propre compte.');
      return false;
    }
    if (user.is_suspended) {
      toast.error('Ce compte est déjà suspendu.');
      return false;
    }
    return true;
  }, [isCurrentAdmin]);

  // Vérifier si on peut réactiver l'utilisateur
  const canReactivate = useCallback((user) => {
    if (!user.is_suspended) {
      toast.error('Ce compte n\'est pas suspendu.');
      return false;
    }
    return true;
  }, []);

  // Ouvrir modal de confirmation pour toggle admin
  const openToggleAdminConfirm = (user) => {
    if (!canToggleAdmin(user)) return;
    
    setConfirmModal({
      isOpen: true,
      type: 'toggleAdmin',
      user,
      title: user.is_admin ? 'Supprimer les droits admin' : 'Nommer administrateur',
      message: user.is_admin
        ? `Role actuel: ADMIN. Cette action retirera les droits administrateur de ${user.email}, revoquera ses refresh tokens et sera enregistree dans l'audit log.`
        : `Role actuel: ${getRoleLabel(user)}. Cette action nommera ${user.email} administrateur, revoquera ses refresh tokens et sera enregistree dans l'audit log.`,
      confirmLabel: user.is_admin ? 'Supprimer admin' : 'Make Admin',
      variant: user.is_admin ? 'warning' : 'info',
    });
  };

  // Ouvrir modal de confirmation pour reactivate
  const openReactivateConfirm = (user) => {
    if (!canReactivate(user)) return;
    
    setConfirmModal({
      isOpen: true,
      type: 'reactivate',
      user,
      title: 'Réactiver le compte',
      message: `Cette action reactivera le compte de ${user.email}, revoquera ses refresh tokens existants et sera enregistree dans l'audit log.`,
      confirmLabel: 'Réactiver',
      variant: 'info',
    });
  };

  // Ouvrir modal de suspension
  const openSuspendModal = (user) => {
    if (!canSuspendUser(user)) return;
    setSuspendModalUser(user);
    setSuspendError(null);
  };

  // Exécuter l'action après confirmation
  const handleConfirmAction = useCallback(async () => {
    const { type, user } = confirmModal;
    setIsActionLoading(true);

    let result;
    switch (type) {
      case 'toggleAdmin':
        if (!canToggleAdmin(user)) {
          setIsActionLoading(false);
          setConfirmModal(prev => ({ ...prev, isOpen: false }));
          return;
        }
        result = await onToggleAdmin(user);
        if (result?.success) {
          toast.success(`${user.email} est désormais ${result.data?.is_admin ? 'administrateur' : 'utilisateur standard'}.`);
        } else if (result?.error) {
          toast.error(result.error.message || 'Échec de la modification du rôle.');
        }
        break;
      
      case 'reactivate':
        result = await onReactivateUser(user);
        if (result?.success) {
          toast.success(`Le compte de ${user.email} a été réactivé.`);
        } else if (result?.error) {
          toast.error(result.error.message || 'Échec de la réactivation du compte.');
        }
        break;
      
      default:
        break;
    }

    setIsActionLoading(false);
    setConfirmModal(prev => ({ ...prev, isOpen: false }));
  }, [confirmModal, onToggleAdmin, onReactivateUser, canToggleAdmin]);

  // Soumission du modal de suspension
  const handleSuspendModalSubmit = useCallback(async (user, reason, detail) => {
    if (!canSuspendUser(user)) {
      return { success: false, error: { message: 'Impossible de suspendre cet utilisateur.' } };
    }
    
    const result = await onSuspendUser(user, reason, detail);
    
    if (result?.success) {
      toast.success(`Le compte de ${user.email} a été suspendu.`);
      setSuspendModalUser(null);
      setSuspendError(null);
    } else if (result?.error) {
      setSuspendError(result.error);
      toast.error(result.error.message || 'Échec de la suspension du compte.');
    }
    
    return result;
  }, [onSuspendUser, canSuspendUser]);

  const handleSuspendModalClose = useCallback(() => {
    setSuspendModalUser(null);
    setSuspendError(null);
  }, []);

  // Afficher le skeleton UNIQUEMENT pendant le chargement initial
  const showSkeleton = isInitialLoading;
  
  // Afficher le message "no users" UNIQUEMENT quand le chargement est fini et qu'il n'y a pas d'utilisateurs
  const showNoUsers = !isInitialLoading && !isLoading && users.length === 0;
  
  // Afficher les données UNIQUEMENT quand le chargement est fini et qu'il y a des utilisateurs
  const showUsers = !isInitialLoading && users.length > 0;

  return (
    <>
      <Card>
        <CardHeader className="flex flex-col gap-2 border-b border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-base">Liste des utilisateurs</CardTitle>
          <span className="text-sm text-neutral-500">{count} total</span>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-neutral-50">
                <TableHead className="px-4 py-3" aria-sort={ariaSortFor(ordering, 'email')}>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-sm font-medium"
                    onClick={() => onToggleOrdering('email')}
                  >
                    Email
                    {(() => {
                      const Icon = sortIconFor(ordering, 'email');
                      return <Icon className="h-3.5 w-3.5" aria-hidden="true" />;
                    })()}
                  </button>
                </TableHead>
                <TableHead className="px-4 py-3 text-sm font-medium" aria-sort={ariaSortFor(ordering, 'date_joined')}>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1"
                    onClick={() => onToggleOrdering('date_joined')}
                  >
                    Inscrit le
                    {(() => {
                      const Icon = sortIconFor(ordering, 'date_joined');
                      return <Icon className="h-3.5 w-3.5" aria-hidden="true" />;
                    })()}
                  </button>
                </TableHead>
                <TableHead className="px-4 py-3 text-sm font-medium" aria-sort={ariaSortFor(ordering, 'last_login_at')}>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1"
                    onClick={() => onToggleOrdering('last_login_at')}
                  >
                    Dernière connexion
                    {(() => {
                      const Icon = sortIconFor(ordering, 'last_login_at');
                      return <Icon className="h-3.5 w-3.5" aria-hidden="true" />;
                    })()}
                  </button>
                </TableHead>
                <TableHead className="px-4 py-3 text-sm font-medium">Rôle</TableHead>
                <TableHead className="px-4 py-3 text-sm font-medium">Statut</TableHead>
                <TableHead className="px-4 py-3 text-right text-sm font-medium">Actions</TableHead>
              </TableRow>
            </TableHeader>
            
            <TableBody
              aria-busy={isLoading}
              style={{
                opacity: isRefreshing ? 0.4 : 1,
                pointerEvents: isRefreshing ? 'none' : 'auto',
                transition: 'opacity 150ms ease',
              }}
            >
              {/* SKELETON - UNIQUEMENT pendant le chargement initial */}
              {showSkeleton && (
                <AdminUsersSkeleton 
                  isInitialLoading={showSkeleton} 
                  variant="progressive" 
                  rows={6} 
                />
              )}

              {/* NO USERS - UNIQUEMENT quand le chargement est terminé et qu'il n'y a aucun résultat */}
              {showNoUsers && (
                <TableRow>
                  <TableCell colSpan={6} className="px-4 py-10 text-center text-neutral-500">
                    Aucun utilisateur trouvé.
                  </TableCell>
                </TableRow>
              )}

              {/* USERS LIST - UNIQUEMENT quand le chargement est terminé et qu'il y a des résultats */}
              {showUsers && users.map((user) => {
                const isOwnAccount = isCurrentAdmin(user);
                
                return (
                  <TableRow key={user.id} className="hover:bg-neutral-50/50">
                    <TableCell className="max-w-[460px] px-4 py-3">
                      <p className="truncate font-medium text-neutral-900">
                        {user.email || `User #${user.id}`}
                        {isOwnAccount && (
                          <span className="ml-2 text-xs font-normal text-blue-600">(Vous)</span>
                        )}
                      </p>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-sm text-neutral-600">
                      {formatDate(user.date_joined)}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-sm text-neutral-600">
                      {formatDateTime(user.last_login_at)}
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={getRoleClassName(user)}>
                        {getRoleLabel(user)}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <Badge variant="outline" className={statusClassName(user)}>
                        {statusLabel(user)}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          aria-label={`Voir la fiche de ${user.email}`}
                          title="Voir la fiche"
                          disabled={isLoading}
                          onClick={() => setDetailsUser(user)}
                        >
                          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                        </Button>
                        {/* Toggle Admin - Désactivé pour son propre compte */}
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          aria-label={user.is_admin ? `Retirer les droits admin de ${user.email}` : `Nommer ${user.email} administrateur`}
                          disabled={actionUserId === user.id || isLoading || isOwnAccount}
                          onClick={() => openToggleAdminConfirm(user)}
                          title={isOwnAccount ? "Vous ne pouvez pas modifier votre propre role" : user.is_admin ? "Retirer admin" : "Ajouter admin"}
                        >
                          {user.is_admin ? (
                            <ShieldOff className="h-3.5 w-3.5" aria-hidden="true" />
                          ) : (
                            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                          )}
                        </Button>
                        
                        {/* Suspend / Reactivate - Désactivé pour son propre compte */}
                        {user.is_suspended ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            aria-label={`Reactiver le compte de ${user.email}`}
                            title="Reactiver"
                            disabled={actionUserId === user.id || isLoading}
                            onClick={() => openReactivateConfirm(user)}
                          >
                            <UserCheck className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            variant="destructive"
                            size="icon"
                            aria-label={`Suspendre le compte de ${user.email}`}
                            disabled={actionUserId === user.id || isLoading || isOwnAccount}
                            onClick={() => openSuspendModal(user)}
                            title={isOwnAccount ? "Vous ne pouvez pas suspendre votre propre compte" : "Suspendre"}
                          >
                            <UserX className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Modal de confirmation moderne */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmLabel={confirmModal.confirmLabel}
        cancelLabel="Annuler"
        variant={confirmModal.variant}
        onConfirm={handleConfirmAction}
        onCancel={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
        isLoading={isActionLoading}
      />

      {/* Modal de suspension */}
      <AdminUsersSuspendModal
        isOpen={!!suspendModalUser}
        user={suspendModalUser}
        isLoading={actionUserId === suspendModalUser?.id}
        error={suspendError}
        onSuspend={handleSuspendModalSubmit}
        onClose={handleSuspendModalClose}
      />
      {detailsUser ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
            <div className="border-b border-neutral-200 px-6 py-4">
              <h2 className="text-lg font-semibold text-neutral-900">Fiche utilisateur</h2>
              <p className="mt-1 text-sm text-neutral-500">{detailsUser.email}</p>
            </div>
            <div className="grid gap-3 px-6 py-5 text-sm">
              <p><span className="font-medium text-neutral-700">ID:</span> {detailsUser.id}</p>
              <p><span className="font-medium text-neutral-700">Role:</span> {getRoleLabel(detailsUser)}</p>
              <p><span className="font-medium text-neutral-700">Statut:</span> {statusLabel(detailsUser)}</p>
              <p><span className="font-medium text-neutral-700">Provider:</span> {detailsUser.provider || '-'}</p>
              <p><span className="font-medium text-neutral-700">Inscription:</span> {formatDate(detailsUser.date_joined)}</p>
              <p><span className="font-medium text-neutral-700">Derniere connexion:</span> {formatDateTime(detailsUser.last_login_at)}</p>
              {detailsUser.suspension_reason ? (
                <p><span className="font-medium text-neutral-700">Motif suspension:</span> {detailsUser.suspension_reason}</p>
              ) : null}
            </div>
            <div className="flex justify-end border-t border-neutral-200 px-6 py-4">
              <Button type="button" variant="outline" onClick={() => setDetailsUser(null)}>
                Fermer
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};

export default memo(AdminUsersTable);
