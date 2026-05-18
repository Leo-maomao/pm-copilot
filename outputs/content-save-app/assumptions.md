# Assumptions

| ID | Assumption | Reason | Risk |
|---|---|---|---|
| A1 | App is the primary platform. | The task explicitly asks for mobile app behavior. | Web saved content may need separate design. |
| A2 | Save requires login. | Saved lists usually need account persistence. | Login friction may reduce save rate. |
| A3 | Offline access depends on content rights and local cache. | Content rights and storage are mentioned constraints. | Users may expect all saved content to work offline. |
| A4 | V1 excludes folders and advanced sorting. | The request asks for simple save and maybe offline reading. | Heavy users may need organization later. |
| A5 | Analytics should not log article body text or raw device paths. | Content and device data can be sensitive. | Diagnostics may require aggregated identifiers instead. |
