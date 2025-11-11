# Feature Specification: Client Request Approval Workflow

**Feature Branch**: `001-request-approval`  
**Created**: 2025-11-04  
**Status**: Draft  
**Input**: User description: "Potential client of SOSenki housing and user of Telegram sends a /request with message 'Please give me access to SOSenki' to 'SG_SOSenki_Bot' Telegram bot. Bot sends this request to Administrator of SOSenki with predefined telegram_id. Administrator replies to this request with Approve or Reject. If Reject - bot sends to the user Rejection message. If Approve - bot sends Welcome message to the new client"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Client Submits Access Request (Priority: P1)

A potential client discovers the SOSenki bot and sends a `/request` command with the message "Please give me access to SOSenki" to initiate the access approval workflow. The client expects confirmation that their request was received.

**Why this priority**: This is the entry point for all new clients. Without a functioning request submission mechanism, no clients can onboard. This is the critical foundation of the feature.

**Independent Test**: Can be fully tested by: (1) sending `/request` command to bot, (2) verifying request is recorded with client's Telegram ID and timestamp, and (3) confirming client receives acknowledgment that their request was submitted.

**Acceptance Scenarios**:

1. **Given** a user has discovered the SG_SOSenki_Bot, **When** the user sends `/request` with message "Please give me access to SOSenki", **Then** the system records the request with the user's Telegram ID, message content, and timestamp, and the user receives a confirmation message.
2. **Given** a user sends a `/request` command, **When** the request is stored, **Then** the request becomes available to administrators for review within seconds.
3. **Given** a user sends `/request`, **When** the request processing encounters no errors, **Then** the user receives a human-readable confirmation (e.g., "Your request has been received and is pending review").

---

### User Story 2 - Administrator Reviews and Approves Request (Priority: P1)

An administrator with predefined Telegram ID receives the client's request notification and can respond with either "Approve" or "Reject". Upon approval, the system sends a welcome message to the client, granting them access to SOSenki.

**Why this priority**: This is the core approval mechanism. Without it, requests have nowhere to go and clients cannot be onboarded. This directly enables the feature's primary value.

**Independent Test**: Can be fully tested by: (1) submitting a request as a client, (2) administrator receiving notification with request details, (3) administrator sending "Approve" response, (4) verifying client receives welcome message and system grants access.

**Acceptance Scenarios**:

1. **Given** a client request exists and is pending, **When** the administrator sends "Approve" in response to the notification, **Then** the system marks the request as approved and immediately sends a welcome message to the client.
2. **Given** a client request exists, **When** the administrator sends "Approve", **Then** the system grants the client access to SOSenki (marks their account as active/approved in the system).
3. **Given** an administrator approves a request, **When** the welcome message is sent to the client, **Then** the message clearly explains that access has been granted and provides basic next steps or usage instructions.

---

### User Story 3 - Administrator Rejects Request (Priority: P2)

An administrator reviews a client request and determines it should be rejected (e.g., insufficient information, duplicate account, policy violation). The administrator responds with "Reject", and the system notifies the client with a rejection message explaining the decision.

**Why this priority**: Rejection is important for managing access control and preventing unauthorized or problematic requests. However, the happy path (approval) is the primary use case. Rejection handling is essential but secondary to approval workflows.

**Independent Test**: Can be fully tested by: (1) submitting a request as a client, (2) administrator sending "Reject" response, (3) verifying client receives rejection message with explanation, and (4) confirming no access is granted to the client.

**Acceptance Scenarios**:

1. **Given** a client request exists and is pending, **When** the administrator sends "Reject" in response to the notification, **Then** the system marks the request as rejected.
2. **Given** an administrator rejects a request, **When** the rejection is processed, **Then** the system sends a rejection message to the client within seconds.
3. **Given** a client receives a rejection message, **When** the rejection is delivered, **Then** the message is professional and explains that their request was not approved (specific reason for rejection is not required in this version).

---

### Edge Cases

- What happens when an administrator responds with neither "Approve" nor "Reject" (e.g., "Maybe later", typo, or other text)?
- How does the system handle a request if the client's account is already active or previously approved?
- What happens if a request remains unanswered for an extended period (e.g., 30 days)? Should notifications be resent or requests auto-expire?
- How does the system behave if the administrator's predefined Telegram ID is invalid or the admin account becomes inactive?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept `/request` commands from any Telegram user and store the request with the user's Telegram ID, message content, timestamp, and request status (pending/approved/rejected).
- **FR-002**: System MUST forward client requests to the administrator with a Telegram ID specified in the configuration.
- **FR-003**: System MUST accept "Approve" or "Reject" responses from the administrator replying to request notifications.
- **FR-004**: System MUST send a welcome message to the client when their request is approved, indicating access has been granted.
- **FR-005**: System MUST send a rejection message to the client when their request is rejected.
- **FR-006**: System MUST persist request records (client ID, message, timestamp, status, admin response) in durable storage for audit purposes.
- **FR-007**: System MUST prevent duplicate/redundant messages: the same client cannot have multiple pending requests simultaneously (previous request must be resolved first).
- **FR-008**: System MUST handle the case where the administrator's response happens offline or with delay; the request state MUST remain consistent.

### Key Entities

- **ClientRequest**: Represents a client's access request with attributes: client_telegram_id, request_message, submitted_timestamp, status (pending/approved/rejected), admin_telegram_id (who responds), response_timestamp, response_message.
- **Administrator**: Represents an admin user with a predefined Telegram ID authorized to approve/reject requests.
- **Client**: Represents a user applying for access with at minimum: telegram_id, initial request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New clients can submit an access request via `/request` command and receive confirmation within 2 seconds.
- **SC-002**: Administrator receives request notification containing client Telegram ID, request message, and timestamp within 3 seconds of client submission.
- **SC-003**: Administrator can approve a request and the client receives a welcome message within 5 seconds of the admin's approval response.
- **SC-004**: Administrator can reject a request and the client receives a rejection message within 5 seconds of the admin's rejection response.
- **SC-005**: 100% of client requests are successfully stored and retrievable for audit purposes (no lost requests).
- **SC-006**: All request state transitions (pending → approved/rejected) are atomic and consistent; no race conditions or duplicate messages occur.
- **SC-007**: The system successfully handles administrator responses with no error messages surfaced to the admin or client.

## Assumptions

- The administrator's Telegram ID is stored in the project configuration (e.g., environment variable, config file) and is valid.
- "Approve" and "Reject" responses are exact matches (case-insensitive is reasonable but not required in this version).
- Client requests are expected to be simple text messages; no complex data structures are needed for this MVP.
- The Telegram bot is already running and can send/receive messages (this feature assumes bot infrastructure exists).
- Request storage can use the project's standard database (SQLite per constitution).
- No authentication beyond Telegram ID is required for clients to submit requests (Telegram ID is the identity).

## Out of Scope

- Bulk approval/rejection workflows
- Request filtering or search functionality for administrators
- Request expiration or automatic cleanup
- Email or SMS notifications (Telegram only)
- Request modification after submission
- Appeal or resubmission workflows
