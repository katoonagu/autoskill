# The Blueprint Outreach Master Report

Этот файл сводит в одно место весь текущий pipeline по The Blueprint career:
- full archive parser по career-разделу
- shortlist reducer по сегментам B/C/D/E
- stage-2 people targets
- stage-3 route resolver
- ручную пометку потенциального мусора в auto-search выдаче

Собрано: `2026-04-15T16:23:14.847837+00:00`

## Метод

### Шаг 1. Полный сбор
- Из career-архива The Blueprint берутся все brand pages и все вакансии брендов.
- Затем архив схлопывается до company-level карточек: бренд, роли, вакансии, e-mail, источники.

### Шаг 2. Редукция до рабочей shortlist
- Оставляем только сегменты `B/C/D/E`.
- Вырезаем media / culture / non-target сущности.
- Оставляем только свежие marketing / PR / content сигналы.

### Шаг 3. Приоритизация
- Смотрим не на величину бренда, а на `why now`: свежий hiring, кадровая перестановка, запуск категории, founder-led доступность.
- Для `C/D` приоритет person-first. Для `B` — person-first при наличии имени, иначе person + brand route. Для `E` — role-first.

### Шаг 4. Person-route логика
- Сначала фиксируем buyer по роли.
- Потом ищем `ФИО + бренд` в открытом вебе.
- Потом Instagram/Telegram/site/email trail.
- Только после этого считаем, что маршрут контакта реально существует.

### Шаг 5. Фильтр мусора
- Если auto-search приносит `zhihu`, `baidu`, `reddit`, `support.google`, `youtube`, `stackoverflow` и похожий шум, эти результаты не считаются доказательством.
- В детальных карточках ниже такие находки либо вырезаны, либо помечены как `potential noise`.

## Snapshot

- Архив компаний: `2000`
- Shortlist после фильтрации: `81`
- Разбивка по сегментам: `{'E': 9, 'D': 3, 'B': 45, 'C': 24}`
- Активные top targets: `10`
- Wave split: `{'wave_1': 5, 'wave_2': 3, 'wave_3': 2}`
- Текущий stage-3 snapshot: `{'companies_scanned': 70, 'resolved_person_route': 5, 'resolved_brand_route': 1, 'partial': 4, 'unresolved': 60, 'error': 0}`

## Финальный порядок действий

### Wave 1
- `Don't Touch My Skin` — WRITE NOW — Адэль Мифтахова (Founder)
- `Befree` — ENRICH 10-15 MIN, THEN WRITE — Евгений Лагутин (Marketing Manager)
- `Ushatava` — WRITE NOW — Нино Шаматавa (Creative / Content Director, co-founder)
- `Emka` — WRITE NOW — Прохор Шаляпин (PR-менеджер)
- `Finn Flare` — ENRICH 10-15 MIN, THEN WRITE — Named HR bridge + marketing/pr mailbox (Bridge to marketing owner)

### Wave 2
- `Lamoda` — ENRICH 10-15 MIN, THEN WRITE — Brand / STM owner (name to confirm) (Private label / digital marketing)
- `Bork` — WRITE NOW — Brand / marketing owner via named Bork email (Brand or CRM marketing)
- `2Mood` — WRITE NOW — Полина Подплетенная (Co-owner)

### Wave 3
- `YuliaWave` — WRITE NOW — Юлия Василевская (Founder)
- `Бар «Ровесник»` — WRITE NOW — Александр Мартынов (Co-founder)

## Детально: кому писать и что писать

### 1. Don't Touch My Skin

- Verdict: `WRITE NOW`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_1`
- Score: `184`
- Почему сейчас: Идет найм руководителя отдела маркетинга. Это момент, когда founder и новый маркетинг-руководитель будут собирать новый стек подрядчиков.
- Кому писать первым: Адэль Мифтахова (Founder)
- Вход: person-first via Telegram, then brand Instagram and direct founder-related email trail
- Stage-3 snapshot: `resolved_person_route / high`
- Pitch angle: Skincare сейчас = короткие AI-ролики + ASMR-видео. Это наша сильная сторона. Плюс AI-музыка для бренда — у DTMS нет саунд-идентичности.
- Текущий gap: Через 2-4 недели обновить имя нового head of marketing и писать парой: founder + marketer.

Что писать:
- Тема: Don't Touch My Skin: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас идет найм руководителя отдела маркетинга.
- Оффер: Для Don't Touch My Skin здесь логично предложить Skincare сейчас = короткие AI-ролики + ASMR-видео. Это наша сильная сторона. Плюс AI-музыка для бренда — у DTMS нет саунд-идентичности..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Адэль Мифтахова (Founder)

Что уже найдено:
- Адэль Мифтахова (Founder): https://www.instagram.com/adeliamft/, https://t.me/donttouchmyface
- Official brand Instagram: https://www.instagram.com/dtmskin/
- Brand site: https://dtmskin.com/
- Fallback email: m.mitasova@fdroconsult.com
- Fallback email: igor.doubnov@dtmskin.com
- Fallback email: info@dtmskin.com
- Fallback email: cv@foamstore.ru

Доверенные ссылки:
- https://theblueprint.ru/career/brand/donttouchmyskin
- https://theblueprint.ru/career/38806
- https://theblueprint.ru/career/38518
- https://theblueprint.ru/career/37595
- https://theblueprint.ru/career/35231
- https://theblueprint.ru/career/34148
- https://theblueprint.ru/career/32306
- https://theblueprint.ru/career/30700

Если добивать ещё 10 минут:
- "Don't Touch My Skin" "руководитель отдела маркетинга"
- "Адэль Мифтахова" Instagram
- "Адэль Мифтахова" Telegram

Potential noise, не использовать как доказательство:
- https://outlook.live.com/MAIL/?prompt=select_account

### 2. Befree

- Verdict: `ENRICH 10-15 MIN, THEN WRITE`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_1`
- Score: `171`
- Почему сейчас: Новый marketing manager Евгений Лагутин. Это лучший триггер на тест нового продакшна в первые 30-60 дней.
- Кому писать первым: Евгений Лагутин (Marketing Manager)
- Вход: person-first via industry mentions, then brand Telegram fallback
- Stage-3 snapshot: `resolved_brand_route / medium`
- Pitch angle: Лагутин — известный в индустрии, придёт с пулом агентств. Но он ценит 'что-то новое'. Питч = 'освежим ваш vertical content, покажем альтернативу текущему production'.
- Текущий gap: Нужно добить персональный Instagram/Telegram Евгения Лагутина через vc.ru, Cossa, AdIndex и выступления.

Что писать:
- Тема: Befree: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас новый marketing manager евгений лагутин.
- Оффер: Для Befree здесь логично предложить Лагутин — известный в индустрии, придёт с пулом агентств. Но он ценит 'что-то новое'. Питч = 'освежим ваш vertical content, покажем альтернативу текущему production'..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Евгений Лагутин (Marketing Manager)

Что уже найдено:
- Official brand Telegram: https://t.me/befree_community
- Brand site: https://befree.ru/
- Stage-3 emails: info@befree.ru, suppliers.befree@melonfashion.com
- Fallback email: bunkovaar@melonfashion.com
- Fallback email: rubinovamzh@melonfashion.com

Доверенные ссылки:
- https://theblueprint.ru/career/brand/befree
- https://theblueprint.ru/career/39242
- https://theblueprint.ru/career/38765
- https://theblueprint.ru/career/38585
- https://theblueprint.ru/career/33958
- https://theblueprint.ru/career/33262
- https://theblueprint.ru/career/32518
- https://theblueprint.ru/career/32500

Если добивать ещё 10 минут:
- "Евгений Лагутин" Befree
- "Евгений Лагутин" Instagram
- "Евгений Лагутин" Telegram
- site:vc.ru "Евгений Лагутин"

Potential noise, не использовать как доказательство:
- https://otvet.mail.ru/question/64897906
- https://otvet.mail.ru/question/241417322
- https://otvet.mail.ru/question/68745925
- https://otvet.mail.ru/question/236671480
- https://www.facebook.com/Repubblica/

### 3. Ushatava

- Verdict: `WRITE NOW`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_1`
- Score: `170`
- Почему сейчас: Ushatava открывает или усиливает обувную и аксессуарную категорию. Это прямой launch-content кейс под кампанию и product reels.
- Кому писать первым: Нино Шаматавa (Creative / Content Director, co-founder)
- Вход: person-first via Instagram, then official photo/content contact
- Stage-3 snapshot: `stage-2 only / not in current route snapshot`
- Pitch angle: Запуск новой категории (обувь) = нужны съёмки product + campaign. Их стиль = минималистичная режиссура, подходит Danil/Georgiy.
- Текущий gap: Отдельно найти личный route Алисы Ушатовой, чтобы писать двум лицам с разным углом: launch и brand.

Что писать:
- Тема: Ushatava: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас ushatava открывает или усиливает обувную и аксессуарную категорию.
- Оффер: Для Ushatava здесь логично предложить Запуск новой категории (обувь) = нужны съёмки product + campaign. Их стиль = минималистичная режиссура, подходит Danil/Georgiy..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Нино Шаматавa (Creative / Content Director, co-founder)

Что уже найдено:
- Нино Шаматава (Content director / co-founder): https://www.instagram.com/ninoshenka/, photo@ushatava.com
- Official client service bot: https://t.me/Ushatava_clientsbot
- Official contacts: https://en.ushatava.ru/about/contacts/
- Fallback email: photo@ushatava.com

Доверенные ссылки:
- https://theblueprint.ru/career/brand/ushatava
- https://theblueprint.ru/career/39175
- https://theblueprint.ru/career/38811
- https://theblueprint.ru/career/38795
- https://theblueprint.ru/career/37895
- https://theblueprint.ru/career/36757
- https://theblueprint.ru/career/35868
- https://theblueprint.ru/career/35648

Если добивать ещё 10 минут:
- "Алиса Ушатова" Instagram
- "Алиса Ушатова" Telegram
- "Нино Шаматава" Telegram

### 4. Emka

- Verdict: `WRITE NOW`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_1`
- Score: `169`
- Почему сейчас: Прохор Шаляпин только что стал PR-менеджером бренда. Новый PR-руководитель почти всегда ищет быстрые заметные кейсы.
- Кому писать первым: Прохор Шаляпин (PR-менеджер)
- Вход: person-first via Instagram or Telegram
- Stage-3 snapshot: `resolved_person_route / high`
- Pitch angle: Новый PR-директор будет ставить свою повестку — ему нужен сильный визуал за первые 60 дней. Питч = сезонный имиджевый ролик + 4 вертикала.
- Текущий gap: Если личный DM не зайдет, дожать через брендовый PR-mailbox и подтверждение нового PR owner в профильных медиа.

Что писать:
- Тема: Emka: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас прохор шаляпин только что стал pr-менеджером бренда.
- Оффер: Для Emka здесь логично предложить Новый PR-директор будет ставить свою повестку — ему нужен сильный визуал за первые 60 дней. Питч = сезонный имиджевый ролик + 4 вертикала..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Прохор Шаляпин (PR-менеджер)

Что уже найдено:
- Прохор Шаляпин (PR-менеджер): https://www.instagram.com/shalyapin_official/, https://t.me/aChaliapin
- Brand site: https://emka-fashion.ru/
- Fallback email: hrfactory@emkafashion.ru

Доверенные ссылки:
- https://theblueprint.ru/career/brand/emka
- https://theblueprint.ru/career/brand/brendemka
- https://theblueprint.ru/career/39044
- https://theblueprint.ru/career/39035
- https://theblueprint.ru/career/36216
- https://theblueprint.ru/career/27027
- https://theblueprint.ru/career/26214
- https://theblueprint.ru/career/27674

Если добивать ещё 10 минут:
- "Прохор Шаляпин" Emka
- "Прохор Шаляпин" Instagram
- "Прохор Шаляпин" Telegram

Potential noise, не использовать как доказательство:
- https://www.zhihu.com/question/6633411738
- https://www.zhihu.com/question/1980596374903993722
- https://www.zhihu.com/question/1903028279096632276
- https://www.zhihu.com/question/1987568735523980297

### 5. Finn Flare

- Verdict: `ENRICH 10-15 MIN, THEN WRITE`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_1`
- Score: `166`
- Почему сейчас: Ищут SMM-менеджера. Это обычно значит, что дистрибуцию строят in-house, а тяжелый видео-продакшн готовы отдавать наружу.
- Кому писать первым: Named HR bridge + marketing/pr mailbox (Bridge to marketing owner)
- Вход: named-email-first with parallel official Telegram/Instagram touch
- Stage-3 snapshot: `stage-2 only / not in current route snapshot`
- Pitch angle: SMM-менеджер сам не снимет кампанию. NSX — готовый пакет 15-20 сек вертикалов для TG/VK. Чек 150-300к на ежемесячный поток контента.
- Текущий gap: Нужно имя текущего маркетинг/бренд owner, чтобы уйти от HR-bridge к buyer.

Что писать:
- Тема: Finn Flare: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас ищут smm-менеджера.
- Оффер: Для Finn Flare здесь логично предложить SMM-менеджер сам не снимет кампанию. NSX — готовый пакет 15-20 сек вертикалов для TG/VK. Чек 150-300к на ежемесячный поток контента..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Named HR bridge + marketing/pr mailbox (Bridge to marketing owner)

Что уже найдено:
- Unknown marketing owner (SMM / marketing): chernovitskaya@finn-flare.ru
- Official brand Telegram: https://t.me/finnflareofficial
- Official brand Instagram: https://www.instagram.com/finn_flare_official/
- Fallback email: chernovitskaya@finn-flare.ru
- Fallback email: gavrikova@finn-flare.ru
- Fallback email: ivanova.a@finn-flare.ru
- Fallback email: kadry@finn-flare.ru

Доверенные ссылки:
- https://theblueprint.ru/career/brand/finnflare
- https://theblueprint.ru/career/38809
- https://theblueprint.ru/career/34159
- https://theblueprint.ru/career/32702
- https://theblueprint.ru/career/32497
- https://theblueprint.ru/career/31693
- https://theblueprint.ru/career/31509
- https://theblueprint.ru/career/30451

Если добивать ещё 10 минут:
- "Finn Flare" marketing director
- "Finn Flare" brand director
- "Finn Flare" Telegram

### 6. Lamoda

- Verdict: `ENRICH 10-15 MIN, THEN WRITE`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_2`
- Score: `154`
- Почему сейчас: Одновременно видны digital marketing, STM design, event и producer signals. Это значит, что Lamoda строит контент-поток, а не единичную кампанию.
- Кому писать первым: Brand / STM owner (name to confirm) (Private label / digital marketing)
- Вход: role-first via named Lamoda email plus brand Telegram
- Stage-3 snapshot: `stage-2 only / not in current route snapshot`
- Pitch angle: СТМ требует отдельной визуальной идентичности. Питч = полный пакет (имиджевые + соцсеть-вертикалы) для запуска.
- Текущий gap: Нужно имя владельца STM/private label или текущего brand lead, иначе писать придется через bridge contact.

Что писать:
- Тема: Lamoda: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас одновременно видны digital marketing, stm design, event и producer signals.
- Оффер: Для Lamoda здесь логично предложить СТМ требует отдельной визуальной идентичности. Питч = полный пакет (имиджевые + соцсеть-вертикалы) для запуска..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Brand / STM owner (name to confirm) (Private label / digital marketing)

Что уже найдено:
- Darya Sokolova (Lamoda contact from Blueprint hiring trail): darya.sokolova@lamoda.ru
- Official brand Telegram: https://t.me/lamoda_na_svyazi
- Official brand Instagram: https://www.instagram.com/lamoda/
- Career site: https://job.lamoda.ru/
- Fallback email: darya.sokolova@lamoda.ru

Доверенные ссылки:
- https://theblueprint.ru/career/brand/lamoda
- https://theblueprint.ru/career/39231
- https://theblueprint.ru/career/39181
- https://theblueprint.ru/career/38885
- https://theblueprint.ru/career/38646
- https://theblueprint.ru/career/38132
- https://theblueprint.ru/career/38154
- https://theblueprint.ru/career/37870

Если добивать ещё 10 минут:
- "Lamoda" "private label" маркетинг
- "Lamoda" brand director
- "Lamoda" Telegram

### 7. Bork

- Verdict: `WRITE NOW`
- Segment: `B` (strong brand / retail)
- Wave: `wave_2`
- Score: `138`
- Почему сейчас: У Bork одновременно видны CRM, brand, SMM и event roles. Это не единичный найм, а работающий контент- и brand-маховик.
- Кому писать первым: Brand / marketing owner via named Bork email (Brand or CRM marketing)
- Вход: named-email-first, then premium brand socials
- Stage-3 snapshot: `stage-2 only / not in current route snapshot`
- Pitch angle: Bork = премиум-сегмент. Режиссёрский имиджевый ролик 1.5 мин — их стандарт. Кейсы Dior/Hugo убеждают.
- Текущий gap: Нужно конкретное имя бренд-менеджера или PR owner, чтобы перестать писать через hiring bridge.

Что писать:
- Тема: Bork: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас у bork одновременно видны crm, brand, smm и event roles.
- Оффер: Для Bork здесь логично предложить Bork = премиум-сегмент. Режиссёрский имиджевый ролик 1.5 мин — их стандарт. Кейсы Dior/Hugo убеждают..
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Brand / marketing owner via named Bork email (Brand or CRM marketing)

Что уже найдено:
- Valeriya Chernova (HR / hiring bridge): valeriya.chernova@bork.com
- Official brand Telegram: https://t.me/bork_public
- Official brand Instagram: https://www.instagram.com/bork_com/
- Fallback email: valeriya.chernova@bork.com
- Fallback email: valeriya.chernova@bork.ru

Доверенные ссылки:
- https://theblueprint.ru/career/brand/bork
- https://theblueprint.ru/career/39243
- https://theblueprint.ru/career/39057
- https://theblueprint.ru/career/38608
- https://theblueprint.ru/career/38379
- https://theblueprint.ru/career/38080
- https://theblueprint.ru/career/36784
- https://theblueprint.ru/career/36522

Если добивать ещё 10 минут:
- "Bork" "бренд-менеджер"
- "Bork" PR director
- "Valeriya Chernova" Bork

### 8. 2Mood

- Verdict: `WRITE NOW`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_2`
- Score: `138`
- Почему сейчас: Свежий найм в SMM и Influence & PR marketing. Это ровно тот момент, когда бренд расширяет контент-команду, но еще не закрыл все production-потребности.
- Кому писать первым: Полина Подплетенная (Co-owner)
- Вход: person-first via founder Instagram, then brand mailboxes
- Stage-3 snapshot: `resolved_person_route / high`
- Текущий gap: Нужно имя текущего Influence & PR marketing lead, чтобы писать founders + team owner.

Что писать:
- Тема: 2Mood: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас свежий найм в smm и influence & pr marketing.
- Оффер: Для 2Mood здесь логично предложить короткий launch-пакет для 2Mood: 1 hero video + 4-6 вертикалей под Instagram / Telegram / VK.
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Полина Подплетенная (Co-owner)

Что уже найдено:
- Полина Подплетенная (Co-owner): https://www.instagram.com/pollyhey/, pollyheywork@gmail.com
- Кристина Хоронжук (Co-owner): https://www.instagram.com/khkris/, khkristinaur@gmail.com
- Brand Telegram: https://t.me/twomoodstore
- Brand Instagram: https://www.instagram.com/2moodstore/
- Stage-3 emails: pollyheywork@gmail.com, khkristinaur@gmail.com, cambiopasswordmail@telecomitalia.it
- Fallback email: pollyheywork@gmail.com
- Fallback email: khkristinaur@gmail.com
- Fallback email: p.moskalev@2mood.com

Доверенные ссылки:
- https://theblueprint.ru/career/brand/2mood
- https://theblueprint.ru/career/38606
- https://theblueprint.ru/career/38605
- https://theblueprint.ru/career/37366
- https://theblueprint.ru/career/37309
- https://theblueprint.ru/career/37302
- https://theblueprint.ru/career/36662
- https://theblueprint.ru/career/36109

Если добивать ещё 10 минут:
- "2MOOD" "Influence & PR"
- "Полина Подплетенная" Telegram
- "Кристина Хоронжук" Telegram

Potential noise, не использовать как доказательство:
- https://gemini.google.com/?hl=es

### 9. YuliaWave

- Verdict: `WRITE NOW`
- Segment: `C` (founder-led DTC / fashion / beauty)
- Wave: `wave_3`
- Score: `134`
- Почему сейчас: Свежий PR-director signal плюс у founder-led fashion house уже есть прямой personal route, что сильно сокращает путь до решения.
- Кому писать первым: Юлия Василевская (Founder)
- Вход: person-first via founder Instagram, then CEO / PR email fallback
- Stage-3 snapshot: `resolved_person_route / high`
- Текущий gap: Хорошо бы найти имя нового PR director, чтобы писать founder + PR pair.

Что писать:
- Тема: YuliaWave: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас свежий pr-director signal плюс у founder-led fashion house уже есть прямой personal route, что сильно сокращает путь до решения.
- Оффер: Для YuliaWave здесь логично предложить короткий launch-пакет для YuliaWave: 1 hero video + 4-6 вертикалей под Instagram / Telegram / VK.
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Юлия Василевская (Founder)

Что уже найдено:
- Юлия Василевская (Founder): https://www.instagram.com/yuliawave/, https://t.me/YULIAWAVE_BRAND, ceo@yuliawave.com
- Brand Instagram: https://www.instagram.com/yuliawave.brand/
- Brand contacts: https://yuliawave.com/contact/
- Stage-3 emails: ceo@yuliawave.com, hello@octopus.energy, admin@disneyplusenquiries.com
- Fallback email: ceo@yuliawave.com
- Fallback email: creative.director@yuliawave.com
- Fallback email: art.director@yuliawave.com
- Fallback email: hrd@yuliawave.com

Доверенные ссылки:
- https://theblueprint.ru/career/brand/yuliawave
- https://theblueprint.ru/career/brand/brendyuliawave
- https://theblueprint.ru/career/37838
- https://theblueprint.ru/career/36494
- https://theblueprint.ru/career/36377
- https://theblueprint.ru/career/36177
- https://theblueprint.ru/career/33886
- https://theblueprint.ru/career/33431

Если добивать ещё 10 минут:
- "YuliaWave" "PR-директор"
- "Юлия Василевская" Telegram

Potential noise, не использовать как доказательство:
- https://www.reddit.com/r/DisneyPlus/comments/j5lc5s/i_cant_load_the_disney_home_screen_or_login_page/
- https://www.reddit.com/r/DisneyPlus/comments/yve8ef/is_anyone_else_getting_this_email_not_sure_if_it/
- https://www.reddit.com/r/DisneyPlus/comments/vbezza/technical_support_mega_thread/

### 10. Бар «Ровесник»

- Verdict: `WRITE NOW`
- Segment: `D` (HoReCa / restaurant)
- Wave: `wave_3`
- Score: `131`
- Почему сейчас: Две свежие SMM-роли с фокусом на content и sales. Для HoReCa это почти прямой маркер постоянной потребности в роликах и social formats.
- Кому писать первым: Александр Мартынов (Co-founder)
- Вход: founder-aware via official Instagram/Telegram and HR Telegram handle
- Stage-3 snapshot: `resolved_person_route / high`
- Текущий gap: Нужно добить личный Instagram/Telegram Александра Мартынова и второго co-founder для прямого owner outreach.

Что писать:
- Тема: Бар «Ровесник»: идея под текущий hiring / launch signal
- Открытие: Увидел, что у вас две свежие smm-роли с фокусом на content и sales.
- Оффер: Для Бар «Ровесник» здесь логично предложить серия vertical reels для Бар «Ровесник» + быстрый AI-джингл / саунд-идея под social и заведение.
- CTA: Если уместно, отправим 2 релевантных кейса и treatment на 1 страницу без длинного созвона.
- Кому: Александр Мартынов (Co-founder)

Что уже найдено:
- HR / studio contact (Hiring bridge): https://t.me/HRp2pstudio
- Official bar Telegram: https://t.me/rovesnikbar
- Official bar Instagram: https://www.instagram.com/rovesnik.bar/

Доверенные ссылки:
- https://theblueprint.ru/career/brand/bar-rovesnik
- https://theblueprint.ru/career/38754
- https://theblueprint.ru/career/38753
- https://t.me/rovesnikbar
- https://www.instagram.com/rovesnik.bar/
- https://moskvichmag.ru/gorod/v-malom-gnedzdnikovskom-otkroetsya-bar-rovesnik-pryamo-u-ministerstva-kultury/
- https://t.me/HRp2pstudio

Если добивать ещё 10 минут:
- "Александр Мартынов" "Ровесник" Instagram
- "Александр Мартынов" "Ровесник" Telegram
- "Кирилл" "Ровесник" бар

Potential noise, не использовать как доказательство:
- https://www.zhihu.com/question/12490593786
- https://www.zhihu.com/question/29788274
- https://www.zhihu.com/question/474514219

## Backlog: хорошие бренды, но не первая десятка

- `ADDA gems` | seg `C` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер, Контент-директор.
- `ARLIGENT` | seg `C` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Директор по маркетингу. Creative content signals: Визуальный мерчандайзер.
- `Золотое Яблоко` | seg `C` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: SMM, Контент-директор.
- `AllTime` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель SMM-отдела.
- `Blar` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Директор по маркетингу.
- `Botrois` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Директор по маркетингу.
- `Kin` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Директор по маркетингу.
- `Leokid` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Директор по маркетингу.
- `MTС` | seg `B` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: Руководитель в отдел событийного маркетинга, Маркетинговый аналитик.
- `Nrav` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель команды маркетинга.
- `Oniverse` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Старший PR-менеджер, Специалист отдела трейд-маркетинга и event-отдела. Creative content signals: Специалист отдела трейд-маркетинга и event-отдела.
- `Ozon` | seg `B` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: Стажер-маркетолог, Стажер в B2C промо-маркетинг, Контент-маркетолог образовательных проектов.
- `RINK` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер, Директор по маркетингу.
- `Scandale Manière` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель SMM-направления.
- `Simple Group` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель группы контент-поддержки, Руководитель PR-отдела, Бренд-менеджер.
- `Sportmaster` | seg `B` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: Бренд-менеджер, Бренд-менеджер.
- `T2` | seg `B` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: менеджер по маркетингу и контролю качества бренд материалов, Старший специалист по маркетинговым коммуникациям, Менеджер по бренд-коммуникациям.
- `The Ayris` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Бренд-директор.
- `«Технопарк»` | seg `B` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: PR-менеджер, Руководитель отдела маркетинговых коммуникаций. Creative content signals: Event-менеджер.
- `Т-Банк` | seg `B` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: IR PR-менеджер, Стажер PR-специалист, Старший категорийный маркетолог в направление «Мода».
- `2ГИС` | seg `E` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель CRM-маркетинга, HR-маркетолог, SMM-менеджер. Creative content signals: Креативный продюсер.
- `KION` | seg `E` | nsx `3` | priority `high` | route `not resolved` | Fresh direct roles in last 365d: Руководитель SMM-отдела, Заместитель PR-директора.
- `VK` | seg `E` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: PR-менеджер для продвижения HR-бренда, Ведущий менеджер по коммуникациям в продуктовый PR, Старший event-маркетолог. Creative content signals: Старший event-маркетолог.
- `«Яндекс»` | seg `E` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель службы контента, SMM-менеджер. Creative content signals: Арт-директор.
- `Авито` | seg `E` | nsx `3` | priority `high` | route `unresolved / low` | Fresh direct roles in last 365d: Старший менеджер по продуктовому маркетингу категории Fashion, Руководитель направления внутренних коммуникаций, Стажер в PR-команду.
- `Aldo Coppola` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по связям с общественностью и коммуникациям.
- `ALL WE NEED` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Контент-креатор, SMM-менеджер, PR и Influence менеджер. Creative content signals: Контент-креатор.
- `Belle YOU` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR&Influence менеджер, Стажер в SMM-отдел.
- `BLCV` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Ekonika` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Loom by Rodina` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `MIUZ Diamonds` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по маркетинговым коммуникациям и PR, Менеджер по продвижению бренда в социальных сетях.
- `Monochrome` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Контент-креатор, SMM-менеджер. Creative content signals: Контент-креатор.
- `Poison Drop` | seg `C` | nsx `2` | priority `medium` | route `partial / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `RMixed` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по маркетинговым коммуникациям.
- `Sela` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR и Influence-менеджер.
- `SHIKcosmetics, Natalya Shik` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-специалист, SMM-специалист, Influence-менеджер.
- `Studio 29` | seg `C` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `ABC Coffee Roasters` | seg `D` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Бренд-менеджер.
- `Bosco di Ciliegi` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по маркетинговым коммуникациям.
- `Cois` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `F | ABLE` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по маркетинговым коммуникациям.
- `Imakebags` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Jenek` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-редактор с функционалом контент-мейкера.
- `Kits` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Руководитель SMM-отдела.
- `Linda de La` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Маркетолог, Маркетолог, PR-специалист.
- `Miele` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR-менеджер.
- `NAOS` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по PR и работе с лидерами мнений.
- `Nikasport` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Omoikiri` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Parure Atelier` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Контент-продюсер. Creative content signals: Контент-продюсер.
- `Pitkina` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR-менеджер.
- `Pritch` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `R4S` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `Rendez-Vous` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Старший PR-менеджер.
- `Sanchy` | seg `B` | nsx `2` | priority `medium` | route `partial / low` | Fresh direct roles in last 365d: PR-менеджер.
- `SENECA` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Бренд-менеджер.
- `Tondeo` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Бренд-менеджер.
- `VASSA&Co` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `vesnaskoro` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR-специалист.
- `Volga Dream` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Менеджер по маркетингу и коммуникациям.
- `Way of living/WoL` | seg `B` | nsx `2` | priority `medium` | route `partial / low` | Fresh direct roles in last 365d: Бренд-менеджер.
- `WoL` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер.
- `«Самокат»` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Старший SMM-менеджер.
- `Авиасейлс` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: SMM-менеджер, Креативный маркетинг-менеджер, Контент-редактор. Creative content signals: Креативный маркетинг-менеджер.
- `Бани Малевича` | seg `B` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Маркетолог.
- `«Кинопоиск»` | seg `E` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Аналитик контента.
- `«Сбер»` | seg `E` | nsx `2` | priority `medium` | route `partial / low` | Fresh direct roles in last 365d: Руководитель PR-направления.
- `Книжный сервис «Кион Строки»` | seg `E` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: PR-менеджер.
- `Магнит AdTech` | seg `E` | nsx `2` | priority `medium` | route `unresolved / low` | Fresh direct roles in last 365d: Ведущий менеджер по маркетингу.
- `Prime Ride` | seg `D` | nsx `2` | priority `low` | route `not resolved` | 

## Potential Мусор В Auto-Search

Эти бренды не обязательно плохие. Плохой именно auto-search хвост, который нельзя считать контактом без ручной проверки.

- `BLCV` | status `unresolved` | noise `8` | domains: www.zhihu.com, zhidao.baidu.com, support.microsoft.com
- `Poison Drop` | status `partial` | noise `8` | domains: www.zhihu.com
- `Pritch` | status `unresolved` | noise `8` | domains: support.microsoft.com, support.google.com
- `SHIKcosmetics, Natalya Shik` | status `unresolved` | noise `8` | domains: www.zhihu.com, en-gb.facebook.com, www.facebook.com, l.facebook.com
- `«Самокат»` | status `unresolved` | noise `8` | domains: www.zhihu.com, en-gb.facebook.com
- `«Технопарк»` | status `unresolved` | noise `8` | domains: www.zhihu.com
- `Studio 29` | status `unresolved` | noise `7` | domains: www.studio.se
- `Oniverse` | status `unresolved` | noise `6` | domains: www.zhihu.com, mail.google.com
- `Scandale Manière` | status `unresolved` | noise `6` | domains: www.reddit.com
- `Befree` | status `resolved_brand_route` | noise `5` | domains: otvet.mail.ru, www.facebook.com
- `Jenek` | status `unresolved` | noise `5` | domains: www.reddit.com, support.google.com, www.zhihu.com
- `Way of living/WoL` | status `partial` | noise `5` | domains: www.waygroup.se
- `ABC Coffee Roasters` | status `unresolved` | noise `4` | domains: www.zhihu.com, zhidao.baidu.com
- `ADDA gems` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `ALL WE NEED` | status `unresolved` | noise `4` | domains: www.zhihu.com, zhidao.baidu.com
- `AllTime` | status `unresolved` | noise `4` | domains: support.microsoft.com
- `Belle YOU` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Cois` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Emka` | status `resolved_person_route` | noise `4` | domains: www.zhihu.com
- `F | ABLE` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Imakebags` | status `unresolved` | noise `4` | domains: accounts.google.com
- `Kin` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Linda de La` | status `unresolved` | noise `4` | domains: www.zhihu.com, zhidao.baidu.com
- `Loom by Rodina` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Miele` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `MIUZ Diamonds` | status `unresolved` | noise `4` | domains: jingyan.baidu.com, www.zhihu.com
- `Monochrome` | status `unresolved` | noise `4` | domains: zhidao.baidu.com, www.zhihu.com
- `Nikasport` | status `unresolved` | noise `4` | domains: www.reddit.com
- `Pitkina` | status `unresolved` | noise `4` | domains: www.reddit.com
- `RINK` | status `unresolved` | noise `4` | domains: jingyan.baidu.com
- `RMixed` | status `unresolved` | noise `4` | domains: outlook.office.com, outlook.live.com, www.youtube.com, play.google.com
- `Sela` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `SENECA` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Simple Group` | status `unresolved` | noise `4` | domains: www.zhihu.com, zhidao.baidu.com
- `The Ayris` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Tondeo` | status `unresolved` | noise `4` | domains: messagerie.orange.fr, mon-espace.mail.orange.fr, communaute.orange.fr, espace-client.orange.fr
- `VK` | status `unresolved` | noise `4` | domains: www.zhihu.com
- `Volga Dream` | status `unresolved` | noise `4` | domains: www.zhihu.com, zhidao.baidu.com
- `Авито` | status `unresolved` | noise `4` | domains: www.reddit.com
- `Aldo Coppola` | status `unresolved` | noise `3` | domains: www.zhihu.com
- `Kits` | status `unresolved` | noise `3` | domains: www.zhihu.com
- `R4S` | status `unresolved` | noise `3` | domains: chatgpt.com, openai.com
- `YuliaWave` | status `resolved_person_route` | noise `3` | domains: www.reddit.com
- `Бар «Ровесник»` | status `resolved_person_route` | noise `3` | domains: www.zhihu.com

### Наиболее частые шумные домены

- `www.zhihu.com` — `107`
- `www.reddit.com` — `22`
- `zhidao.baidu.com` — `13`
- `support.microsoft.com` — `12`
- `jingyan.baidu.com` — `8`
- `support.google.com` — `7`
- `www.studio.se` — `7`
- `www.facebook.com` — `6`
- `accounts.google.com` — `5`
- `en-gb.facebook.com` — `5`
- `www.waygroup.se` — `5`
- `otvet.mail.ru` — `4`
- `mail.google.com` — `3`
- `play.google.com` — `3`
- `openai.com` — `2`
- `outlook.live.com` — `2`
- `www.youtube.com` — `2`
- `answers.microsoft.com` — `1`
- `chatgpt.com` — `1`
- `communaute.orange.fr` — `1`

## Что я считаю готовым к отправке прямо сейчас

- `Don't Touch My Skin`
- `Emka`
- `Ushatava`
- `2Mood`
- `YuliaWave`

## Что сначала бы ещё добил 10-15 минут

- `Befree` — нужен прямой social-route Евгения Лагутина
- `Finn Flare` — нужно имя buyer, а не только HR bridge
- `Lamoda` — нужен owner private label / brand
- `Bork` — нужен brand / PR owner вместо hiring bridge
- `Бар «Ровесник»` — нужен личный route фаундера, а не только brand socials

## Где смотреть сырые артефакты

- `inputs/theblueprint_career_hiring.yaml` — shortlist на 81 бренд
- `output/company_contacts_enrichment/theblueprint_people_targets.yaml` — top-10 people targets
- `output/company_contacts_enrichment/theblueprint_route_resolutions.yaml` — stage-3 route snapshot
