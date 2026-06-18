# <feature-name> PRD

<!--
Use this template only for implemented-feature PRD delivery.
All human-facing headings and table labels must be localized before delivery.
Keep requirement IDs, event names, property names, file names, and run ids in ASCII where they are machine identifiers.
Remove this note from generated artifacts.
-->

## 1. <document information>

| <item>                       | <content> |
| ---------------------------- | --------- |
| <feature name>               |           |
| <branch / version>           |           |
| <document date>              |           |
| <related modules>            |           |
| <PRD status>                 |           |
| <engineering handoff status> |           |
| <launch status>              |           |

## 2. <version history>

| <version> | <date> | <change summary> | <owner> |
| --------- | ------ | ---------------- | ------- |

## 3. <background and current problems>

## 4. <product goals and metrics>

| ID  | <goal> | <metric> | <target / direction> | <measurement note> |
| --- | ------ | -------- | -------------------- | ------------------ |

## 5. <users and scenarios>

| ID  | <user / role> | <scenario> | <desired outcome> |
| --- | ------------- | ---------- | ----------------- |

## 6. <scope>

### 6.1 <in scope>

| ID  | <scope item> | <source evidence> | <priority> |
| --- | ------------ | ----------------- | ---------- |

### 6.2 <out of scope>

| ID  | <out-of-scope item> | <reason> |
| --- | ------------------- | -------- |

## 7. <information architecture and entry points>

| ID  | <entry / surface> | <visible condition> | <target state> | <permission / fallback> |
| --- | ----------------- | ------------------- | -------------- | ----------------------- |

## 8. <functional requirements>

### 8.1 <requirement name>

<!--
Put screenshots or missing-image placeholders directly below the requirement heading or inside the relevant row.
Missing-image placeholder format must be exactly:

> 占位图：<recommended-image-name>.png
> 用途：<one sentence describing the UI state, dialog, or requirement position>

When the real image exists, replace the whole placeholder block with:
![<recommended-image-name>](./assets/<recommended-image-name>.png)

Name missing and real screenshots by content. When one object has multiple states, use object-specific state names such as `文件上传-上传中.png` and `文件上传-上传失败.png`, not `文件上传-状态.png`.

Do not create a separate screenshot/image list.
-->

| ID  | <function> | <user scenario> | <entry / trigger> | <content requirements> | <business logic> | <interaction rules> | <data rules> | <permission rules> | <edge states> | <tracking links> | <acceptance links> |
| --- | ---------- | --------------- | ----------------- | ---------------------- | ---------------- | ------------------- | ------------ | ------------------ | ------------- | ---------------- | ------------------ |

## 9. <parameters and rules>

### 9.1 <parameter group>

| <parameter> | <type> | <source> | <usage> | <rule / limit> |
| ----------- | ------ | -------- | ------- | -------------- |

## 10. <states and exceptions>

| ID  | <state / exception> | <trigger> | <display / behavior> | <recovery / next action> | <related requirement IDs> |
| --- | ------------------- | --------- | -------------------- | ------------------------ | ------------------------- |

## 11. <permissions and operation boundaries>

| <role / asset / object> | <view> | <create> | <edit> | <delete> | <batch action> | <notes> |
| ----------------------- | ------ | -------- | ------ | -------- | -------------- | ------- |

## 12. <data and API requirements>

### 12.1 <existing calls or implemented data source>

| <capability> | <current source / endpoint> | <frontend usage> | <limitation> |
| ------------ | --------------------------- | ---------------- | ------------ |

### 12.2 <backend requirements>

| ID  | <capability> | <method / endpoint proposal> | <request fields> | <response fields> | <error codes / states> | <frontend integration note> |
| --- | ------------ | ---------------------------- | ---------------- | ----------------- | ---------------------- | --------------------------- |

## 13. <frontend real-data integration notes>

| ID  | <current implementation state> | <real-data integration requirement> | <affected files / modules> |
| --- | ------------------------------ | ----------------------------------- | -------------------------- |

## 14. <tracking and monitoring>

| <event_name> | <description> | <trigger> | <required_properties> | <success criteria> | <privacy note> |
| ------------ | ------------- | --------- | --------------------- | ------------------ | -------------- |

## 15. <copy and i18n>

| <key / scene> | <copy> | <usage> | <i18n note> |
| ------------- | ------ | ------- | ----------- |

## 16. <acceptance criteria>

| ID  | <requirement IDs> | <criteria> | <verification method> |
| --- | ----------------- | ---------- | --------------------- |

## 17. <test suggestions>

| <test type> | <coverage> | <suggested cases> |
| ----------- | ---------- | ----------------- |

## 18. <risks and dependencies>

| ID  | <risk / dependency> | <impact> | <owner> | <mitigation / decision> |
| --- | ------------------- | -------- | ------- | ----------------------- |

## 19. <implementation evidence and coverage map>

| <evidence ID> | <source> | <observed behavior> | <related requirement IDs> | <coverage status> | <gap / risk> |
| ------------- | -------- | ------------------- | ------------------------- | ----------------- | ------------ |

## 20. <reference code locations>

| <module> | <path> | <note> |
| -------- | ------ | ------ |
