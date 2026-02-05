# CLAUDE.md - Инструкции для Claude Code

## Структура проекта

- `apps/backend/` — Django-приложение (основной код бэкенда)
- `PRD.md` — Product Requirements Document
- `SDD.md` — Software Design Document

## Правила работы

### Код и структура
- Работать с backend из `apps/backend/`
- Не менять структуру каталогов без согласования
- Не перезаписывать данные пользователя и не удалять файлы без запроса

### Документация
- При изменениях в коде обновлять `PRD.md` и `SDD.md`, чтобы документация соответствовала реализации

### Разработка и тестирование
- Для dev использовать Docker Compose
- После изменения кода запускать сервисы через Docker Compose
- Проверять работоспособность с помощью curl

### Git
- `git push` делаем только по прямому указанию пользователя

## Технологический стек (MVP)

- Backend: Django + Django templates (SSR)
- DB: SQLite
- Админ-панель: Django Admin
- Dev-среда: Docker Compose
- Порт: 8000

## Ключевые команды

```bash
# Запуск dev-окружения
docker compose up

# Проверка работоспособности
curl http://localhost:8000/
```
