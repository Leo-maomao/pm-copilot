# Mini Program Appointment Booking PRD

## Status and Owners

| Field | Value |
|---|---|
| Status | Draft for review |
| Product owner | TBD |
| Design owner | TBD |
| Engineering owner | TBD |
| Analytics owner | TBD |
| Operations owner | TBD |

## Background

Users currently rely on support messages to reserve service appointments. This creates manual work, delayed confirmation, and inconsistent booking records.

## Problem Statement

Users need a simple mini-program booking flow that supports authorization, service selection, time-slot selection, and confirmation without requiring manual support messages.

## Goals

| Goal | Metric | Target | Notes |
|---|---|---|---|
| Reduce manual booking | Self-service booking rate | TBD | Primary |
| Improve booking completion | Booking form completion rate | TBD | Secondary |
| Protect operations quality | No-show rate and support correction rate | No material increase | Guardrail |

## Non-goals

- Payment collection.
- Full staff scheduling system.
- Complex rescheduling and cancellation rules.
- Loyalty or coupon integration.

## Target Users

- User booking a service appointment.
- First-time visitor who needs authorization.
- Operations staff reviewing confirmed appointments.

## User Scenarios

| Scenario | Entry Point | User Need | Expected Outcome |
|---|---|---|---|
| First-time booking | Mini program home | Authorize and select service | Booking is confirmed |
| Returning booking | Service detail | Pick an available time slot | Confirmation page appears |
| No available slots | Time slot page | Understand unavailable dates | User can choose another date |
| Missing contact | Booking form | Complete required contact fields | User can submit booking |

## Scope

| Area | In Scope | Out of Scope |
|---|---|---|
| Authorization | Request minimal user authorization | Full account system redesign |
| Service selection | Choose one service type | Multi-service bundle |
| Time slot selection | Show available dates and slots | Staff optimization |
| Booking form | Name and contact method if required | Payment |
| Confirmation | Show booking details and support contact | Calendar integration |

## Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| R1 | Users can authorize before booking. | Must | Use minimal required permission |
| R2 | Users can select service type. | Must | Service list from operations config |
| R3 | Users can select available date and time slot. | Must | Hide or disable unavailable slots |
| R4 | Users can submit required contact information. | Must | Minimize personal data |
| R5 | Users see confirmation after successful booking. | Must | Include service, time, and location |
| R6 | Unavailable or expired slots show clear recovery path. | Must | Prevent dead ends |
| R7 | Events track authorization, service selection, slot selection, form submit, success, and failure. | Must | See tracking plan |

## Edge Cases

| Case | Expected Behavior | Owner |
|---|---|---|
| Authorization denied | Explain value and allow retry or exit | Product |
| No slots available | Show next available date or notify option | Product, Operations |
| Slot expires before submit | Ask user to choose another slot | Engineering |
| Booking API fails | Keep form data and allow retry | Engineering |
| Contact field invalid | Show inline validation | Design, Engineering |

## Metrics

- Primary: self-service booking rate.
- Secondary: authorization completion rate, slot selection rate, booking completion rate.
- Guardrails: no-show rate, support correction rate, booking failure rate.

## Dependencies

- Mini program authorization.
- Service and slot inventory API.
- Booking API.
- Operations confirmation process.
- Analytics pipeline.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Slot inventory is stale | High | Revalidate slot on submit |
| Too much personal data is requested | High | Minimize contact fields and review privacy |
| Users deny authorization | Medium | Explain value before retry |

## Open Questions

1. Which authorization fields are required?
2. What contact fields are mandatory?
3. How long is a time slot held?
4. Can users cancel or reschedule in v1?

## Acceptance Criteria

| Requirement ID | Criteria | Verification |
|---|---|---|
| R1 | User can proceed after authorization. | Mini program test |
| R3 | Unavailable slots cannot be selected. | QA slot inventory test |
| R4 | Invalid contact fields show inline errors. | QA form test |
| R5 | Successful booking shows confirmation details. | QA happy path |
| R6 | Expired slot asks user to choose another slot. | API race condition test |
| R7 | Analytics events fire with approved properties. | Analytics validation |
