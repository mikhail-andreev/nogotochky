# SDD - Платформа онлайн-записи на услуги (MVP)

## Цель документа
Описать дизайн минимальной системы для трех интерфейсов (витрина, кабинет мастера, админ-панель) с одним бэкендом и БД.

## Технологические решения (MVP)
- Backend: Django.
- Frontend: Django templates (server-side rendering).
- DB: SQLite.
- Dev-среда: разворачивание через `docker compose`.
- Порт: 8000.
- Админ-панель: встроенный Django Admin.

## Допущения MVP
- Нет проверки контактов посетителя.
- Нет платежей/подписок.
- Нет внешних интеграций.
- В MVP у мастера одна карточка салона/клиники (один мастер = один салон).

## Архитектура
- `API/Backend`: один сервис (Django), который:
  - обслуживает REST API;
  - предоставляет админ-панель (рекомендуется Django Admin как MVP-админка).
- `Frontends`: 3 веб-интерфейса:
  - витрина (public);
  - кабинет мастера (auth);
  - админ-панель (admin).

Примечание: в MVP админ-панель целесообразно реализовать как Django Admin (это быстрее и закрывает требования PRD). Отдельный SPA для админки можно добавить позже.

## Dev-окружение (docker compose)
Dev-окружение должно подниматься одной командой через `docker compose` и включать как минимум:
- контейнер `api` (Django + зависимости);
- volume/маунт для файла SQLite, чтобы данные не терялись между перезапусками.

Опционально (если фронтенды отдельными приложениями): контейнеры для витрины/кабинета/админки.

## Модель данных (MVP)
Ниже — логическая модель. В реализации на Django рекомендуется:
- использовать встроенную модель пользователя (или кастомную),
- роль хранить в `User.role`,
- профиль мастера вынести в `MasterProfile` (OneToOne).

### User
- id
- email
- password_hash
- role: `MASTER` | `ADMIN`
- created_at, updated_at

### MasterProfile
- id
- user_id (FK -> User.id, unique)
- display_name
- slug (unique, человекочитаемый URL, например `anna-nails`)
- phone
- bio
- created_at, updated_at

### Salon
- id
- owner_user_id (FK -> User.id)  // владелец-мастер
- name
- address
- description
- phone
- created_at, updated_at

### Service
- id
- owner_user_id (FK -> User.id)  // мастер
- salon_id (FK -> Salon.id)
- name
- duration_min
- price
- description
- is_active

### ScheduleSlot
- id
- owner_user_id (FK -> User.id)  // мастер
- start_at (datetime)
- end_at (datetime)
- status: `AVAILABLE` | `BOOKED` | `BLOCKED`

### Booking
- id
- owner_user_id (FK -> User.id)  // мастер
- service_id (FK -> Service.id)
- slot_id (FK -> ScheduleSlot.id, unique)  // начальный слот
- booked_slots (M2M -> ScheduleSlot)  // все забронированные слоты (для мульти-слот услуг)
- client_name
- client_phone
- notes (nullable)
- status: `CREATED` | `CANCELLED` (минимум для MVP)
- created_at

Инварианты согласованности (важно для предотвращения "кривых" данных):
- `Service.owner_user_id == Booking.owner_user_id`.
- `ScheduleSlot.owner_user_id == Booking.owner_user_id`.
- `Booking.slot_id` уникален (защита от двойной записи).

## API (REST, MVP)
Набор эндпоинтов описан для варианта с REST API (DRF). Если UI будет сервер-рендером, маршруты могут отличаться, но логика и права — те же.

### Auth
- POST `/auth/register` (master)
- POST `/auth/login`
- POST `/auth/logout`

### Master cabinet (role: MASTER)
- GET `/me`
- PUT `/me`

Salon:
- POST `/salon` (создать/инициализировать, если еще нет)
- GET `/salon`
- PUT `/salon`

Services:
- POST `/services`
- GET `/services`
- PUT `/services/{id}`
- DELETE `/services/{id}`

Schedule:
- POST `/schedule/slots` (создать слот/слоты)
- GET `/schedule/slots?from=&to=`
- DELETE `/schedule/slots/{id}`

Bookings:
- GET `/bookings`
- GET `/bookings/{id}`
- PATCH `/bookings/{id}` (например, отмена)

### Storefront (public)

- GET `/masters/` — каталог мастеров (мастера с доступными слотами + все мастера)
- GET `/masters/{slug}/` — страница мастера (профиль + услуги)
- GET `/masters/{slug}/slots/?service=N` — доступные слоты (ближайшие 2 недели, фильтрация по длительности услуги)
- GET `/masters/{slug}/book/?service=N&slot=N` — форма записи
- POST `/masters/{slug}/book/` — создание записи (`service_id` + `slot_id` + контакты)
- GET `/masters/{slug}/book/success/?booking=N` — подтверждение записи

### Admin (role: ADMIN)
Если используем Django Admin, то REST-эндпоинты ниже не обязательны.
Если админ-панель отдельная (SPA), то нужны:
- GET `/admin/masters`
- PATCH `/admin/masters/{id}` (например, блокировка)
- GET `/admin/salons`
- PATCH `/admin/salons/{id}`
- GET `/admin/services`
- GET `/admin/bookings`
- PATCH `/admin/bookings/{id}`
- DELETE `/admin/bookings/{id}`

## Создание записи (транзакционность)
Требование: слот нельзя забронировать дважды.

### Объединение слотов
Если длительность услуги превышает длительность одного слота, система автоматически объединяет несколько последовательных свободных слотов. Например, если слоты по 30 минут, а услуга длится 90 минут — бронируются 3 последовательных слота.

Рекомендуемый алгоритм:
1. Получить `service_id` и `slot_id` (начальный слот).
2. Рассчитать, сколько слотов нужно для услуги.
3. Найти последовательные слоты начиная с выбранного, проверить что все `AVAILABLE`.
4. Проверить что услуга и все слоты принадлежат одному мастеру (`owner_user_id`).
5. В транзакции:
   - создать `Booking` (с привязкой к начальному слоту);
   - обновить статус всех занятых слотов `ScheduleSlot.status = BOOKED`.
6. При гонке опираться на `unique(slot_id)` в `Booking` и корректно обработать `IntegrityError` (вернуть 409/ошибку занятости слота).

Примечание про SQLite: конкурентная запись ограничена, но уникальный индекс + транзакция все равно обязательны.

### Отмена записи

При отмене записи (`Booking.cancel()`) все связанные слоты из `booked_slots` возвращаются в статус `AVAILABLE`.

## Тестирование

72 автотеста (`python manage.py test`), покрывающие:

- **accounts**: User модель, роли, регистрация (с авто-логином), логин/логаут, сигнал создания MasterProfile.
- **masters**: модели (slug-генерация, уникальность), MasterRequiredMixin (анонимы, ADMIN-роль), CRUD views (профиль, салон, услуги), изоляция данных между мастерами.
- **schedule**: модели (ScheduleSlot, Booking), отмена одиночной и мульти-слот записи, SlotCreateForm (валидация, генерация), views (CRUD слотов, защита забронированных, отмена записи).
- **showcase**: каталог мастеров (фильтрация по слотам), страница мастера (услуги, неактивные скрыты, 404), слоты (доступные, забронированные, фильтр по длительности услуги), `_filter_bookable_slots` (unit-тесты), бронирование (одинарное, мульти-слот, занятый слот, нехватка слотов), страница подтверждения.

## Frontend и дизайн-система

### Технологии

- **CSS-фреймворк**: Bootstrap 5.3 (CDN) + кастомный `style.css`
- **Шрифт**: Inter (Google Fonts)
- **JavaScript**: только Bootstrap bundle (без кастомного JS)

### Дизайн-система (CSS-переменные)

Все дизайн-токены определены в `:root` файла `static/css/style.css`:

- Цвета: `--color-primary` (#b07d62, терракот), `--color-bg` (#faf9f7, off-white), семантические цвета
- Типография: `--font-size-*` (xs..hero), `--font-family` (Inter)
- Spacing: `--space-*` (xs..3xl)
- Радиусы: `--radius-*` (sm, md, lg, full)
- Тени: `--shadow-*` (sm, md, lg)

### Адаптивность

- Таблицы в кабинете (услуги, слоты, записи) заменяются карточками на `< 768px`
- Реализация: `d-none d-md-block` (таблица) + `d-md-none` (карточки)
- Breakpoints: 575px (small), 767px (mobile), 991px (tablet)

### Шаблоны (21 файл)

Все шаблоны наследуют `base.html` через `{% extends 'base.html' %}`.
Блоки: `title`, `extra_css`, `content`, `extra_js`.

## Аутентификация и авторизация
- Master и Admin входят по email+паролю.
- Пароли хэшируются стандартными механизмами Django.
- Сессии/куки или JWT — на выбор реализации; для веб-интерфейсов проще cookie-based auth.
- RBAC:
  - MASTER имеет доступ только к своим данным (`owner_user_id`).
  - ADMIN имеет доступ ко всем данным.

## Наблюдаемость (MVP)
- Структурированные логи запросов/ошибок API.
- Логирование действий админа (минимум: кто/что/когда).

## Развертывание
- MVP: один контейнер Django + файл SQLite.
- После MVP: переход на PostgreSQL (без изменения продуктовых требований) и выделение сервисов при необходимости.
