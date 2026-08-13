// Test IDs for the authenticated workspace surfaces (shell, settings, members,
// roles, sessions). Naming follows the directive in ./auth.js.

export const SHELL = {
	root: 'app-shell-root',
	workspaceSwitcher: 'app-shell-workspace-switcher',
	navDashboard: 'app-shell-nav-dashboard',
	navGeneral: 'app-shell-nav-general',
	navMembers: 'app-shell-nav-members',
	navRoles: 'app-shell-nav-roles',
	navSessions: 'app-shell-nav-sessions',
	userEmail: 'app-shell-user-email',
	roleBadge: 'app-shell-role-badge',
};

export const DASHBOARD = {
	root: 'dashboard-root',
	emptyState: 'dashboard-empty-state',
	connectShopifyButton: 'dashboard-connect-shopify-button',
};

export const VERIFY_EMAIL = {
	root: 'verify-email-root',
	status: 'verify-email-status',
	loginLink: 'verify-email-login-link',
};

export const FORGOT_PASSWORD = {
	emailInput: 'forgot-password-email-input',
	submitButton: 'forgot-password-submit-button',
	message: 'forgot-password-message',
};

export const RESET_PASSWORD = {
	passwordInput: 'reset-password-password-input',
	confirmInput: 'reset-password-confirm-input',
	submitButton: 'reset-password-submit-button',
	message: 'reset-password-message',
};

export const INVITATION = {
	root: 'invitation-root',
	acceptButton: 'invitation-accept-button',
	message: 'invitation-message',
};

export const WORKSPACE_SETTINGS = {
	root: 'workspace-settings-root',
	nameInput: 'workspace-settings-name-input',
	timezoneInput: 'workspace-settings-timezone-input',
	currencyInput: 'workspace-settings-currency-input',
	toleranceInput: 'workspace-settings-tolerance-input',
	settlementWindowInput: 'workspace-settings-settlement-window-input',
	saveButton: 'workspace-settings-save-button',
	message: 'workspace-settings-message',
};

export const MEMBERS = {
	root: 'members-root',
	table: 'members-table',
	row: 'members-row',
	inviteButton: 'members-invite-button',
	inviteEmailInput: 'members-invite-email-input',
	inviteRoleSelect: 'members-invite-role-select',
	inviteSubmitButton: 'members-invite-submit-button',
	inviteMessage: 'members-invite-message',
	roleSelect: 'members-role-select',
	removeButton: 'members-remove-button',
	emptyState: 'members-empty-state',
};

export const ROLES = {
	root: 'roles-root',
	matrix: 'roles-matrix',
};

export const SESSIONS = {
	root: 'sessions-root',
	list: 'sessions-list',
	row: 'sessions-row',
	revokeButton: 'sessions-revoke-button',
	revokeAllButton: 'sessions-revoke-all-button',
};

export const LANDING = {
	root: 'landing-root',
	loginLink: 'landing-login-link',
	registerLink: 'landing-register-link',
	heroCta: 'landing-hero-cta',
};

export const STATE = {
	loading: 'state-loading',
	error: 'state-error',
	empty: 'state-empty',
};
