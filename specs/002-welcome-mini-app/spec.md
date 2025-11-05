# Feature Specification: Welcome Mini App for Approved Users

**Feature Branch**: `002-welcome-mini-app`  
**Created**: 2025-11-05  
**Status**: Draft  
**Input**: User description: "When Administrator approves access to SOSenki, user receives Welcome message with Button to Open App. It's a Telegram Mini App with minimalistic and sleek design (Apple style) inspired by nature colors - Pines, Water and Sand. Mini App checks that Telegram User is registered in SOSenki. Non-registered users see 'Access is limited' message with instruction to send /request. Registered users see Welcome message and Menu with Actions: Rule, Pay, Invest."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Approved User Receives Welcome Message with App Link (Priority: P1)

An approved client receives a Welcome message from the SOSenki bot via Telegram containing a button to open the SOSenki Mini App. This message is sent immediately after the administrator approves their access request. The user can tap the button to launch the Mini App within Telegram.

**Why this priority**: This is the critical entry point for newly approved users. Without the welcome message and app link, approved users have no way to access SOSenki. This is the primary value delivery mechanism for the approval workflow.

**Independent Test**: Can be fully tested by: (1) approving a user's request (from 001-request-approval), (2) verifying the user receives a Welcome message containing an "Open App" button within 5 seconds, and (3) verifying the button launches the Telegram Mini App.

**Acceptance Scenarios**:

1. **Given** a user's access request has been approved by an administrator, **When** the approval is processed, **Then** the user receives a Welcome message from the SOSenki bot within seconds containing text describing access has been granted.
2. **Given** the Welcome message is delivered to the approved user, **When** the user opens the message, **Then** a prominent button labeled "Open App" or similar is visible and clickable.
3. **Given** the user taps the "Open App" button, **When** the button is activated, **Then** the Telegram Mini App launches within the Telegram client displaying the SOSenki interface.

---

### User Story 2 - Registered User Views Welcome and Main Menu (Priority: P1)

When a registered (approved) user opens the SOSenki Mini App, they are greeted with a welcome message and presented with a main navigation menu featuring three primary actions: Rule, Pay, and Invest. The interface uses a minimalistic, sleek design inspired by Apple's design philosophy with nature-inspired colors (pines, water, sand).

**Why this priority**: This is the core UX experience for approved users. The main menu is the hub from which users navigate all SOSenki features. Without a functional main menu, the app provides no value beyond the welcome screen.

**Independent Test**: Can be fully tested by: (1) opening the Mini App as a registered user, (2) verifying welcome content is displayed, (3) verifying all three menu items (Rule, Pay, Invest) are visible and interactive, and (4) confirming the design is visually consistent and professional.

**Acceptance Scenarios**:

1. **Given** a registered user has opened the SOSenki Mini App, **When** the app loads, **Then** a welcome message is displayed acknowledging the user and confirming their access status.
2. **Given** the welcome content is displayed, **When** the user views the main interface, **Then** a navigation menu with exactly three options is visible: Rule, Pay, and Invest.
3. **Given** a menu option is displayed, **When** the user observes the interface, **Then** all menu items are visually distinct, interactive (appear clickable), and follow a minimalistic design with nature-inspired colors (forest green/pine, aqua/water, beige/sand).
4. **Given** the app is open, **When** the user interacts with menu items, **Then** each menu item responds to interaction (hover, tap) with appropriate visual feedback.

---

### User Story 3 - Non-Registered User Sees Access Denied Message (Priority: P2)

When a user who is not registered/approved in SOSenki opens the Mini App via a link (e.g., from a bot message or external reference), they are presented with an "Access is limited" message explaining they do not have access. The message includes clear instructions to send `/request` to the SOSenki bot to request access.

**Why this priority**: This handles the edge case where non-registered users encounter the Mini App. While not the primary flow, it provides important user guidance and prevents confusion. This is secondary to the approved user experience but important for user satisfaction.

**Independent Test**: Can be fully tested by: (1) opening the Mini App Mini App as a non-registered user, (2) verifying the "Access is limited" message is displayed, (3) confirming instructions to send /request are clear and visible, and (4) ensuring no main menu or app features are accessible.

**Acceptance Scenarios**:

1. **Given** a user who is not registered in SOSenki opens the Mini App, **When** the app loads, **Then** an "Access is limited" message is displayed prominently.
2. **Given** the access denied state is displayed, **When** the user views the message, **Then** clear instructions are provided stating "Send /request to the SOSenki bot to request access" or similar language.
3. **Given** the limited access message is shown, **When** the user observes the interface, **Then** the main menu (Rule, Pay, Invest) and other app features are not accessible or visible.
4. **Given** a non-registered user opens the app, **When** the page loads, **Then** the message includes a button or link to return to Telegram or close the app gracefully.

---

### Edge Cases

- What happens if a user's registration status changes (approved, then later revoked) while they have the Mini App open?
- How does the system handle the case where a user's Telegram ID becomes invalid or the user deletes their Telegram account?
- What happens if the Mini App is accessed via a shared link from an approved user?
- How does the system determine and verify a user's registration status during Mini App initialization?
- What happens if the Mini App fails to load or encounters a network error when checking registration status?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST send a Welcome message to the client within 5 seconds of approval being granted by an administrator (extends 001-request-approval).
- **FR-002**: Welcome message MUST include a button/link labeled "Open App" that launches the SOSenki Telegram Mini App.
- **FR-003**: System MUST host the SOSenki Mini App accessible via a deeplink from the Telegram bot that can be triggered by the "Open App" button.
- **FR-004**: Mini App MUST verify the user's registration status in SOSenki upon loading (check if their Telegram ID is in the approved/registered users list).
- **FR-005**: Mini App MUST display a welcome message and navigation menu for registered users with exactly three options: Rule, Pay, and Invest.
- **FR-006**: Mini App MUST display an "Access is limited" message for non-registered users with instructions to send `/request` to request access.
- **FR-007**: Mini App MUST prevent non-registered users from accessing any menu items or app features beyond the access denied message.
- **FR-008**: Mini App interface MUST use a minimalistic design consistent with Apple design principles (clean layouts, ample whitespace, intuitive interactions).
- **FR-009**: Mini App color scheme MUST incorporate nature-inspired colors: forest green/pine tones, aqua/water tones, and beige/sand tones for a cohesive natural aesthetic.
- **FR-010**: Mini App MUST gracefully handle errors (network failures, invalid Telegram IDs, database issues) and display user-friendly error messages.
- **FR-011**: Mini App MUST store or cache the user's registration status locally to enable faster subsequent loads (while maintaining accuracy).

### Key Entities

- **RegisteredUser**: Represents a user approved to access SOSenki, with attributes: telegram_id, registered_status (active/inactive/revoked), registration_timestamp, and associated client_request_id.
- **MiniAppSession**: Represents a session of a user's Mini App usage, with attributes: telegram_id, session_start_time, user_registration_status_at_load, last_activity_timestamp.
- **ApprovalNotification**: Represents the welcome notification message sent to newly approved users, with attributes: recipient_telegram_id, sent_timestamp, message_content, app_link_deeplink.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Approved users receive a Welcome message with an "Open App" button within 5 seconds of approval being processed.
- **SC-002**: The Mini App loads and displays the appropriate interface (registered user menu or access denied message) within 3 seconds of the user tapping "Open App" or opening the Mini App link.
- **SC-003**: 100% of registered users successfully see the welcome message and main menu (Rule, Pay, Invest) without errors when opening the Mini App.
- **SC-004**: 100% of non-registered users see the "Access is limited" message with clear instructions, preventing accidental access to features.
- **SC-005**: The Mini App interface meets Apple design standards: responsive layout, intuitive navigation, nature-inspired color palette visually appeals to 90% of user feedback (subjective UX metric).
- **SC-006**: The system correctly identifies and restricts/grants access based on registration status with 100% accuracy (no false positives or false negatives).
- **SC-007**: Menu items (Rule, Pay, Invest) are functional and respond to user interaction with visible feedback within 500ms.
- **SC-008**: The Mini App handles registration status changes (user approval revoked) and updates access accordingly on app reload or refresh.

## Assumptions

- The Telegram Mini App platform (Telegram Web App API) is available and functional; deployment leverages Telegram's Mini App infrastructure.
- User registration status is persisted in the SOSenki database (connected to 001-request-approval) and can be queried by the Mini App backend.
- The Mini App backend has access to user Telegram IDs from the Telegram API (via the client-side WebApp bridge).
- The approval notification message can be sent to users automatically upon approval (feature extends 001-request-approval workflow).
- Color values and design assets (nature-inspired palette) will be defined during design/implementation phase.
- Nature-inspired colors are interpreted as: Pine (forest green ~#2D5016), Water (aqua/teal ~#0099CC), Sand (beige ~#D4A574) as reasonable defaults.
- No additional authentication beyond Telegram ID is required; Telegram ID is the primary identity.
- The Mini App does not require persistent login; the user is authenticated via Telegram's Mini App client context.
- Rule, Pay, and Invest are placeholder menu items; their specific functionality is defined in future features and not part of this specification.

## Out of Scope

- Functional implementation of Rule, Pay, or Invest menu items (only menu structure and navigation)
- User profile management or settings within the Mini App
- Advanced design customization or theme selection
- Integration with third-party analytics or tracking (beyond basic functionality monitoring)
- Mobile app or native iOS/Android applications
- Multi-language support or localization
- Dark mode or alternative themes
