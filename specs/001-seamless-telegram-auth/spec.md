# Feature Specification: Плавная аутентификация через Telegram (seamless-telegram-auth)

**Feature Branch**: `001-seamless-telegram-auth`  
**Created**: 2025-11-03  
**Status**: Draft  
**Input**: User description:

> Любой пользователь Telegram может начать взаимодействовать с ботом (sosenkibot)
>
> - Он может найти его самостоятельно в поиске контактов Телеграм (не требует реализации)
> - Ему могут переслать сообщение от него друзья в личном сообщении (не требует реализации)
> - Он может начать взаимодействовать с sosenkibot, находясь в одной группе, куда бот был предварительно добавлен
>
> Для начала нам нужно реализовать самые базовые истории:
>
> - Выдача приветственного сообщения от sosenkibot с кнопкой открытия Mini App
> - При попытке открытия MiniApp происходит Аутентификация пользователя SOSenki - существует ли пользователь с таким Telegram id в нашей системе?
> - Если Пользователя пока нет, бот предлагает сформулировать Сообщение (например, Интересуюсь покупкой, Хотел бы арендовать, Я хозяин дома 13) для Запроса на подключение к системе
> - В настройках SOSenki есть Telegram идентификатор чата Администраторской группы (Admin Group Chat), который по умолчанию равен Telegram ID первого Администратора (создателя бота)
> - sosenkibot отправляет Запрос от пользователя в Admin Group Chat с текстом Сообщения и кнопками Добавить / Отклонить
> - Ответом на сообщение боту Администратор может добавить его в систему или отклонить запрос
> - При добавлении Администратор сразу назначает Пользователю одну из Ролей (Administrator, Tenant, Owner, Investor)
> - Пользователь получает уведомление от бота об отказе или приветствует пользователя в системе
> - При открытии первой страницы Mini App Пользователь SOSenki видит Приветственный текст

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Открытие Mini App и быстрая проверка пользователя (Priority: P1)

Кратко: Пользователь нажимает кнопку в приветственном сообщении бота и пытается открыть Mini App. Система должна проверить, есть ли Telegram ID этого пользователя в базе SOSenki и либо сразу открыть приветственную страницу, либо предложить создать запрос на подключение.

Why this priority: это основной путь — позволяет пользователю впервые попасть в Mini App и определяет дальнейший поток взаимодействия.

Independent Test: отправить тестовое приветственное сообщение боту, нажать кнопку «Открыть Mini App» и проверить поведение в случае существующего/несуществующего пользователя.

Acceptance Scenarios:

1. Given: Telegram-пользователь получил приветственное сообщение от sosenkibot; When: нажимает кнопку открытия Mini App; Then: если Telegram ID связан с пользователем в системе — открывается первая страница Mini App с приветственным текстом и доступом к своему профилю.
2. Given: Telegram-пользователь нажал кнопку открытия Mini App; When: Telegram ID не найден в системе; Then: внутри Mini App пользователь видит интерфейс для формирования запроса на подключение (короткое текстовое сообщение) и кнопку «Отправить запрос».

---

### User Story 2 - Отправка запроса на подключение (Priority: P2)

Кратко: Если пользователя нет в системе, бот/mini app предлагает сформулировать короткое сообщение-запрос. После подтверждения запрос передаётся администраторам SOSenki.

Why this priority: без этого шага пользователь не сможет быть добавлен.

Independent Test: из аккаунта без соответствия в системе попытаться отправить запрос и убедиться, что администратор получает сообщение от бота с содержимым запроса и идентификатором Telegram.

Acceptance Scenarios:

1. Given: пользователь без учётной записи формирует сообщение; When: нажимает «Отправить запрос»; Then: бот подтверждает отправку и показывает сообщение «Ваш запрос отправлен администраторам». Администратор получает сообщение через Telegram с текстом запроса и кнопками «Добавить» / «Отклонить».

---

### User Story 3 - Обработка запроса администратором (Priority: P3)

Кратко: Администратор видит входящее сообщение от бота и может принять или отклонить запрос; при принятии администратор выбирает роль пользователя.

Why this priority: обеспечивает контроль доступа и назначение ролей — необходим для корректной работы системы.

Independent Test: отправить запрос от тестового Telegram-идентификатора, выбрать роль и подтвердить от имени одного из Администраторов — затем проверить, что пользователь получил уведомление о добавлении и назначенной роли.

Acceptance Scenarios:

1. Given: администратор получил запрос; When: администратор выбирает «Добавить» и выбирает роль (Administrator, Tenant, Owner, Investor); Then: система проверяет Администратора и создаёт пользователя с указанной ролью, бот отправляет пользователю приветственное сообщение с указанием роли.
2. Given: администратор выбирает «Отклонить»; When: подтверждает отклонение; Then: бот отправляет пользователю сообщение об отказе и причина (если указана) и помечает запрос как отклонённый.

---

### Edge Cases

- Пользователь отправил несколько одинаковых запросов подряд — система должна дедуплицировать запросы от одного Telegram ID и сообщать пользователю о том, что запрос уже отправлен.
- В чате администратора несколько администраторов нажали «Добавить» одновременно — только первый подтверждённый ответ должен создать пользователя; остальные — получат уведомление, что запрос уже обработан.
- Администратор не назначил роль — интерфейс не должен позволять завершить добавление без выбора одной из ролей.
- Пользователь указал недопустимый или оскорбительный текст в запросе — запрос принимается, но админам рекомендуется иметь возможность отклонить и указать причину.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Бот `sosenkibot` MUST отправлять приветственное сообщение с кнопкой «Открыть Mini App» для пользователей, которые взаимодействуют с ботом в личном чате или в группе, где бот присутствует.
- **FR-002**: При попытке открыть Mini App система MUST проверить наличие Telegram ID в базе SOSenki и вернуть результат проверки (существует / не существует).
- **FR-003**: Если Telegram ID не найден, пользователь MUST иметь возможность сформировать короткое текстовое сообщение-запрос (не более 280 символов) и отправить его администраторам через бота.
- **FR-004**: Бот MUST отправлять сообщение в Admin Group Chat с текстом запроса, идентификатором Telegram пользователя, ссылкой на его профиль и интерактивными действиями: «Добавить» и «Отклонить».
- **FR-005**: При выборе «Добавить» администратор MUST выбирать одну из предопределённых ролей: Administrator, Tenant, Owner, Investor. После подтверждения пользователь MUST быть создан в системе с указанной ролью.
- **FR-006**: При выборе «Отклонить» администратор MUST иметь возможность указать причину (необязательно); бот MUST уведомить пользователя об отказе.
- **FR-007**: После успешного добавления бот MUST отправить пользователю приветственное сообщение внутри Telegram с краткой информацией о роли и ссылкой/кнопкой для открытия Mini App.
- **FR-008**: Все сообщения от бота, связанные с созданием/отклонением запросов, MUST содержать уникальный идентификатор запроса для дальнейшего аудита.
- **FR-009**: Система MUST предотвращать дублирование запросов от одного Telegram ID.

### Key Entities *(include if feature involves data)*

- **TelegramUserCandidate**: временный объект запроса — содержит Telegram ID, текст запроса, timestamp, статус (pending/accepted/rejected), request_id.
- **AdminAction**: запись действия администратора — кто обработал запрос, время, выбранная роль или причина отклонения.
- **SOSenkiUser**: существующий пользователь в системе — имеет связь с Telegram ID после добавления и поле role (Administrator, Tenant, Owner, Investor).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% случаев открытия Mini App от пользователя с существующим Telegram ID сразу отображают приветственную страницу (функциональная корректность).
- **SC-002**: 95% отправленных пользователем запросов доставляются администраторам и помечаются как «в обработке» в течение 30 секунд.
- **SC-003**: 90% запросов получают ответ (принят/отклонён) от администратора в течение 24 часов.
- **SC-004**: Дублированные запросы от одного Telegram ID в 100% случаев.
- **SC-005**: Пользователи, добавленные администратором, получают уведомление о добавлении в 100% случаев и могут открыть Mini App и увидеть приветственный текст.

---

### Assumptions

- Администраторы SOSenki имеют отдельный (существующий) админ-чат/способ получения сообщений от бота.
- Минимально жизнеспособная версия не включает автоматическое подтверждение запроса без участия администратора.
- Максимальная длина сообщения-запроса — 280 символов (разумное ограничение для коротких заявок).

### Notes

- Спецификация фокусируется на пользовательских сценариях и требованиях; детали реализации (протоколы, API, хранилище) намеренно опущены и будут определены в планировании/техническом задании.

# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
