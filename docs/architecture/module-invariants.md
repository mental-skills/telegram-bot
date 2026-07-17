# Архитектурные инварианты модулей

## Текущий модуль

- Audience: `parents`
- Публичный `module_id`: `parents_football_competition`
- Название: «Родитель на соревнованиях»
- Текущий runtime registry/storage ID: `football_parent_mvp`

Публичная идентичность не равна legacy-ключу хранения. До отдельной контролируемой
миграции PostgreSQL существующие значения `TrainerSession.module_id` не изменяются.

## Legacy storage keys и route mode

Оба legacy-ключа принадлежат одному публичному модулю:

| Storage key | Public module_id | route_mode |
|---|---|---|
| `football_parent_mvp` | `parents_football_competition` | `full` |
| `football_parent_standalone` | `parents_football_competition` | `standalone` |

`route_mode` описывает способ запуска ситуации, а не отдельный продукт или модуль.
Standalone не продолжает следующий сценарий автоматически, не завершает full route
и не меняет его progress.

## Правила изоляции прогресса

1. Каждая `TrainerSession` относится ровно к одному storage `module_id`.
2. Поиск активных, последних и завершённых сессий выполняется с фильтрами по модулю.
3. История выбора связана с сессией через `session_id` и не анализируется без проверки
   module identity этой сессии.
4. Completion, reset и номер попытки принадлежат storage-модулю сессии.
5. Переход разрешён только через registry, соответствующий текущему модулю.
6. Неизвестный storage module ID отклоняется контролируемой ошибкой.

## Роль scenario_catalog

`content/scenario_catalog.json` определяет `module_id`, `start_scenario_id`, состав и
порядок включённых ситуаций. Число ситуаций является свойством каталога, а не
глобальным правилом продукта.

Следующая ситуация определяется registry/catalog. Full route считается завершённым,
когда `registry.next_scenario_id(current_scenario_id)` возвращает `None`. Нельзя
определять завершение по номеру 7, суффиксу `_07`, длине каталога или конкретному
`scenario_id`. Узел `module_completion` из утверждённого JSON отображается только
после проверки этого условия.

## API-контракт

API аддитивно возвращает:

- публичный `module_id`;
- `route_mode`: `full` или `standalone`.

Legacy storage IDs клиенту не раскрываются. Существующие поля API сохраняются.

## Границы MVP

Полноценные `ModuleContext`, общий каталог нескольких модулей, таблицы modules/audiences
и миграция перегруженного поля `TrainerSession.module_id` вводятся только при появлении
второго реального модуля.
