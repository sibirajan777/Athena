/**
 * Athena AI - Main Application Logic
 * Claude AI Signature Editorial Design System with Antigravity Visual Engine
 */

const API_BASE = "";
let currentConversationId = null;
let conversationsList = [];
let isGenerating = false;
let currentDocumentsList = [];

// DOM Elements cache
let elements = {};

document.addEventListener("DOMContentLoaded", () => {
    // 0. Auth check
    const token = localStorage.getItem("athena_token");
    if (!token) {
        window.location.replace("login.html");
        return;
    }

    elements = {
        // Layout
        sidebar: document.getElementById("sidebar"),
        sidebarBackdrop: document.getElementById("sidebar-backdrop"),
        mobileToggleBtn: document.getElementById("mobile-toggle-btn"),
        closeSidebarBtn: document.getElementById("close-sidebar-btn"),
        currentChatTitle: document.getElementById("current-chat-title"),
        renameTitleBtn: document.getElementById("rename-title-btn"),
        
        // Theme
        themeToggleBtn: document.getElementById("theme-toggle-btn"),
        themeIconSun: document.getElementById("theme-icon-sun"),
        themeIconMoon: document.getElementById("theme-icon-moon"),
        
        // Chat UI
        newChatBtn: document.getElementById("new-chat-btn"),
        conversationsList: document.getElementById("conversations-list"),
        chatScrollArea: document.getElementById("chat-scroll-area"),
        welcomeState: document.getElementById("welcome-state"),
        messagesContainer: document.getElementById("messages-container"),
        typingIndicator: document.getElementById("typing-indicator"),
        chatForm: document.getElementById("chat-form"),
        questionInput: document.getElementById("question-input"),
        sendBtn: document.getElementById("send-btn"),
        fileInput: document.getElementById("file-input"),
        dockUploadBtn: document.getElementById("dock-upload-btn"),
        
        // Knowledge Base Sidebar & Modal
        sidebarKbWidget: document.getElementById("sidebar-kb-widget"),
        btnViewKbDocs: document.getElementById("btn-view-kb-docs"),
        kbChunksBadge: document.getElementById("kb-chunks-badge"),
        kbInfoText: document.getElementById("kb-info-text"),
        
        // Knowledge Base Manager Modal
        kbModal: document.getElementById("kb-modal"),
        kbCloseBtn: document.getElementById("kb-close-btn"),
        kbDoneBtn: document.getElementById("kb-done-btn"),
        kbModalTotalDocs: document.getElementById("kb-modal-total-docs"),
        kbModalTotalChunks: document.getElementById("kb-modal-total-chunks"),
        kbSearchInput: document.getElementById("kb-search-input"),
        kbRefreshBtn: document.getElementById("kb-refresh-btn"),
        kbDocsContainer: document.getElementById("kb-docs-container"),
        
        // Document Chunks Inspector Modal
        docPreviewModal: document.getElementById("doc-preview-modal"),
        previewCloseBtn: document.getElementById("preview-close-btn"),
        previewDoneBtn: document.getElementById("preview-done-btn"),
        previewDocTitle: document.getElementById("preview-doc-title"),
        previewDocMeta: document.getElementById("preview-doc-meta"),
        previewChunksList: document.getElementById("preview-chunks-list"),

        // Rename Modal
        renameModal: document.getElementById("rename-modal"),
        renameInput: document.getElementById("rename-input"),
        renameForm: document.getElementById("rename-form"),
        renameCancelBtn: document.getElementById("rename-cancel-btn"),
        
        // User Profile & Footer
        sidebarProfileCard: document.getElementById("sidebar-profile-card"),
        userAvatar: document.getElementById("user-avatar"),
        userDisplayName: document.getElementById("user-display-name"),
        userEmail: document.getElementById("user-email"),
        logoutBtn: document.getElementById("logout-btn"),
        topProfileBtn: document.getElementById("top-profile-btn"),
        topAvatar: document.getElementById("top-avatar"),
        
        // Profile Modal
        profileModal: document.getElementById("profile-modal"),
        profileCloseBtn: document.getElementById("profile-close-btn"),
        profileDoneBtn: document.getElementById("profile-done-btn"),
        profileHeroAvatar: document.getElementById("profile-hero-avatar"),
        profileHeroName: document.getElementById("profile-hero-name"),
        profileHeroEmail: document.getElementById("profile-hero-email"),
        profileMemberSince: document.getElementById("profile-member-since"),
        profileUserId: document.getElementById("profile-user-id"),
        profileModalLogoutBtn: document.getElementById("profile-modal-logout-btn"),
        
        // Stats in Profile
        statConvs: document.getElementById("stat-convs"),
        statMessages: document.getElementById("stat-messages"),
        statChunks: document.getElementById("stat-chunks"),
        statDocs: document.getElementById("stat-docs"),
        profileStatDocsCard: document.getElementById("profile-stat-docs-card"),
        
        // Edit Profile Form
        editProfileForm: document.getElementById("edit-profile-form"),
        editDisplayName: document.getElementById("edit-display-name"),
        avatarColorDots: document.querySelectorAll(".color-dot"),
        
        // Change Password Form
        changePasswordForm: document.getElementById("change-password-form"),
        currentPassword: document.getElementById("current-password"),
        newPassword: document.getElementById("new-password"),
        confirmNewPassword: document.getElementById("confirm-new-password"),
        
        // Data Export & Clear
        btnExportChats: document.getElementById("btn-export-chats"),
        btnClearChats: document.getElementById("btn-clear-chats"),

        // Alert
        appAlert: document.getElementById("app-alert"),
        alertMessage: document.getElementById("alert-message"),
        alertCloseBtn: document.getElementById("alert-close-btn"),

        // Feature 2 — Citation Panel
        citationPanel: document.getElementById("citation-panel"),
        citationOverlay: document.getElementById("citation-overlay"),
        citationCloseBtn: document.getElementById("citation-close-btn"),
        citationDoneBtn: document.getElementById("citation-done-btn"),
        citationRefBadge: document.getElementById("citation-ref-badge"),
        citationSourceName: document.getElementById("citation-source-name"),
        citationLocation: document.getElementById("citation-location"),
        citationChunkText: document.getElementById("citation-chunk-text"),
        citationOpenKbBtn: document.getElementById("citation-open-kb-btn")
    };

    // 1. Initialize Theme UI
    initTheme();

    // 2. Setup Event Listeners
    setupEventListeners();

    // 3. Load Initial Data
    loadUserProfile();
    loadKnowledgeStats();
    loadConversations();
});

/**
 * Theme Management (Claude Light Warm Paper vs Claude Charcoal Dark)
 */
function initTheme() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    updateThemeIcons(isDark);

    if (elements.themeToggleBtn) {
        elements.themeToggleBtn.addEventListener("click", () => {
            const currentDark = document.documentElement.getAttribute("data-theme") === "dark";
            const newDark = !currentDark;
            if (newDark) {
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("athena_theme", "dark");
            } else {
                document.documentElement.removeAttribute("data-theme");
                localStorage.setItem("athena_theme", "light");
            }
            updateThemeIcons(newDark);
        });
    }
}

function updateThemeIcons(isDark) {
    if (elements.themeIconSun && elements.themeIconMoon) {
        if (isDark) {
            elements.themeIconSun.classList.add("hidden");
            elements.themeIconMoon.classList.remove("hidden");
        } else {
            elements.themeIconSun.classList.remove("hidden");
            elements.themeIconMoon.classList.add("hidden");
        }
    }
}

/**
 * Setup All Event Listeners
 */
function setupEventListeners() {
    const token = localStorage.getItem("athena_token");

    // Mobile sidebar
    if (elements.mobileToggleBtn) {
        elements.mobileToggleBtn.addEventListener("click", () => toggleSidebar(true));
    }
    if (elements.closeSidebarBtn) {
        elements.closeSidebarBtn.addEventListener("click", () => toggleSidebar(false));
    }
    if (elements.sidebarBackdrop) {
        elements.sidebarBackdrop.addEventListener("click", () => toggleSidebar(false));
    }

    // New Chat button
    if (elements.newChatBtn) {
        elements.newChatBtn.addEventListener("click", () => startNewChat());
    }

    // Chat form submit
    if (elements.chatForm) {
        elements.chatForm.addEventListener("submit", handleSendMessage);
    }

    // Input auto-resize & keyboard shortcuts
    if (elements.questionInput) {
        elements.questionInput.addEventListener("input", autoResizeInput);
        elements.questionInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                elements.chatForm.dispatchEvent(new Event("submit"));
            }
        });
    }

    // Prompt Chips click with Antigravity Impulse
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const prompt = chip.getAttribute("data-prompt");
            if (prompt && elements.questionInput) {
                elements.questionInput.value = prompt;
                autoResizeInput();
                elements.questionInput.focus();

                // Trigger Antigravity particle impulse from chip
                if (window.antigravity && typeof window.antigravity.triggerImpulse === "function") {
                    const rect = chip.getBoundingClientRect();
                    window.antigravity.triggerImpulse(rect.left + rect.width / 2, rect.top + rect.height / 2);
                }
            }
        });
    });

    // File Upload input & dock trigger
    if (elements.dockUploadBtn && elements.fileInput) {
        elements.dockUploadBtn.addEventListener("click", () => elements.fileInput.click());
    }
    if (elements.fileInput) {
        elements.fileInput.addEventListener("change", handleFileUpload);
    }

    // Rename button in top bar
    if (elements.renameTitleBtn) {
        elements.renameTitleBtn.addEventListener("click", () => openRenameModal());
    }
    if (elements.renameCancelBtn) {
        elements.renameCancelBtn.addEventListener("click", closeRenameModal);
    }
    if (elements.renameForm) {
        elements.renameForm.addEventListener("submit", handleRenameSubmit);
    }

    // Profile Modals
    if (elements.sidebarProfileCard) {
        elements.sidebarProfileCard.addEventListener("click", () => openProfileModal());
    }
    if (elements.topProfileBtn) {
        elements.topProfileBtn.addEventListener("click", () => openProfileModal());
    }
    if (elements.profileCloseBtn) {
        elements.profileCloseBtn.addEventListener("click", () => closeProfileModal());
    }
    if (elements.profileDoneBtn) {
        elements.profileDoneBtn.addEventListener("click", () => closeProfileModal());
    }
    if (elements.profileModal) {
        elements.profileModal.addEventListener("click", (e) => {
            if (e.target === elements.profileModal) closeProfileModal();
        });
    }

    // Knowledge Base Documents Manager Modals
    if (elements.btnViewKbDocs) {
        elements.btnViewKbDocs.addEventListener("click", (e) => {
            e.stopPropagation();
            openKbModal();
        });
    }
    if (elements.sidebarKbWidget) {
        elements.sidebarKbWidget.addEventListener("click", (e) => {
            if (e.target.closest("label") || e.target.closest("input")) return;
            openKbModal();
        });
    }
    if (elements.profileStatDocsCard) {
        elements.profileStatDocsCard.addEventListener("click", () => {
            closeProfileModal();
            openKbModal();
        });
    }
    if (elements.kbCloseBtn) {
        elements.kbCloseBtn.addEventListener("click", () => closeKbModal());
    }
    if (elements.kbDoneBtn) {
        elements.kbDoneBtn.addEventListener("click", () => closeKbModal());
    }
    if (elements.kbModal) {
        elements.kbModal.addEventListener("click", (e) => {
            if (e.target === elements.kbModal) closeKbModal();
        });
    }
    if (elements.kbRefreshBtn) {
        elements.kbRefreshBtn.addEventListener("click", () => loadKnowledgeDocuments());
    }
    if (elements.kbSearchInput) {
        elements.kbSearchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            const filtered = currentDocumentsList.filter(d => d.filename.toLowerCase().includes(query));
            renderKnowledgeDocuments(filtered);
        });
    }

    // Document Chunks Inspector Modal
    if (elements.previewCloseBtn) {
        elements.previewCloseBtn.addEventListener("click", () => closeDocPreviewModal());
    }
    if (elements.previewDoneBtn) {
        elements.previewDoneBtn.addEventListener("click", () => closeDocPreviewModal());
    }
    if (elements.docPreviewModal) {
        elements.docPreviewModal.addEventListener("click", (e) => {
            if (e.target === elements.docPreviewModal) closeDocPreviewModal();
        });
    }

    // Alert close
    if (elements.alertCloseBtn) {
        elements.alertCloseBtn.addEventListener("click", hideAlert);
    }

    // Feature 2 — Citation panel close controls
    if (elements.citationCloseBtn) {
        elements.citationCloseBtn.addEventListener("click", closeCitationPanel);
    }
    if (elements.citationDoneBtn) {
        elements.citationDoneBtn.addEventListener("click", closeCitationPanel);
    }
    if (elements.citationOverlay) {
        elements.citationOverlay.addEventListener("click", closeCitationPanel);
    }
    if (elements.citationOpenKbBtn) {
        elements.citationOpenKbBtn.addEventListener("click", () => {
            const sourceName = elements.citationOpenKbBtn.getAttribute("data-source");
            closeCitationPanel();
            if (sourceName) {
                openKbModal();
                setTimeout(() => openDocPreview(sourceName), 250);
            }
        });
    }

    // Global ESC listener to close open citation panel or modals
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (elements.citationPanel && elements.citationPanel.classList.contains("active")) {
                closeCitationPanel();
            }
        }
    });

    // Profile Tabs Switching
    document.querySelectorAll(".profile-tab-btn").forEach(tabBtn => {
        tabBtn.addEventListener("click", () => {
            const targetTab = tabBtn.getAttribute("data-tab");
            switchProfileTab(targetTab);
        });
    });

    // Avatar Color Selection
    if (elements.avatarColorDots) {
        elements.avatarColorDots.forEach(dot => {
            dot.addEventListener("click", () => {
                elements.avatarColorDots.forEach(d => d.classList.remove("active"));
                dot.classList.add("active");
                const chosenColor = dot.getAttribute("data-color");
                if (elements.profileHeroAvatar) elements.profileHeroAvatar.style.background = chosenColor;
            });
        });
    }

    // Edit Profile Form Submit
    if (elements.editProfileForm) {
        elements.editProfileForm.addEventListener("submit", handleEditProfileSubmit);
    }

    // Change Password Form Submit
    if (elements.changePasswordForm) {
        elements.changePasswordForm.addEventListener("submit", handleChangePasswordSubmit);
    }

    // Export Chats
    if (elements.btnExportChats) {
        elements.btnExportChats.addEventListener("click", handleExportChats);
    }

    // Clear All Chats
    if (elements.btnClearChats) {
        elements.btnClearChats.addEventListener("click", handleClearAllChats);
    }

    // Logout Actions
    const doLogout = () => {
        localStorage.removeItem("athena_token");
        localStorage.removeItem("athena_user");
        window.location.replace("login.html");
    };

    if (elements.logoutBtn) elements.logoutBtn.addEventListener("click", (e) => { e.stopPropagation(); doLogout(); });
    if (elements.profileModalLogoutBtn) elements.profileModalLogoutBtn.addEventListener("click", doLogout);
}

function toggleSidebar(open) {
    if (open) {
        elements.sidebar.classList.add("open");
        elements.sidebarBackdrop.classList.add("active");
    } else {
        elements.sidebar.classList.remove("open");
        elements.sidebarBackdrop.classList.remove("active");
    }
}

function autoResizeInput() {
    const input = elements.questionInput;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
}

/**
 * User Profile & Settings Management
 */
async function loadUserProfile() {
    const token = localStorage.getItem("athena_token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/user/profile`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            renderUserProfileUI(data);
        }
    } catch (err) {
        console.error("Failed to load user profile:", err);
    }
}

function renderUserProfileUI(profile) {
    const initial = (profile.display_name || profile.email || "U").charAt(0).toUpperCase();
    
    // Sidebar Footer
    if (elements.userAvatar) {
        elements.userAvatar.textContent = initial;
        if (profile.avatar_color) elements.userAvatar.style.background = profile.avatar_color;
    }
    if (elements.userDisplayName) elements.userDisplayName.textContent = profile.display_name;
    if (elements.userEmail) elements.userEmail.textContent = profile.email;

    // Top Bar Trigger Avatar
    if (elements.topAvatar) {
        elements.topAvatar.textContent = initial;
        if (profile.avatar_color) elements.topAvatar.style.background = profile.avatar_color;
    }

    // Modal Hero Card
    if (elements.profileHeroAvatar) {
        elements.profileHeroAvatar.textContent = initial;
        if (profile.avatar_color) elements.profileHeroAvatar.style.background = profile.avatar_color;
    }
    if (elements.profileHeroName) elements.profileHeroName.textContent = profile.display_name;
    if (elements.profileHeroEmail) elements.profileHeroEmail.textContent = profile.email;
    if (elements.profileMemberSince && profile.created_at) {
        elements.profileMemberSince.textContent = `Member since ${profile.created_at}`;
    }
    if (elements.profileUserId) elements.profileUserId.textContent = `#${profile.id}`;

    // Modal Overview Stats
    if (profile.stats) {
        if (elements.statConvs) elements.statConvs.textContent = profile.stats.total_conversations;
        if (elements.statMessages) elements.statMessages.textContent = profile.stats.total_messages;
        if (elements.statChunks) elements.statChunks.textContent = Number(profile.stats.total_chunks).toLocaleString();
        if (elements.statDocs) elements.statDocs.textContent = profile.stats.total_documents;
    }

    // Edit Form Pre-fill
    if (elements.editDisplayName) elements.editDisplayName.value = profile.display_name;
    if (elements.avatarColorDots) {
        elements.avatarColorDots.forEach(dot => {
            if (dot.getAttribute("data-color") === profile.avatar_color) {
                dot.classList.add("active");
            } else {
                dot.classList.remove("active");
            }
        });
    }
}

function openProfileModal() {
    loadUserProfile();
    if (elements.profileModal) elements.profileModal.classList.remove("hidden");
}

function closeProfileModal() {
    if (elements.profileModal) elements.profileModal.classList.add("hidden");
}

function switchProfileTab(tabName) {
    document.querySelectorAll(".profile-tab-btn").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabName) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    document.querySelectorAll(".profile-tab-pane").forEach(pane => {
        if (pane.id === `tab-${tabName}`) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });
}

async function handleEditProfileSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem("athena_token");
    const displayName = elements.editDisplayName.value.trim();
    const activeDot = document.querySelector(".color-dot.active");
    const avatarColor = activeDot ? activeDot.getAttribute("data-color") : "#141413";

    if (!displayName) return;

    try {
        const res = await fetch(`${API_BASE}/user/profile`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ display_name: displayName, avatar_color: avatarColor })
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            showAlert("Profile updated successfully!");
            loadUserProfile();
            switchProfileTab("overview");
        } else {
            const data = await res.json();
            showAlert(data.detail || "Failed to update profile", "error");
        }
    } catch (err) {
        console.error("Profile edit error:", err);
        showAlert("Failed to connect to server.", "error");
    }
}

async function handleChangePasswordSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem("athena_token");
    const oldPass = elements.currentPassword.value;
    const newPass = elements.newPassword.value;
    const confirmPass = elements.confirmNewPassword.value;

    if (newPass.length < 6) {
        showAlert("New password must be at least 6 characters.", "error");
        return;
    }
    if (newPass !== confirmPass) {
        showAlert("New passwords do not match.", "error");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/user/change-password`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ old_password: oldPass, new_password: newPass })
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            showAlert("Password updated successfully!");
            elements.currentPassword.value = "";
            elements.newPassword.value = "";
            elements.confirmNewPassword.value = "";
            switchProfileTab("overview");
        } else {
            const data = await res.json();
            showAlert(data.detail || "Incorrect current password.", "error");
        }
    } catch (err) {
        console.error("Password update error:", err);
        showAlert("Connection error changing password.", "error");
    }
}

async function handleExportChats() {
    const token = localStorage.getItem("athena_token");
    try {
        const res = await fetch(`${API_BASE}/user/export`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `athena_conversations_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            showAlert("Chat history exported successfully!");
        }
    } catch (err) {
        console.error("Export error:", err);
        showAlert("Failed to export conversations.", "error");
    }
}

async function handleClearAllChats() {
    if (!confirm("Are you sure you want to PERMANENTLY CLEAR ALL conversation history? This cannot be undone.")) return;

    const token = localStorage.getItem("athena_token");
    try {
        const res = await fetch(`${API_BASE}/user/conversations`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            showAlert("All conversation history cleared.");
            currentConversationId = null;
            await loadConversations();
            startNewChat(false);
            loadUserProfile();
        } else {
            showAlert("Failed to clear chat history.", "error");
        }
    } catch (err) {
        console.error("Clear chats error:", err);
        showAlert("Connection error.", "error");
    }
}

/**
 * ==========================================================================
 * Knowledge Base Documents Viewer & Manager
 * ==========================================================================
 */
function openKbModal() {
    if (elements.kbModal) {
        elements.kbModal.classList.remove("hidden");
        loadKnowledgeDocuments();
    }
}

function closeKbModal() {
    if (elements.kbModal) elements.kbModal.classList.add("hidden");
}

async function loadKnowledgeStats() {
    const token = localStorage.getItem("athena_token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/knowledge/stats`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            const chunkCount = Number(data.total_chunks || 0).toLocaleString();
            const docCount = data.document_count || 0;

            if (elements.kbChunksBadge) elements.kbChunksBadge.textContent = `${chunkCount} chunks`;
            if (elements.kbInfoText) elements.kbInfoText.textContent = `${docCount} document${docCount === 1 ? '' : 's'} feeded to Athena.`;
        }
    } catch (err) {
        console.error("Knowledge stats fetch error:", err);
    }
}

async function loadKnowledgeDocuments() {
    const token = localStorage.getItem("athena_token");
    if (!token) return;

    if (elements.kbDocsContainer) {
        elements.kbDocsContainer.innerHTML = `
            <div class="kb-loading">
                <div class="spinner"></div>
                <span>Loading feeded documents...</span>
            </div>
        `;
    }

    try {
        const res = await fetch(`${API_BASE}/knowledge/documents`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            currentDocumentsList = data.documents || [];
            
            if (elements.kbModalTotalDocs) elements.kbModalTotalDocs.textContent = data.document_count;
            if (elements.kbModalTotalChunks) elements.kbModalTotalChunks.textContent = Number(data.total_chunks).toLocaleString();
            
            // Sync sidebar badges
            if (elements.kbChunksBadge) elements.kbChunksBadge.textContent = `${Number(data.total_chunks).toLocaleString()} chunks`;
            if (elements.kbInfoText) elements.kbInfoText.textContent = `${data.document_count} document${data.document_count === 1 ? '' : 's'} feeded to Athena.`;

            renderKnowledgeDocuments(currentDocumentsList);
        } else {
            elements.kbDocsContainer.innerHTML = `
                <div class="kb-empty-state">
                    <p>Failed to load knowledge documents.</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error loading knowledge documents:", err);
        elements.kbDocsContainer.innerHTML = `
            <div class="kb-empty-state">
                <p>Connection error loading documents.</p>
            </div>
        `;
    }
}

function renderKnowledgeDocuments(documents) {
    if (!elements.kbDocsContainer) return;

    if (!documents || documents.length === 0) {
        elements.kbDocsContainer.innerHTML = `
            <div class="kb-empty-state">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color:var(--text-muted)">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
                <p>No documents found matching your search.</p>
            </div>
        `;
        return;
    }

    elements.kbDocsContainer.innerHTML = "";

    documents.forEach(doc => {
        const card = document.createElement("div");
        card.className = "kb-doc-card";

        const docType = (doc.type || "FILE").toUpperCase();
        let badgeClass = "file";
        if (docType === "PDF") badgeClass = "pdf";
        else if (docType === "MD") badgeClass = "md";

        card.innerHTML = `
            <div class="kb-doc-left">
                <div class="doc-format-badge ${badgeClass}">${escapeHtml(docType)}</div>
                <div class="kb-doc-info">
                    <span class="kb-doc-title" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                    <div class="kb-doc-meta-row">
                        <span class="doc-chunks-pill">${Number(doc.chunks).toLocaleString()} chunks</span>
                        <span class="doc-size-tag">${escapeHtml(doc.size)}</span>
                        <span>•</span>
                        <span>${escapeHtml(doc.modified_at)}</span>
                    </div>
                </div>
            </div>
            <div class="kb-doc-actions">
                <button class="btn-doc-action btn-inspect" title="Inspect indexed text chunks">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                    <span>Inspect</span>
                </button>
                <button class="btn-doc-action btn-reindex" title="Re-index document">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="23 4 23 10 17 10"></polyline>
                        <polyline points="1 20 1 14 7 14"></polyline>
                        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                    </svg>
                </button>
                <button class="btn-doc-action danger btn-delete" title="Delete document from knowledge base">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        // Inspect chunks
        card.querySelector(".btn-inspect").addEventListener("click", () => openDocPreview(doc.filename));
        
        // Reindex document
        card.querySelector(".btn-reindex").addEventListener("click", () => handleReindexDoc(doc.filename));

        // Delete document
        card.querySelector(".btn-delete").addEventListener("click", () => handleDeleteDoc(doc.filename));

        elements.kbDocsContainer.appendChild(card);
    });
}

/**
 * Document Preview / Chunk Inspector Modal
 */
async function openDocPreview(filename) {
    const token = localStorage.getItem("athena_token");
    if (!token) return;

    if (elements.previewDocTitle) elements.previewDocTitle.textContent = filename;
    if (elements.previewDocMeta) elements.previewDocMeta.textContent = "Loading indexed chunks from vector database...";
    if (elements.previewChunksList) {
        elements.previewChunksList.innerHTML = `
            <div class="kb-loading">
                <div class="spinner"></div>
                <span>Fetching vector chunks...</span>
            </div>
        `;
    }

    if (elements.docPreviewModal) elements.docPreviewModal.classList.remove("hidden");

    try {
        const encodedName = encodeURIComponent(filename);
        const res = await fetch(`${API_BASE}/knowledge/documents/${encodedName}/preview`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            renderDocChunksPreview(data);
        } else {
            elements.previewChunksList.innerHTML = `<p class="kb-empty-state">No chunks found or document not indexed yet.</p>`;
        }
    } catch (err) {
        console.error("Preview fetch error:", err);
        elements.previewChunksList.innerHTML = `<p class="kb-empty-state">Error loading preview.</p>`;
    }
}

function renderDocChunksPreview(data) {
    if (elements.previewDocMeta) {
        elements.previewDocMeta.textContent = `Showing sample extracted chunks (${data.total_chunks_found} samples displayed)`;
    }

    if (!data.chunks_preview || data.chunks_preview.length === 0) {
        elements.previewChunksList.innerHTML = `<div class="kb-empty-state"><p>No text chunks indexed for this file yet.</p></div>`;
        return;
    }

    elements.previewChunksList.innerHTML = "";

    data.chunks_preview.forEach((chunk, idx) => {
        const chunkItem = document.createElement("div");
        chunkItem.className = "preview-chunk-item";
        chunkItem.innerHTML = `
            <div class="preview-chunk-header">
                <span class="chunk-id-tag">Chunk #${idx + 1} • ID: ${escapeHtml(chunk.chunk_id)}</span>
                <button class="chunk-copy-btn" title="Copy chunk text">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Copy</span>
                </button>
            </div>
            <div class="chunk-snippet-text">${escapeHtml(chunk.text)}</div>
        `;

        const copyBtn = chunkItem.querySelector(".chunk-copy-btn");
        copyBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(chunk.text).then(() => {
                copyBtn.querySelector("span").textContent = "Copied!";
                setTimeout(() => { copyBtn.querySelector("span").textContent = "Copy"; }, 1800);
            });
        });

        elements.previewChunksList.appendChild(chunkItem);
    });
}

function closeDocPreviewModal() {
    if (elements.docPreviewModal) elements.docPreviewModal.classList.add("hidden");
}

async function handleReindexDoc(filename) {
    const token = localStorage.getItem("athena_token");
    showAlert(`Re-indexing "${filename}"...`);

    try {
        const encodedName = encodeURIComponent(filename);
        const res = await fetch(`${API_BASE}/knowledge/documents/${encodedName}/reindex`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            showAlert(`✅ Successfully re-indexed "${filename}" (${data.chunks_added} chunks).`);
            loadKnowledgeDocuments();
            loadUserProfile();
        } else {
            showAlert(`Failed to re-index document.`, "error");
        }
    } catch (err) {
        console.error("Re-index error:", err);
        showAlert("Connection error re-indexing.", "error");
    }
}

async function handleDeleteDoc(filename) {
    if (!confirm(`Are you sure you want to remove "${filename}" from Athena's Knowledge Base?\n\nThis will remove the file and all associated vector embeddings.`)) return;

    const token = localStorage.getItem("athena_token");
    try {
        const encodedName = encodeURIComponent(filename);
        const res = await fetch(`${API_BASE}/knowledge/documents/${encodedName}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            showAlert(`✅ Document "${filename}" deleted.`);
            loadKnowledgeDocuments();
            loadUserProfile();
        } else {
            showAlert(`Failed to delete "${filename}".`, "error");
        }
    } catch (err) {
        console.error("Delete doc error:", err);
        showAlert("Connection error deleting file.", "error");
    }
}

/**
 * ==========================================================================
 * Conversations Management
 * ==========================================================================
 */
async function loadConversations() {
    const token = localStorage.getItem("athena_token");
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/conversations`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            conversationsList = await res.json();
            renderConversationsList();
        }
    } catch (err) {
        console.error("Failed to load conversations:", err);
        if (elements.conversationsList) {
            elements.conversationsList.innerHTML = `<div class="conv-empty">Failed to load chats.</div>`;
        }
    }
}

function renderConversationsList() {
    if (!elements.conversationsList) return;

    if (conversationsList.length === 0) {
        elements.conversationsList.innerHTML = `<div class="conv-empty">No conversation history yet.</div>`;
        return;
    }

    elements.conversationsList.innerHTML = "";

    conversationsList.forEach(conv => {
        const item = document.createElement("div");
        item.className = `conv-item ${conv.id === currentConversationId ? "active" : ""}`;
        item.setAttribute("data-id", conv.id);

        item.innerHTML = `
            <div class="conv-content">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="conv-title" title="${escapeHtml(conv.title)}">${escapeHtml(conv.title)}</span>
            </div>
            <div class="conv-actions">
                <button class="conv-action-btn edit" title="Rename chat">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="conv-action-btn delete" title="Delete chat">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        // Row Click: Select Conversation
        item.addEventListener("click", (e) => {
            if (e.target.closest(".conv-action-btn")) return;
            selectConversation(conv.id);
            if (window.innerWidth <= 768) toggleSidebar(false);
        });

        // Edit Title Action
        const editBtn = item.querySelector(".conv-action-btn.edit");
        editBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            openRenameModal(conv.id);
        });

        // Delete Action
        const deleteBtn = item.querySelector(".conv-action-btn.delete");
        deleteBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            confirmDeleteConversation(conv.id);
        });

        elements.conversationsList.appendChild(item);
    });
}

async function selectConversation(convId) {
    if (currentConversationId === convId) return;

    currentConversationId = convId;
    renderConversationsList();

    const conv = conversationsList.find(c => c.id === convId);
    if (elements.currentChatTitle) {
        elements.currentChatTitle.textContent = conv ? conv.title : "Chat";
    }

    const token = localStorage.getItem("athena_token");
    try {
        const res = await fetch(`${API_BASE}/conversations/${convId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            const data = await res.json();
            renderConversationMessages(data.messages || []);
        }
    } catch (err) {
        console.error("Error loading chat messages:", err);
    }
}

function startNewChat(focusInput = true) {
    currentConversationId = null;
    if (elements.currentChatTitle) elements.currentChatTitle.textContent = "New Chat";
    renderConversationsList();

    if (elements.messagesContainer) elements.messagesContainer.innerHTML = "";
    if (elements.welcomeState) elements.welcomeState.classList.remove("hidden");
    if (elements.questionInput) {
        elements.questionInput.value = "";
        autoResizeInput();
        if (focusInput) elements.questionInput.focus();
    }
}

function renderConversationMessages(messages) {
    if (!elements.messagesContainer) return;
    elements.messagesContainer.innerHTML = "";

    if (!messages || messages.length === 0) {
        if (elements.welcomeState) elements.welcomeState.classList.remove("hidden");
        return;
    }

    if (elements.welcomeState) elements.welcomeState.classList.add("hidden");

    messages.forEach(msg => {
        // Historical messages don't have confidence/citations stored; pass defaults
        appendMessageBubble(msg.text, msg.sender, msg.sources || [], null, []);
    });

    scrollToBottom();
}

function appendMessageBubble(text, sender, sources = [], confidence = null, citations = []) {
    if (elements.welcomeState) elements.welcomeState.classList.add("hidden");

    const row = document.createElement("div");
    row.className = `message-row ${sender}`;

    if (sender === "user") {
        row.innerHTML = `
            <div class="bubble user-bubble">
                <div class="bubble-text">${escapeHtml(text).replace(/\n/g, "<br>")}</div>
            </div>
        `;
    } else {
        // ── Feature 1: Confidence badge ────────────────────────────────────
        let confidenceHtml = "";
        if (confidence && confidence.level) {
            const levelLabel = {
                high: "High confidence",
                medium: "Medium confidence",
                low: "Low confidence — verify manually"
            }[confidence.level] || "Unknown";
            const scoreText = confidence.score != null ? ` · ${Math.round(confidence.score * 100)}%` : "";
            const srcText = confidence.num_sources > 0
                ? ` · ${confidence.num_sources} source${confidence.num_sources !== 1 ? "s" : ""}`
                : "";
            confidenceHtml = `
                <div class="confidence-badge conf-${confidence.level}" title="Grounding score: ${confidence.score}">
                    <span class="conf-dot"></span>
                    <span>${levelLabel}${scoreText}${srcText}</span>
                </div>
            `;
        }

        // ── Feature 2: Sources HTML (clickable chips) ─────────────────────
        let sourcesHtml = "";
        if (sources && sources.length > 0) {
            const uniqueSources = [...new Set(sources)];
            const chips = uniqueSources.map(s => `
                <span class="source-chip" data-source="${escapeHtml(s)}" title="Click to inspect chunks for ${escapeHtml(s)}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <span>${escapeHtml(s)}</span>
                </span>
            `).join("");

            sourcesHtml = `
                <div class="sources-card">
                    <span class="source-label">Sources:</span>
                    ${chips}
                </div>
            `;
        }

        // ── Feature 2: Render markdown then linkify [N] citation markers ──
        const formattedText = linkifyCitations(formatMarkdown(text), citations);

        row.innerHTML = `
            <div class="athena-avatar-bubble">
                <img src="assets/logo-dark.png" alt="Athena AI" class="avatar-logo-img theme-adaptive-logo">
            </div>
            <div class="bubble athena-bubble">
                ${confidenceHtml}
                <div class="bubble-text">${formattedText}</div>
                ${sourcesHtml}
                <div class="message-actions">
                    <button class="copy-btn" title="Copy response">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span>Copy</span>
                    </button>
                </div>
            </div>
        `;

        // Copy button listener
        const copyBtn = row.querySelector(".copy-btn");
        if (copyBtn) {
            copyBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(text).then(() => {
                    const span = copyBtn.querySelector("span");
                    if (span) span.textContent = "Copied!";
                    setTimeout(() => { if (span) span.textContent = "Copy"; }, 2000);
                });
            });
        }

        // Clickable Source Chips: open chunk inspector
        row.querySelectorAll(".source-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const sourceName = chip.getAttribute("data-source");
                if (sourceName) openDocPreview(sourceName);
            });
        });

        // Feature 2: Clickable [N] citation superscripts
        row.querySelectorAll(".cite-ref").forEach(ref => {
            const activateCitation = (e) => {
                if (e) e.stopPropagation();
                const citId = parseInt(ref.getAttribute("data-cit-id"), 10);
                const cit = (citations || []).find(c => c.id === citId);
                if (cit) {
                    openCitationPanel(cit);
                } else {
                    // Fallback: if citation object not matched by id, synthesize from available chunk info
                    console.warn(`Citation [${citId}] details not found in metadata`);
                }
            };

            ref.addEventListener("click", activateCitation);
            ref.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    activateCitation(e);
                }
            });
        });
    }

    elements.messagesContainer.appendChild(row);
    scrollToBottom();
}

async function handleSendMessage(e) {
    e.preventDefault();
    if (isGenerating) return;

    const question = elements.questionInput.value.trim();
    if (!question) return;

    const token = localStorage.getItem("athena_token");
    if (!token) return handleAuthError();

    // Trigger Antigravity particle impulse from send button
    if (window.antigravity && typeof window.antigravity.triggerImpulse === "function" && elements.sendBtn) {
        const rect = elements.sendBtn.getBoundingClientRect();
        window.antigravity.triggerImpulse(rect.left + rect.width / 2, rect.top + rect.height / 2);
    }

    elements.questionInput.value = "";
    autoResizeInput();

    appendMessageBubble(question, "user");

    isGenerating = true;
    if (elements.typingIndicator) elements.typingIndicator.classList.remove("hidden");
    if (elements.sendBtn) elements.sendBtn.disabled = true;
    scrollToBottom();

    try {
        const payload = {
            question: question,
            conversation_id: currentConversationId
        };

        const res = await fetch(`${API_BASE}/query`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (res.status === 401) return handleAuthError();

        const data = await res.json();

        if (res.ok) {
            if (!currentConversationId && data.conversation_id) {
                currentConversationId = data.conversation_id;
                await loadConversations();
            }

            const activeConv = conversationsList.find(c => c.id === currentConversationId);
            if (activeConv && elements.currentChatTitle) {
                elements.currentChatTitle.textContent = activeConv.title;
            }

            // Feature 1 & 2: pass confidence + citations to the bubble renderer
            const confidence = {
                level: data.confidence_level || "low",
                score: data.confidence_score ?? 0,
                num_sources: data.num_sources ?? 0
            };
            const citations = data.citations || [];

            appendMessageBubble(data.answer, "athena", data.sources || [], confidence, citations);
            loadUserProfile();
        } else {
            appendMessageBubble(data.detail || "Sorry, I couldn't generate an answer right now.", "athena");
        }

    } catch (err) {
        console.error("Query request failed:", err);
        appendMessageBubble("Connection issue. Please verify backend status.", "athena");
    } finally {
        isGenerating = false;
        if (elements.typingIndicator) elements.typingIndicator.classList.add("hidden");
        if (elements.sendBtn) elements.sendBtn.disabled = false;
        scrollToBottom();
    }
}

async function handleFileUpload() {
    const file = elements.fileInput.files[0];
    if (!file) return;

    const token = localStorage.getItem("athena_token");
    if (!token) return handleAuthError();

    showAlert(`Uploading and feeding "${file.name}" to Athena...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/ingest`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` },
            body: formData
        });

        if (res.status === 401) return handleAuthError();

        const data = await res.json();

        if (res.ok) {
            showAlert(`✅ Successfully feeded and indexed "${data.filename}" (${data.chunks_added} chunks added).`);
            await loadKnowledgeStats();
            loadUserProfile();
            if (elements.kbModal && !elements.kbModal.classList.contains("hidden")) {
                loadKnowledgeDocuments();
            }
        } else {
            showAlert(`Upload failed: ${data.detail || "Could not process file"}`, "error");
        }
    } catch (err) {
        console.error("File upload error:", err);
        showAlert("Error connecting to server for file upload.", "error");
    } finally {
        elements.fileInput.value = "";
    }
}

/**
 * Rename Modal Logic
 */
let renamingConvId = null;

function openRenameModal(convId) {
    const targetId = convId || currentConversationId;
    if (!targetId) return;

    renamingConvId = targetId;
    const conv = conversationsList.find(c => c.id === targetId);
    if (elements.renameInput) {
        elements.renameInput.value = conv ? conv.title : "Chat";
    }
    if (elements.renameModal) {
        elements.renameModal.classList.remove("hidden");
        elements.renameInput.focus();
        elements.renameInput.select();
    }
}

function closeRenameModal() {
    renamingConvId = null;
    if (elements.renameModal) elements.renameModal.classList.add("hidden");
}

async function handleRenameSubmit(e) {
    e.preventDefault();
    if (!renamingConvId) return;

    const newTitle = elements.renameInput.value.trim();
    if (!newTitle) return;

    const token = localStorage.getItem("athena_token");

    try {
        const res = await fetch(`${API_BASE}/conversations/${renamingConvId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ title: newTitle })
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            closeRenameModal();
            if (renamingConvId === currentConversationId && elements.currentChatTitle) {
                elements.currentChatTitle.textContent = newTitle;
            }
            await loadConversations();
        } else {
            showAlert("Failed to rename conversation.", "error");
        }
    } catch (err) {
        console.error("Rename error:", err);
        showAlert("Failed to connect to server.", "error");
    }
}

async function confirmDeleteConversation(convId) {
    if (!confirm("Are you sure you want to delete this conversation?")) return;

    const token = localStorage.getItem("athena_token");

    try {
        const res = await fetch(`${API_BASE}/conversations/${convId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.status === 401) return handleAuthError();

        if (res.ok) {
            if (currentConversationId === convId) {
                currentConversationId = null;
            }
            await loadConversations();
            if (!currentConversationId) {
                startNewChat(false);
            }
            loadUserProfile();
        } else {
            showAlert("Failed to delete conversation.", "error");
        }
    } catch (err) {
        console.error("Delete error:", err);
        showAlert("Failed to connect to server.", "error");
    }
}

function scrollToBottom() {
    if (elements.chatScrollArea) {
        elements.chatScrollArea.scrollTop = elements.chatScrollArea.scrollHeight;
    }
}

let alertTimeout = null;
function showAlert(message, type = "success") {
    if (!elements.appAlert || !elements.alertMessage) return;

    elements.alertMessage.textContent = message;
    elements.appAlert.className = `app-alert ${type === "error" ? "error" : ""}`;
    elements.appAlert.classList.remove("hidden");

    if (alertTimeout) clearTimeout(alertTimeout);
    alertTimeout = setTimeout(() => hideAlert(), 5000);
}

function hideAlert() {
    if (elements.appAlert) elements.appAlert.classList.add("hidden");
}

function handleAuthError() {
    localStorage.removeItem("athena_token");
    localStorage.removeItem("athena_user");
    window.location.replace("login.html");
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);

    // Code blocks: ```language ... ```
    formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code: `code`
    formatted = formatted.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Headers
    formatted = formatted.replace(/^### (.*$)/gim, '<h3 style="color:var(--text-primary);font-size:15px;margin:12px 0 4px;font-weight:600;">$1</h3>');
    formatted = formatted.replace(/^## (.*$)/gim, '<h2 style="color:var(--text-primary);font-size:16px;margin:14px 0 6px;font-weight:600;">$1</h2>');

    // Bold: **text**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic: *text*
    formatted = formatted.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Unordered lists
    formatted = formatted.replace(/^\s*[-*]\s+(.+)$/gm, "<li>$1</li>");
    formatted = formatted.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");

    // Paragraphs
    formatted = formatted.split("\n\n").map(p => {
        if (p.startsWith("<pre>") || p.startsWith("<ul>") || p.startsWith("<ol>") || p.startsWith("<h2") || p.startsWith("<h3")) {
            return p;
        }
        return `<p>${p.replace(/\n/g, "<br>")}</p>`;
    }).join("");

    return formatted;
}

/**
 * ==========================================================================
 * Feature 2 — Citation Superscript Linkification & Panel
 * ==========================================================================
 */

/**
 * Replace plain [N] or multi-number [N, M] text markers in already-rendered
 * HTML with clickable <span class="cite-ref"> elements. Operates on HTML string,
 * ignoring HTML tags and code blocks.
 */
function linkifyCitations(html, citations = []) {
    if (!citations || citations.length === 0) return html;

    // Build a set of valid IDs so we only linkify real markers
    const validIds = new Set(citations.map(c => c.id));

    const parseCitationGroup = (groupText) => {
        const result = [];
        const parts = groupText.split(/[,;]+/);
        for (let part of parts) {
            part = part.trim();
            if (!part) continue;
            // Handle range format like "1-3" or "1 - 3"
            const rangeMatch = part.match(/^(\d+)\s*[-–—]\s*(\d+)$/);
            if (rangeMatch) {
                const start = parseInt(rangeMatch[1], 10);
                const end = parseInt(rangeMatch[2], 10);
                if (start <= end && end - start <= 10) {
                    for (let i = start; i <= end; i++) {
                        if (validIds.has(i)) result.push(i);
                    }
                }
            } else {
                const num = parseInt(part, 10);
                if (!isNaN(num) && validIds.has(num)) {
                    result.push(num);
                }
            }
        }
        return [...new Set(result)]; // deduplicate
    };

    // Matches [ followed by digits, commas, semicolons, spaces, hyphens, and ]
    return html.replace(/\[([\d\s,;\-–—]+)\]/g, (match, inner) => {
        const validNums = parseCitationGroup(inner);
        if (validNums.length === 0) return match;

        // Render each matched number as an adjacent clickable chip [2][4]
        return validNums
            .map(num => `<span class="cite-ref" data-cit-id="${num}" tabindex="0" role="button" aria-label="Citation ${num}">[${num}]</span>`)
            .join("");
    });
}

/** Open the citation panel with data from a citation object */
function openCitationPanel(citation) {
    if (!elements.citationPanel) return;

    // Populate panel content
    if (elements.citationRefBadge) elements.citationRefBadge.textContent = `[${citation.id}]`;
    if (elements.citationSourceName) elements.citationSourceName.textContent = citation.source || "Document";
    if (elements.citationLocation) elements.citationLocation.textContent = citation.location || "";
    if (elements.citationChunkText) elements.citationChunkText.textContent = citation.text || "";
    if (elements.citationOpenKbBtn) elements.citationOpenKbBtn.setAttribute("data-source", citation.source || "");

    // Show overlay + panel via animation classes
    elements.citationPanel.classList.remove("hidden");
    elements.citationOverlay.classList.remove("hidden");
    // Force reflow before adding active class so transition fires
    void elements.citationPanel.offsetWidth;
    elements.citationPanel.classList.add("active");
    elements.citationOverlay.classList.add("active");
}

/** Close the citation panel */
function closeCitationPanel() {
    if (!elements.citationPanel) return;
    elements.citationPanel.classList.remove("active");
    elements.citationOverlay.classList.remove("active");
    // Re-hide after transition completes
    setTimeout(() => {
        elements.citationPanel.classList.add("hidden");
        elements.citationOverlay.classList.add("hidden");
    }, 340);
}