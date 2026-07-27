# Domain Glossary

- **ACD Calls (Answered)**: Calls that were answered by an agent.
- **ABAN Calls (Abandoned)**: Calls that were abandoned by the caller before being answered.
- **Call Offered**: Total calls presented to the system. Formula: `ACD Calls + ABAN Calls`.
- **Service Level**: The percentage of calls answered within a threshold (20 seconds), adjusted for calls abandoned within a short threshold (10 seconds).
- **Avg Hold Time**: The average time a caller spends on hold during an answered call.
- **Avg Handle Time (AHT)**: The average total time spent on a call, including talk time (ACD Time), after-call work (ACW Time), and hold time.
- **Good/Penalty Thresholds**:
  - Service Level: >85% is Good.
  - Avg Handle Time: <= 240 seconds is Good.
  - Avg Hold Time: <= 20 seconds is Good.
