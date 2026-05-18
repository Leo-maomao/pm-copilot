# Assumptions

| ID | Assumption | Reason | Risk |
|---|---|---|---|
| A1 | Mini Program is the primary platform. | The task requests booking inside a mini program. | Native app or web booking may need separate flows. |
| A2 | Payment is excluded from v1. | The brief states payment is out of scope. | Some services may require deposit later. |
| A3 | Authorization is required before submission, not before viewing. | Users should understand value before permission request. | Platform rules may require earlier authorization. |
| A4 | Slot inventory is provided by operations. | Booking depends on available appointment slots. | Stale inventory can cause failed submissions. |
| A5 | Analytics excludes raw phone and name. | Contact fields are personal data. | Operations diagnostics should use booking ID instead. |
